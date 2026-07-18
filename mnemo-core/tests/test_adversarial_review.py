import json

import httpx
import pytest

from mnemo_core.models import AdversarialReviewResult, PublishResult, ReviewerReport
from mnemo_core.pipeline.review import (
    AdversarialReviewer,
    GitHubReviewAuditSink,
    _system_prompt,
)
from tests.conftest import FakeLLM, processed_doc


class FakeSink:
    def __init__(self, merged: bool = False) -> None:
        self.result = None
        self.merged = merged

    async def record(self, published, result):
        self.result = result
        return self.merged


def report(verdict: str, concerns=None, tier: str = "tier-1") -> str:
    return json.dumps(
        {
            "verdict": verdict,
            "recommended_tier": tier,
            "concerns": concerns or [],
            "rationale": f"Evidence for {verdict}.",
        }
    )


def reviewer(advocate: str, critic: str, sink=None) -> AdversarialReviewer:
    return AdversarialReviewer(
        FakeLLM(advocate),
        FakeLLM(critic),
        advocate_family="anthropic",
        critic_family="openai",
        audit_sink=sink or FakeSink(),
    )


def published() -> PublishResult:
    return PublishResult(
        pr_url="https://github.com/acme/kb/pull/42", branch="mnemo/test", file_path="how-to/a.md"
    )


@pytest.mark.parametrize("role", ["advocate", "critic"])
def test_reviewer_prompt_explains_expected_pipeline_states(role):
    prompt = _system_prompt(role)

    assert "`proposed` status" in prompt
    assert "`incomplete` flag" in prompt
    assert "unresolved cross-references awaiting the curator" in prompt
    assert "Tier 2 human" in prompt
    assert "pending ratification is not a defect" in prompt


def test_advocate_rejects_only_substantiated_correctness_or_safety_errors():
    prompt = _system_prompt("advocate")

    assert "Reject only for a demonstrable, material correctness or safety error" in prompt
    assert "otherwise accept" in prompt


def test_critic_uses_broader_material_risk_bar_without_rejecting_for_style_alone():
    prompt = _system_prompt("critic")

    assert "poor provenance" in prompt
    assert "failure to serve its stated Diataxis purpose" in prompt
    assert "style alone is grounds for rejection only when it materially" in prompt


@pytest.mark.parametrize("role", ["advocate", "critic"])
def test_reviewer_prompt_allows_non_blocking_concerns_with_acceptance(role):
    assert "Concerns may be non-blocking" in _system_prompt(role)


async def test_unanimous_tier_1_acceptance_can_merge():
    sink = FakeSink(merged=True)
    result = await reviewer(report("accept"), report("accept"), sink).review(
        processed_doc(review_tier="tier-1"), published()
    )
    assert result.outcome == "accepted"
    assert result.requires_human_review is False
    assert result.merged is True


async def test_disagreement_escalates():
    result = await reviewer(report("accept"), report("reject")).review(
        processed_doc(), published()
    )
    assert result.outcome == "escalated"
    assert result.requires_human_review is True


async def test_invalid_reviewer_response_escalates():
    result = await reviewer(report("accept"), "not json").review(processed_doc(), published())
    assert result.outcome == "escalated"
    assert result.critic is None


async def test_oversized_reviewer_concern_is_bounded_without_discarding_report():
    result = await reviewer(report("accept", ["x" * 501]), report("accept")).review(
        processed_doc(), published()
    )

    assert result.advocate is not None
    assert result.advocate.concerns == ["x" * 500]
    assert result.outcome == "accepted"


async def test_tier_2_always_requires_human_review():
    result = await reviewer(report("accept"), report("accept")).review(
        processed_doc(review_tier="tier-2"), published()
    )
    assert result.outcome == "accepted"
    assert result.requires_human_review is True
    assert result.merged is False


async def test_audit_failure_does_not_turn_successful_publish_into_error():
    class FailingSink:
        async def record(self, published, result):
            raise httpx.HTTPStatusError(
                "comment failed",
                request=httpx.Request("POST", published.pr_url),
                response=httpx.Response(503),
            )

    result = await reviewer(report("accept"), report("accept"), FailingSink()).review(
        processed_doc(review_tier="tier-1"), published()
    )

    assert result.outcome == "accepted"
    assert result.requires_human_review is False
    assert result.merged is False


async def test_either_reviewer_can_upgrade_claimed_tier_1_to_tier_2():
    result = await reviewer(report("accept"), report("accept", tier="tier-2")).review(
        processed_doc(review_tier="tier-1"), published()
    )
    assert result.tier == "tier-2"
    assert result.requires_human_review is True
    assert result.merged is False


def test_same_family_pair_is_rejected():
    with pytest.raises(ValueError, match="different provider families"):
        AdversarialReviewer(
            FakeLLM(report("accept")),
            FakeLLM(report("accept")),
            advocate_family="openai",
            critic_family="OPENAI",
            audit_sink=FakeSink(),
        )


@pytest.mark.parametrize("concern", ["", "x" * 501])
def test_reviewer_concerns_are_bounded(concern):
    with pytest.raises(ValueError, match="concerns"):
        ReviewerReport(
            role="critic",
            provider_family="openai",
            verdict="reject",
            recommended_tier="tier-1",
            concerns=[concern],
            rationale="A concern was found.",
        )


async def test_github_sink_comments_then_merges_accepted_tier_1():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "PUT":
            return httpx.Response(200, json={"merged": True})
        return httpx.Response(201, json={})

    async with httpx.AsyncClient(
        base_url="https://api.github.com", transport=httpx.MockTransport(handler)
    ) as client:
        sink = GitHubReviewAuditSink("token", "acme/kb", client)
        result = AdversarialReviewResult(
            tier="tier-1",
            outcome="accepted",
            requires_human_review=False,
            reason="Both accepted.",
        )
        assert await sink.record(published(), result) is True

    assert [request.method for request in requests] == ["POST", "PUT"]
    assert requests[0].url.path == "/repos/acme/kb/issues/42/comments"
    assert requests[1].url.path == "/repos/acme/kb/pulls/42/merge"


async def test_github_sink_never_merges_tier_2():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json={})

    async with httpx.AsyncClient(
        base_url="https://api.github.com", transport=httpx.MockTransport(handler)
    ) as client:
        sink = GitHubReviewAuditSink("token", "acme/kb", client)
        result = AdversarialReviewResult(
            tier="tier-2",
            outcome="accepted",
            requires_human_review=True,
            reason="Human required.",
        )
        assert await sink.record(published(), result) is False

    assert [request.method for request in requests] == ["POST"]


async def test_github_sink_treats_merge_refusal_as_not_merged():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "PUT":
            return httpx.Response(409, json={"message": "Merge conflict"})
        return httpx.Response(201, json={})

    async with httpx.AsyncClient(
        base_url="https://api.github.com", transport=httpx.MockTransport(handler)
    ) as client:
        sink = GitHubReviewAuditSink("token", "acme/kb", client)
        result = AdversarialReviewResult(
            tier="tier-1",
            outcome="accepted",
            requires_human_review=False,
            reason="Both accepted.",
        )
        assert await sink.record(published(), result) is False
