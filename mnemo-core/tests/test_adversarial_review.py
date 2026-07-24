import asyncio
import json

import httpx
import pytest

from mnemo_core.models import (
    AcceptanceCase,
    AdversarialReviewResult,
    ConcernDisposition,
    CriticReport,
    DuplicateCandidate,
    JudgeReport,
    PublishResult,
    RebuttalEntry,
    RebuttalReport,
)
from mnemo_core.pipeline.review import (
    REVIEW_OUTPUT_MAX_TOKENS,
    AdversarialReviewer,
    GitHubReviewAuditSink,
    _audit_comment,
    _critic_prompt,
    _judge_prompt,
    _rebuttal_prompt,
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


class ScriptedLLM(FakeLLM):
    """A provider that answers differently on each call, so a stage can fail
    once and succeed on its retry."""

    def __init__(self, *responses: str) -> None:
        super().__init__(responses[0])
        self.responses = list(responses)

    async def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        await super().complete(system, user, max_tokens)
        return self.responses[min(len(self.calls), len(self.responses)) - 1]


def critic_report(*, tier: str = "tier-1", blocking=None, non_blocking=None) -> str:
    return json.dumps(
        {
            "recommended_tier": tier,
            "blocking_concerns": blocking or [],
            "non_blocking_concerns": non_blocking or [],
            "rationale": "The acceptance case was tested against the document.",
        }
    )


def rebuttal_report(*entries) -> str:
    return json.dumps(
        {
            "entries": [
                {"concern_index": index, "stance": stance, "argument": argument}
                for index, stance, argument in entries
            ]
        }
    )


def judge_report(*dispositions, tier: str = "tier-1") -> str:
    return json.dumps(
        {
            "recommended_tier": tier,
            "dispositions": [
                {
                    "concern_index": index,
                    "disposition": disposition,
                    "reason": f"The record shows the concern is {disposition}.",
                }
                for index, disposition in dispositions
            ],
            "rationale": "Each blocking concern was disposed of on the record.",
        }
    )


def reviewer(critic, judge, sink=None, author=None) -> AdversarialReviewer:
    return AdversarialReviewer(
        author if author is not None else FakeLLM(rebuttal_report()),
        critic if isinstance(critic, FakeLLM) else FakeLLM(critic),
        judge if isinstance(judge, FakeLLM) else FakeLLM(judge),
        author_family="anthropic",
        author_model="claude-sonnet-4-6",
        critic_family="openai",
        critic_model="gpt-4o",
        judge_family="gemini",
        judge_model="gemini-2.5-pro",
        audit_sink=sink or FakeSink(),
    )


def published() -> PublishResult:
    return PublishResult(
        pr_url="https://github.com/acme/kb/pull/42",
        branch="mnemo/test",
        file_path="how-to/a.md",
    )


@pytest.mark.parametrize(
    "prompt", [_critic_prompt("abc123"), _rebuttal_prompt("abc123"), _judge_prompt("tier-1", "abc123")]
)
def test_review_prompts_explain_expected_pipeline_states(prompt):
    assert "`proposed` status" in prompt
    assert "`incomplete` flag" in prompt
    assert "unresolved cross-references awaiting the curator" in prompt
    assert "Tier 2 human" in prompt
    assert "pending ratification is not a defect" in prompt


@pytest.mark.parametrize(
    "prompt", [_critic_prompt("abc123"), _rebuttal_prompt("abc123"), _judge_prompt("tier-1", "abc123")]
)
def test_every_prompt_states_the_record_nonce_and_untrusted_material(prompt):
    assert "The record nonce for this call is abc123." in prompt
    assert "<<<BEGIN LABEL abc123>>>" in prompt
    assert "untrusted" in prompt


def test_critic_attacks_the_authors_case_and_separates_concerns():
    prompt = _critic_prompt("abc123")
    assert "Attempt to defeat the author's acceptance case" in prompt
    assert "blocking_concerns" in prompt
    assert "non_blocking_concerns" in prompt
    assert "DUPLICATE LEADS" in prompt


def test_rebuttal_prompt_offers_two_stances_and_permits_silence():
    prompt = _rebuttal_prompt("abc123")
    assert '"dispute"' in prompt
    assert '"no-contest"' in prompt
    assert "A concern you do not answer is undefended, which is permitted." in prompt
    assert "never defend a claim the\ndocument does not support" in prompt
    assert "Neither stance decides anything" in prompt


def test_judge_prompt_asks_for_dispositions_not_a_verdict():
    prompt = _judge_prompt("tier-1", "abc123")
    assert "- dispositions: array with one object per critic blocking concern" in prompt
    assert "The verdict is computed" in prompt and "not yours to state" in prompt
    assert '"upheld"' in prompt
    assert '"dismissed"' in prompt
    assert '"unresolved"' in prompt
    assert "do not perform another open-ended review" in prompt
    assert "Do not introduce an objection the critic did not raise" in prompt
    assert "Non-blocking\nconcerns cannot affect the outcome." in prompt
    assert "misrepresents the document or the concern it answers weighs against the author's" in prompt


def test_tier_1_and_tier_2_judges_receive_different_authority_rules():
    assert "may merge automatically" in _judge_prompt("tier-1", "abc123")
    assert "human approval is mandatory regardless" in _judge_prompt("tier-2", "abc123")


async def test_no_blocking_concerns_skips_the_rebuttal_and_accepts():
    author = FakeLLM(rebuttal_report())
    result = await reviewer(critic_report(), judge_report(), author=author).review(
        processed_doc(review_tier="tier-1"), published()
    )
    assert author.calls == []
    assert result.rebuttal is None
    assert result.outcome == "accepted"
    assert result.requires_human_review is False
    assert result.protocol_version == "adr-021"


async def test_blocking_concerns_run_the_rebuttal_and_reach_the_judge():
    author = FakeLLM(rebuttal_report((0, "dispute", "The document does say so.")))
    judge = FakeLLM(judge_report((0, "dismissed")))
    result = await reviewer(
        critic_report(blocking=["The claim is unsupported."]), judge, author=author
    ).review(processed_doc(review_tier="tier-1"), published())

    assert "[0] The claim is unsupported." in author.last_user
    assert "AUTHOR REBUTTAL" in judge.last_user
    assert "[0] dispute: The document does say so." in judge.last_user
    assert result.rebuttal is not None
    assert result.outcome == "accepted"


@pytest.mark.parametrize(
    "response",
    ["not json", rebuttal_report((3, "dispute", "Out of range.")), rebuttal_report((0, "shrug", ""))],
)
async def test_required_rebuttal_that_fails_escalates_without_calling_the_judge(response):
    author = ScriptedLLM(response, response)
    judge = FakeLLM(judge_report((0, "dismissed")))
    result = await reviewer(
        critic_report(blocking=["The claim is unsupported."]), judge, author=author
    ).review(processed_doc(review_tier="tier-1"), published())

    assert result.outcome == "escalated"
    assert result.requires_human_review is True
    assert result.merged is False
    assert result.rebuttal is None
    assert judge.calls == []
    assert "author rebuttal" in result.reason


async def test_rebuttal_may_answer_only_some_concerns():
    author = FakeLLM(rebuttal_report((1, "no-contest", "")))
    result = await reviewer(
        critic_report(blocking=["First concern.", "Second concern."]),
        judge_report((0, "dismissed"), (1, "dismissed")),
        author=author,
    ).review(processed_doc(review_tier="tier-1"), published())

    assert result.rebuttal is not None
    assert [entry.concern_index for entry in result.rebuttal.entries] == [1]
    assert result.outcome == "accepted"


async def test_duplicate_rebuttal_index_escalates():
    response = rebuttal_report((0, "dispute", "One."), (0, "no-contest", ""))
    result = await reviewer(
        critic_report(blocking=["First concern.", "Second concern."]),
        judge_report((0, "dismissed"), (1, "dismissed")),
        author=ScriptedLLM(response, response),
    ).review(processed_doc(review_tier="tier-1"), published())

    assert result.outcome == "escalated"
    assert "author rebuttal" in result.reason


@pytest.mark.parametrize(
    ("dispositions", "outcome"),
    [
        (("upheld", "dismissed"), "rejected"),
        (("unresolved", "dismissed"), "escalated"),
        (("dismissed", "dismissed"), "accepted"),
        (("upheld", "unresolved"), "rejected"),
    ],
)
async def test_outcome_is_derived_from_the_dispositions(dispositions, outcome):
    result = await reviewer(
        critic_report(blocking=["First concern.", "Second concern."]),
        judge_report(*enumerate(dispositions)),
        author=FakeLLM(rebuttal_report((0, "dispute", "It holds."), (1, "no-contest", ""))),
    ).review(processed_doc(review_tier="tier-1"), published())

    assert result.outcome == outcome
    assert result.requires_human_review is (outcome != "accepted")


@pytest.mark.parametrize(
    "dispositions",
    [
        ((0, "dismissed"),),
        ((0, "dismissed"), (0, "dismissed")),
        ((0, "dismissed"), (5, "dismissed")),
        (),
    ],
)
async def test_dispositions_that_do_not_match_the_challenge_escalate(dispositions):
    response = judge_report(*dispositions)
    result = await reviewer(
        critic_report(blocking=["First concern.", "Second concern."]),
        ScriptedLLM(response, response),
        author=FakeLLM(rebuttal_report((0, "no-contest", ""))),
    ).review(processed_doc(review_tier="tier-1"), published())

    assert result.outcome == "escalated"
    assert result.judge is None
    assert "judge" in result.reason


async def test_invalid_stage_output_is_retried_once_before_escalating():
    critic = ScriptedLLM("not json", critic_report())
    result = await reviewer(critic, judge_report()).review(
        processed_doc(review_tier="tier-1"), published()
    )
    assert len(critic.calls) == 2
    assert result.critic is not None
    assert result.outcome == "accepted"


async def test_a_hung_stage_times_out_and_escalates():
    class HangingLLM(FakeLLM):
        async def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
            await asyncio.sleep(10)
            return self.response

    subject = AdversarialReviewer(
        FakeLLM(rebuttal_report()),
        HangingLLM(critic_report()),
        FakeLLM(judge_report()),
        author_family="anthropic",
        critic_family="openai",
        judge_family="gemini",
        audit_sink=FakeSink(),
        timeout_seconds=0.01,
    )
    result = await subject.review(processed_doc(), published())
    assert result.outcome == "escalated"
    assert "critic" in result.reason


async def test_tier_1_acceptance_can_merge():
    sink = FakeSink(merged=True)
    result = await reviewer(critic_report(), judge_report(), sink).review(
        processed_doc(review_tier="tier-1"), published()
    )
    assert result.outcome == "accepted"
    assert result.requires_human_review is False
    assert result.merged is True
    assert result.critic is not None
    assert result.judge is not None


async def test_missing_acceptance_case_fails_closed_without_model_calls():
    author = FakeLLM(rebuttal_report())
    critic = FakeLLM(critic_report())
    judge = FakeLLM(judge_report())
    result = await reviewer(critic, judge, author=author).review(
        processed_doc(acceptance_case=None), published()
    )
    assert result.outcome == "escalated"
    assert result.requires_human_review is True
    assert "author acceptance case" in result.reason
    assert author.calls == []
    assert critic.calls == []
    assert judge.calls == []


async def test_invalid_critic_response_escalates_without_calling_judge():
    critic = FakeLLM("not json")
    judge = FakeLLM(judge_report())
    result = await reviewer(critic, judge).review(processed_doc(), published())
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


async def test_judge_receives_the_whole_record_inside_nonce_fences():
    critic = FakeLLM(critic_report(blocking=["Unsupported claim."]))
    judge = FakeLLM(judge_report((0, "upheld")))
    doc = processed_doc(
        acceptance_case=ACCEPTANCE_CASE,
        duplicate_candidates=[DuplicateCandidate(path="how-to/b.md", score=0.11)],
    )
    await reviewer(critic, judge, author=FakeLLM(rebuttal_report((0, "no-contest", "")))).review(
        doc, published()
    )

    assert '"The proposal is accurate."' in judge.last_user
    assert "Unsupported claim." in judge.last_user
    nonce = judge.last_system.split("The record nonce for this call is ")[1].split(".")[0]
    for label in ("DOCUMENT", "AUTHOR ACCEPTANCE CASE", "CRITIC CHALLENGE", "AUTHOR REBUTTAL"):
        assert f"<<<BEGIN {label} {nonce}>>>" in judge.last_user
        assert f"<<<END {label} {nonce}>>>" in judge.last_user
    assert critic.last_max_tokens == REVIEW_OUTPUT_MAX_TOKENS
    assert judge.last_max_tokens == REVIEW_OUTPUT_MAX_TOKENS
    # Leads reach the critic only; the judge must not open new ground.
    assert "DUPLICATE LEADS" in critic.last_user
    assert "how-to/b.md (raw distance 0.11)" in critic.last_user
    assert "DUPLICATE LEADS" not in judge.last_user


async def test_each_stage_gets_its_own_nonce():
    critic = FakeLLM(critic_report(blocking=["Unsupported claim."]))
    author = FakeLLM(rebuttal_report((0, "dispute", "It is supported.")))
    judge = FakeLLM(judge_report((0, "dismissed")))
    await reviewer(critic, judge, author=author).review(processed_doc(), published())

    nonces = {
        stage.last_system.split("The record nonce for this call is ")[1].split(".")[0]
        for stage in (critic, author, judge)
    }
    assert len(nonces) == 3


async def test_oversized_concerns_are_bounded_without_discarding_reports():
    result = await reviewer(
        critic_report(blocking=["x" * 501]),
        judge_report((0, "dismissed")),
        author=FakeLLM(rebuttal_report((0, "dispute", "y" * 1_100))),
    ).review(processed_doc(), published())
    assert result.critic is not None
    assert result.critic.blocking_concerns == ["x" * 500]
    assert result.rebuttal is not None
    assert result.rebuttal.entries[0].argument == "y" * 1_000


@pytest.mark.parametrize(
    ("disposition", "outcome", "reason"),
    [
        ("dismissed", "accepted", "The judge recommends accept."),
        ("upheld", "rejected", "The judge recommends reject."),
        ("unresolved", "escalated", "The judge could not make a Tier 2 recommendation."),
    ],
)
async def test_tier_2_never_auto_merges_whatever_the_outcome(disposition, outcome, reason):
    sink = FakeSink(merged=False)
    result = await reviewer(
        critic_report(tier="tier-2", blocking=["A governance concern."]),
        judge_report((0, disposition), tier="tier-2"),
        sink,
        author=FakeLLM(rebuttal_report((0, "dispute", "It is sound."))),
    ).review(processed_doc(review_tier="tier-2"), published())
    assert result.outcome == outcome
    assert result.requires_human_review is True
    assert result.merged is False
    assert reason in result.reason


async def test_either_review_stage_can_upgrade_tier_1_to_tier_2():
    result = await reviewer(
        critic_report(), judge_report(tier="tier-2")
    ).review(processed_doc(review_tier="tier-1"), published())
    assert result.tier == "tier-2"
    assert result.requires_human_review is True
    assert result.merged is False


@pytest.mark.parametrize(
    ("author_family", "critic_family", "judge_family"),
    [
        ("anthropic", "openai", "OPENAI"),
        ("anthropic", "ANTHROPIC", "gemini"),
        ("openai", "gemini", "openai"),
    ],
)
def test_a_shared_provider_family_is_rejected(author_family, critic_family, judge_family):
    with pytest.raises(ValueError, match="different provider families"):
        AdversarialReviewer(
            FakeLLM(rebuttal_report()),
            FakeLLM(critic_report()),
            FakeLLM(judge_report()),
            author_family=author_family,
            critic_family=critic_family,
            judge_family=judge_family,
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


def test_critic_blocking_concerns_are_capped_at_ten():
    with pytest.raises(ValueError, match="blocking_concerns"):
        CriticReport(
            provider_family="openai",
            recommended_tier="tier-1",
            blocking_concerns=[f"Concern {index}." for index in range(11)],
            rationale="Too many concerns were raised.",
        )


async def test_audit_failure_does_not_turn_adjudication_into_error():
    class FailingSink:
        async def record(self, published, result):
            raise httpx.HTTPStatusError(
                "comment failed",
                request=httpx.Request("POST", published.pr_url),
                response=httpx.Response(503),
            )

    result = await reviewer(critic_report(), judge_report(), FailingSink()).review(
        processed_doc(review_tier="tier-1"), published()
    )
    assert result.outcome == "accepted"
    assert result.merged is False


def accepted_result(*, tier="tier-1", human=False) -> AdversarialReviewResult:
    return AdversarialReviewResult(
        tier=tier,
        acceptance_case=ACCEPTANCE_CASE,
        critic=CriticReport(
            provider_family="openai",
            model="gpt-4o",
            recommended_tier=tier,
            rationale="No blocking challenge survived.",
        ),
        judge=JudgeReport(
            provider_family="gemini",
            model="gemini-2.5-pro",
            recommended_tier=tier,
            rationale="The acceptance case survived challenge.",
        ),
        outcome="accepted",
        requires_human_review=human,
        reason="Accepted.",
    )


def contested_result() -> AdversarialReviewResult:
    return AdversarialReviewResult(
        tier="tier-1",
        acceptance_case=ACCEPTANCE_CASE,
        critic=CriticReport(
            provider_family="openai",
            model="gpt-4o",
            recommended_tier="tier-1",
            blocking_concerns=["The command is unsafe.", "The provenance is thin."],
            rationale="Two blocking grounds were found.",
        ),
        rebuttal=RebuttalReport(
            provider_family="anthropic",
            model="claude-sonnet-4-6",
            entries=[
                RebuttalEntry(
                    concern_index=0, stance="dispute", argument="The command is scoped to a copy."
                ),
                RebuttalEntry(concern_index=1, stance="no-contest"),
            ],
        ),
        judge=JudgeReport(
            provider_family="gemini",
            model="gemini-2.5-pro",
            recommended_tier="tier-1",
            dispositions=[
                ConcernDisposition(
                    concern_index=0, disposition="dismissed", reason="The rebuttal is borne out."
                ),
                ConcernDisposition(
                    concern_index=1, disposition="upheld", reason="No source is given."
                ),
            ],
            rationale="One ground survived.",
        ),
        outcome="rejected",
        requires_human_review=True,
        reason="The judge rejected this Tier 1 contribution.",
    )


def test_audit_comment_formats_acceptance_case_as_markdown_not_json():
    comment = _audit_comment(accepted_result())

    assert "#### Claims\n\n- The proposal is accurate." in comment
    assert "#### Evidence\n\n- The document supplies supporting detail." in comment
    assert "#### Diataxis fit\n\nIt fits its selected Diataxis type." in comment
    assert "#### Anticipated objections\n\n- None" in comment
    assert '"claims":' not in comment


def test_audit_comment_records_the_rebuttal_and_dispositions():
    comment = _audit_comment(contested_result())

    assert "**Protocol:** adr-021" in comment
    assert "**Effective tier:** tier-1" in comment
    assert "**Outcome:** rejected (derived from the dispositions)" in comment
    assert "### Critic challenge (openai / gpt-4o)" in comment
    assert "- [0] The command is unsafe." in comment
    assert "### Author rebuttal (anthropic / claude-sonnet-4-6)" in comment
    assert "dispute: The command is scoped to a copy." in comment
    assert "no-contest: No argument offered." in comment
    assert "### Neutral adjudication (gemini / gemini-2.5-pro) — rejected" in comment
    assert "| Concern | Disposition | Reason |" in comment
    assert "| [0] The command is unsafe. | dismissed | The rebuttal is borne out. |" in comment
    assert "| [1] The provenance is thin. | upheld | No source is given. |" in comment


def test_audit_comment_distinguishes_a_skipped_rebuttal_from_a_missing_one():
    assert "No blocking concerns; no rebuttal required." in _audit_comment(accepted_result())

    escalated = contested_result().model_copy(update={"rebuttal": None})
    assert "### Author rebuttal\n\nUnavailable or invalid response." in _audit_comment(escalated)


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
