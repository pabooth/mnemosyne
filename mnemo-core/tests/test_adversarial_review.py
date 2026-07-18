import json

import httpx
import pytest

from mnemo_core.models import (
    AcceptanceCase,
    AdversarialReviewResult,
    CriticReport,
    JudgeReport,
    PublishResult,
)
from mnemo_core.pipeline.review import (
    AdversarialReviewer,
    GitHubReviewAuditSink,
    _critic_prompt,
    _judge_prompt,
)
from tests.conftest import FakeLLM, processed_doc

ACCEPTANCE_CASE = AcceptanceCase(
    claims=["The proposal is accurate."],
    evidence=["The document supplies supporting detail."],
    diataxis_fit="It fits its selected Diataxis type.",
)


class FakeSink:
    def __init__(self, merged: bool = False) -> None:
        self.result = None
        self.merged = merged

    async def record(self, published, result):
        self.result = result
        return self.merged


def critic_report(*, tier: str = "tier-1", blocking=None, non_blocking=None) -> str:
    return json.dumps(
        {
            "recommended_tier": tier,
            "blocking_concerns": blocking or [],
            "non_blocking_concerns": non_blocking or [],
            "rationale": "The acceptance case was tested against the document.",
        }
    )


def judge_report(verdict: str, *, tier: str = "tier-1", concerns=None) -> str:
    return json.dumps(
        {
            "verdict": verdict,
            "recommended_tier": tier,
            "concerns": concerns or [],
            "rationale": f"The decisive evidence supports {verdict}.",
        }
    )


def reviewer(critic: str, judge: str, sink=None) -> AdversarialReviewer:
    return AdversarialReviewer(
        FakeLLM(critic),
        FakeLLM(judge),
        critic_family="openai",
        judge_family="gemini",
        audit_sink=sink or FakeSink(),
    )


def published() -> PublishResult:
    return PublishResult(
        pr_url="https://github.com/acme/kb/pull/42",
        branch="mnemo/test",
        file_path="how-to/a.md",
    )


@pytest.mark.parametrize("prompt", [_critic_prompt(), _judge_prompt("tier-1")])
def test_review_prompts_explain_expected_pipeline_states(prompt):
    assert "`proposed` status" in prompt
    assert "`incomplete` flag" in prompt
    assert "unresolved cross-references awaiting the curator" in prompt
    assert "Tier 2 human" in prompt
    assert "pending ratification is not a defect" in prompt


def test_critic_attacks_the_authors_case_and_separates_concerns():
    prompt = _critic_prompt()
    assert "Attempt to defeat the author's acceptance case" in prompt
    assert "blocking_concerns" in prompt
    assert "non_blocking_concerns" in prompt


def test_tier_1_judge_can_accept_reject_or_escalate():
    prompt = _judge_prompt("tier-1")
    assert '"accept", "reject", or "escalate"' in prompt


def test_tier_2_judge_only_recommends_accept_or_reject():
    prompt = _judge_prompt("tier-2")
    assert '"accept" or "reject" as a recommendation' in prompt


async def test_tier_1_judge_acceptance_can_merge():
    sink = FakeSink(merged=True)
    result = await reviewer(critic_report(), judge_report("accept"), sink).review(
        processed_doc(review_tier="tier-1"), published()
    )
    assert result.outcome == "accepted"
    assert result.requires_human_review is False
    assert result.merged is True
    assert result.critic is not None
    assert result.judge is not None


@pytest.mark.parametrize(
    ("verdict", "outcome"), [("reject", "rejected"), ("escalate", "escalated")]
)
async def test_tier_1_non_accept_decisions_require_human_review(verdict, outcome):
    result = await reviewer(critic_report(), judge_report(verdict)).review(
        processed_doc(review_tier="tier-1"), published()
    )
    assert result.outcome == outcome
    assert result.requires_human_review is True
    assert result.merged is False


async def test_missing_acceptance_case_fails_closed_without_model_calls():
    critic = FakeLLM(critic_report())
    judge = FakeLLM(judge_report("accept"))
    subject = AdversarialReviewer(
        critic,
        judge,
        critic_family="openai",
        judge_family="gemini",
        audit_sink=FakeSink(),
    )
    result = await subject.review(processed_doc(acceptance_case=None), published())
    assert result.outcome == "escalated"
    assert result.requires_human_review is True
    assert "author acceptance case" in result.reason
    assert critic.calls == []
    assert judge.calls == []


async def test_invalid_critic_response_escalates_without_calling_judge():
    critic = FakeLLM("not json")
    judge = FakeLLM(judge_report("accept"))
    subject = AdversarialReviewer(
        critic,
        judge,
        critic_family="openai",
        judge_family="gemini",
        audit_sink=FakeSink(),
    )
    result = await subject.review(processed_doc(), published())
    assert result.outcome == "escalated"
    assert result.critic is None
    assert result.judge is None
    assert judge.calls == []
    assert "critic" in result.reason


async def test_invalid_judge_response_preserves_critic_and_escalates():
    result = await reviewer(critic_report(), "not json").review(processed_doc(), published())
    assert result.outcome == "escalated"
    assert result.critic is not None
    assert result.judge is None
    assert "judge" in result.reason


async def test_judge_receives_document_acceptance_case_and_critic_challenge():
    critic = FakeLLM(critic_report(blocking=["Unsupported claim."]))
    judge = FakeLLM(judge_report("reject"))
    subject = AdversarialReviewer(
        critic,
        judge,
        critic_family="openai",
        judge_family="gemini",
        audit_sink=FakeSink(),
    )
    doc = processed_doc(acceptance_case=ACCEPTANCE_CASE)
    await subject.review(doc, published())
    assert '"The proposal is accurate."' in judge.last_user
    assert "CRITIC CHALLENGE" in judge.last_user
    assert "Unsupported claim." in judge.last_user


async def test_oversized_concerns_are_bounded_without_discarding_reports():
    result = await reviewer(
        critic_report(blocking=["x" * 501]), judge_report("accept", concerns=["y" * 501])
    ).review(processed_doc(), published())
    assert result.critic is not None
    assert result.critic.blocking_concerns == ["x" * 500]
    assert result.judge is not None
    assert result.judge.concerns == ["y" * 500]


@pytest.mark.parametrize("verdict", ["accept", "reject"])
async def test_tier_2_judge_verdict_is_a_human_recommendation(verdict):
    result = await reviewer(
        critic_report(tier="tier-2"), judge_report(verdict, tier="tier-2")
    ).review(processed_doc(review_tier="tier-2"), published())
    assert result.outcome == ("accepted" if verdict == "accept" else "rejected")
    assert result.requires_human_review is True
    assert result.merged is False
    assert f"recommends {verdict}" in result.reason


async def test_either_review_stage_can_upgrade_tier_1_to_tier_2():
    result = await reviewer(
        critic_report(), judge_report("accept", tier="tier-2")
    ).review(processed_doc(review_tier="tier-1"), published())
    assert result.tier == "tier-2"
    assert result.requires_human_review is True
    assert result.merged is False


def test_same_critic_and_judge_family_is_rejected():
    with pytest.raises(ValueError, match="different provider families"):
        AdversarialReviewer(
            FakeLLM(critic_report()),
            FakeLLM(judge_report("accept")),
            critic_family="openai",
            judge_family="OPENAI",
            audit_sink=FakeSink(),
        )


@pytest.mark.parametrize("concern", ["", "x" * 501])
def test_critic_concerns_are_bounded(concern):
    with pytest.raises(ValueError, match="concerns"):
        CriticReport(
            provider_family="openai",
            recommended_tier="tier-1",
            blocking_concerns=[concern],
            rationale="A concern was found.",
        )


async def test_audit_failure_does_not_turn_adjudication_into_error():
    class FailingSink:
        async def record(self, published, result):
            raise httpx.HTTPStatusError(
                "comment failed",
                request=httpx.Request("POST", published.pr_url),
                response=httpx.Response(503),
            )

    result = await reviewer(
        critic_report(), judge_report("accept"), FailingSink()
    ).review(processed_doc(review_tier="tier-1"), published())
    assert result.outcome == "accepted"
    assert result.merged is False


def accepted_result(*, tier="tier-1", human=False) -> AdversarialReviewResult:
    return AdversarialReviewResult(
        tier=tier,
        acceptance_case=ACCEPTANCE_CASE,
        critic=CriticReport(
            provider_family="openai",
            recommended_tier=tier,
            rationale="No blocking challenge survived.",
        ),
        judge=JudgeReport(
            provider_family="gemini",
            verdict="accept",
            recommended_tier=tier,
            rationale="The acceptance case survived challenge.",
        ),
        outcome="accepted",
        requires_human_review=human,
        reason="Accepted.",
    )


async def test_github_sink_comments_then_merges_accepted_tier_1():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200 if request.method == "PUT" else 201, json={"merged": True})

    async with httpx.AsyncClient(
        base_url="https://api.github.com", transport=httpx.MockTransport(handler)
    ) as client:
        sink = GitHubReviewAuditSink("token", "acme/kb", client)
        assert await sink.record(published(), accepted_result()) is True

    assert [request.method for request in requests] == ["POST", "PUT"]


async def test_github_sink_never_merges_tier_2():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json={})

    async with httpx.AsyncClient(
        base_url="https://api.github.com", transport=httpx.MockTransport(handler)
    ) as client:
        sink = GitHubReviewAuditSink("token", "acme/kb", client)
        assert await sink.record(published(), accepted_result(tier="tier-2", human=True)) is False

    assert [request.method for request in requests] == ["POST"]
