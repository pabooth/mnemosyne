import asyncio

import pytest

from mnemo_core.api.deps import build_runner
from mnemo_core.config import Settings
from mnemo_core.jobs import JobStore
from mnemo_core.models import AdversarialReviewResult, ProcessedDocument
from mnemo_core.pipeline import ProcessingError
from mnemo_core.pipeline.dedup import DuplicateChecker
from mnemo_core.vector.base import VectorRecord
from mnemo_core.vector.sqlite_vec import SqliteVecIndex
from tests.conftest import (
    FakeEmbedding,
    FakeLLM,
    FakePublisher,
    llm_json_response,
    processed_doc,
    sample_input,
)


async def test_process_does_not_publish():
    llm = FakeLLM(llm_json_response())
    publisher = FakePublisher()
    runner = build_runner(publisher=publisher, llm=llm)

    doc = await runner.process(sample_input())
    assert doc.title == "Deploy the app"
    assert publisher.last_doc is None


def test_build_runner_constructs_reviewer_when_enabled():
    runner = build_runner(
        Settings(
            github_token="token",
            github_repo="acme/kb",
            adversarial_review_enabled=True,
        ),
        publisher=FakePublisher(),
        llm=FakeLLM(llm_json_response()),
    )

    assert runner._reviewer is not None


def test_build_runner_skips_reviewer_when_disabled():
    runner = build_runner(
        Settings(adversarial_review_enabled=False),
        publisher=FakePublisher(),
        llm=FakeLLM(llm_json_response()),
    )

    assert runner._reviewer is None


async def test_process_without_dedup_leaves_candidates_empty():
    llm = FakeLLM(llm_json_response())
    runner = build_runner(publisher=FakePublisher(), llm=llm)

    doc = await runner.process(sample_input())

    assert doc.duplicate_candidates == []


async def test_process_attaches_duplicate_candidates_when_dedup_configured(tmp_path):
    vector_index = SqliteVecIndex(path=str(tmp_path / "vectors.db"), dimension=4)
    vector_index.upsert(
        [
            VectorRecord(
                id="how-to/deploy.md#0",
                content_hash="hash-a",
                embedding=[0.0, 0.0, 0.0, 0.0],
                metadata={"path": "how-to/deploy.md"},
            )
        ]
    )
    dedup = DuplicateChecker(vector_index, FakeEmbedding(dimension=4), max_distance=100.0)
    runner = build_runner(publisher=FakePublisher(), llm=FakeLLM(llm_json_response()), dedup=dedup)

    doc = await runner.process(sample_input())

    assert len(doc.duplicate_candidates) == 1
    assert doc.duplicate_candidates[0].path == "how-to/deploy.md"


async def test_process_succeeds_when_dedup_check_fails():
    class FailingDedup:
        async def find_candidates(self, doc):
            raise RuntimeError("embedding provider unavailable")

    runner = build_runner(
        publisher=FakePublisher(),
        llm=FakeLLM(llm_json_response()),
        dedup=FailingDedup(),
    )

    doc = await runner.process(sample_input())

    assert doc.duplicate_candidates == []


async def test_run_processes_then_publishes():
    llm = FakeLLM(llm_json_response())
    publisher = FakePublisher()
    runner = build_runner(publisher=publisher, llm=llm)

    result = await runner.run(sample_input())

    assert publisher.last_doc is not None
    assert publisher.last_doc.title == "Deploy the app"
    assert result.publish.pr_url == "https://github.com/acme/kb/pull/1"


async def test_publish_attaches_review_and_run_passes_it_through(tmp_path):
    class StubReviewer:
        def __init__(self):
            self.calls = []

        async def review(self, doc, published):
            self.calls.append((doc, published))
            return AdversarialReviewResult(
                tier=doc.review_tier,
                outcome="escalated",
                requires_human_review=True,
                reason="Test escalation.",
            )

    reviewer = StubReviewer()
    runner = build_runner(
        publisher=FakePublisher(),
        llm=FakeLLM(llm_json_response()),
        reviewer=reviewer,
        review_store=JobStore(str(tmp_path / "state.db")),
    )

    published = await runner.publish(processed_doc())
    assert published.review is not None
    assert published.review.reason == "Test escalation."

    ingested = await runner.run(sample_input())
    assert ingested.review == ingested.publish.review
    # The PR URL is the durable idempotency key, so retrying the same
    # publication reuses its completed review instead of auditing twice.
    assert len(reviewer.calls) == 1


async def test_review_continues_when_client_cancels_after_publish(tmp_path):
    class SlowReviewer:
        def __init__(self):
            self.started = asyncio.Event()
            self.release = asyncio.Event()
            self.completed = asyncio.Event()

        async def review(self, doc, published):
            self.started.set()
            await self.release.wait()
            self.completed.set()
            return AdversarialReviewResult(
                tier=doc.review_tier,
                outcome="escalated",
                requires_human_review=True,
                reason="Test escalation.",
            )

    reviewer = SlowReviewer()
    runner = build_runner(
        publisher=FakePublisher(),
        llm=FakeLLM(llm_json_response()),
        reviewer=reviewer,
        review_store=JobStore(str(tmp_path / "state.db")),
    )

    request = asyncio.create_task(runner.publish(processed_doc()))
    await asyncio.wait_for(reviewer.started.wait(), timeout=1)
    request.cancel()
    with pytest.raises(asyncio.CancelledError):
        await request

    reviewer.release.set()
    await asyncio.wait_for(reviewer.completed.wait(), timeout=1)


async def test_publish_can_return_while_review_continues(tmp_path):
    class SlowReviewer:
        def __init__(self):
            self.started = asyncio.Event()
            self.release = asyncio.Event()
            self.completed = asyncio.Event()

        async def review(self, doc, published):
            self.started.set()
            await self.release.wait()
            self.completed.set()
            return AdversarialReviewResult(
                tier=doc.review_tier,
                outcome="escalated",
                requires_human_review=True,
                reason="Test escalation.",
            )

    reviewer = SlowReviewer()
    runner = build_runner(
        publisher=FakePublisher(),
        llm=FakeLLM(llm_json_response()),
        reviewer=reviewer,
        review_store=JobStore(str(tmp_path / "state.db")),
    )

    published = await runner.publish(processed_doc(), wait_for_review=False)

    assert published.review is None
    await asyncio.wait_for(reviewer.started.wait(), timeout=1)
    reviewer.release.set()
    await asyncio.wait_for(reviewer.completed.wait(), timeout=1)


async def test_pending_review_resumes_after_restart(tmp_path):
    class StubReviewer:
        def __init__(self):
            self.completed = asyncio.Event()

        async def review(self, doc, published):
            self.completed.set()
            return AdversarialReviewResult(
                tier=doc.review_tier,
                outcome="escalated",
                requires_human_review=True,
                reason="Recovered review.",
            )

    path = str(tmp_path / "state.db")
    store = JobStore(path)
    published = FakePublisher().result
    store.create_review_job(processed_doc(), published)
    assert store.claim_review_job(published.pr_url)

    reviewer = StubReviewer()
    restarted_store = JobStore(path)
    build_runner(
        publisher=FakePublisher(),
        llm=FakeLLM(llm_json_response()),
        reviewer=reviewer,
        review_store=restarted_store,
    )

    await asyncio.wait_for(reviewer.completed.wait(), timeout=1)
    for _ in range(10):
        job = restarted_store.get_review_job(published.pr_url)
        if job["status"] == "succeeded":
            break
        await asyncio.sleep(0)
    assert job["result"].reason == "Recovered review."


def test_legacy_processed_document_defaults_to_human_gated_tier():
    payload = processed_doc().model_dump(exclude={"review_tier"})
    assert ProcessedDocument.model_validate(payload).review_tier == "tier-2"


async def test_process_raises_pipeline_error_on_bad_json():
    llm = FakeLLM("not-json")
    publisher = FakePublisher()
    runner = build_runner(publisher=publisher, llm=llm)

    with pytest.raises(ProcessingError):
        await runner.process(sample_input())
