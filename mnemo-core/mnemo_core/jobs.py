import asyncio
import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from .models import DocumentInput
from .pipeline.runner import PipelineRunner

JobKind = Literal["process", "ingest", "index_trigger", "index_reconcile"]


def _now() -> str:
    return datetime.now(UTC).isoformat()


class JobStore:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    input_json TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status INTEGER NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            columns = {
                row["name"] for row in db.execute("PRAGMA table_info(jobs)").fetchall()
            }
            if "attempts" not in columns:
                db.execute("ALTER TABLE jobs ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0")
            db.execute(
                "UPDATE jobs SET status = 'failed', error = 'Service restarted while job was running', updated_at = ? "
                "WHERE status IN ('queued', 'running')",
                (_now(),),
            )

    def create_job(self, kind: JobKind, actor: str, payload: BaseModel) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        timestamp = _now()
        with self._connect() as db:
            db.execute(
                "INSERT INTO jobs "
                "(id, kind, status, actor, created_at, updated_at, input_json, result_json, error, attempts) "
                "VALUES (?, ?, 'queued', ?, ?, ?, ?, NULL, NULL, 0)",
                (job_id, kind, actor, timestamp, timestamp, payload.model_dump_json()),
            )
        return self.get_job(job_id)

    def update_job(
        self,
        job_id: str,
        status: str,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        attempts: int | None = None,
    ) -> None:
        with self._connect() as db:
            if attempts is None:
                db.execute(
                    "UPDATE jobs SET status = ?, updated_at = ?, result_json = ?, error = ? WHERE id = ?",
                    (
                        status,
                        _now(),
                        json.dumps(result) if result is not None else None,
                        error,
                        job_id,
                    ),
                )
            else:
                db.execute(
                    "UPDATE jobs SET status = ?, updated_at = ?, result_json = ?, error = ?, attempts = ? "
                    "WHERE id = ?",
                    (
                        status,
                        _now(),
                        json.dumps(result) if result is not None else None,
                        error,
                        attempts,
                        job_id,
                    ),
                )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._job_dict(row) if row else None

    def list_jobs(self, actor: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT * FROM jobs"
        params: list[Any] = []
        if actor:
            query += " WHERE actor = ?"
            params.append(actor)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as db:
            rows = db.execute(query, params).fetchall()
        return [self._job_dict(row) for row in rows]

    def record_audit(
        self,
        actor: str,
        action: str,
        status: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO audit_events (actor, action, status, details_json, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (actor, action, status, json.dumps(details or {}), _now()),
            )

    def list_audit(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "id": row["id"],
                "actor": row["actor"],
                "action": row["action"],
                "status": row["status"],
                "details": json.loads(row["details_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    @staticmethod
    def _job_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "kind": row["kind"],
            "status": row["status"],
            "actor": row["actor"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "error": row["error"],
            "attempts": row["attempts"],
        }


class JobManager:
    def __init__(
        self,
        store: JobStore,
        *,
        max_attempts: int = 2,
        retry_base_seconds: float = 1,
    ) -> None:
        self.store = store
        self.max_attempts = max(1, max_attempts)
        self.retry_base_seconds = max(0, retry_base_seconds)
        self._tasks: dict[str, asyncio.Task] = {}

    def submit(
        self,
        kind: JobKind,
        actor: str,
        payload: BaseModel,
        runner: PipelineRunner | None = None,
    ) -> dict[str, Any]:
        job = self.store.create_job(kind, actor, payload)
        task = asyncio.create_task(self._run(job["id"], kind, payload, runner))
        self._tasks[job["id"]] = task
        task.add_done_callback(lambda _: self._tasks.pop(job["id"], None))
        return job

    async def _run(
        self,
        job_id: str,
        kind: JobKind,
        payload: BaseModel,
        runner: PipelineRunner | None,
    ) -> None:
        for attempt in range(1, self.max_attempts + 1):
            self.store.update_job(job_id, "running", attempts=attempt)
            try:
                result = await self._execute(kind, payload, runner)
                self.store.update_job(
                    job_id,
                    "succeeded",
                    result=result.model_dump(mode="json"),
                    attempts=attempt,
                )
                return
            except asyncio.CancelledError:
                self.store.update_job(job_id, "cancelled", error="Cancelled", attempts=attempt)
                raise
            except NotImplementedError as error:
                # Contract stubs (ADR-013): not a transient failure, so never retry.
                self.store.update_job(
                    job_id,
                    "failed",
                    error=str(error)[:2_000],
                    attempts=attempt,
                )
                return
            except Exception as error:
                if attempt >= self.max_attempts:
                    self.store.update_job(
                        job_id,
                        "failed",
                        error=str(error)[:2_000],
                        attempts=attempt,
                    )
                    return
                self.store.update_job(
                    job_id,
                    "retrying",
                    error=str(error)[:2_000],
                    attempts=attempt,
                )
                await asyncio.sleep(self.retry_base_seconds * (2 ** (attempt - 1)))

    async def _execute(
        self,
        kind: JobKind,
        payload: BaseModel,
        runner: PipelineRunner | None,
    ) -> BaseModel:
        if kind in ("index_trigger", "index_reconcile"):
            raise NotImplementedError(f"Job kind '{kind}' is a contract stub with no implementation yet")
        if runner is None:
            raise NotImplementedError(f"Job kind '{kind}' requires a pipeline runner")
        if not isinstance(payload, DocumentInput):
            raise NotImplementedError(f"Job kind '{kind}' requires a DocumentInput payload")
        if kind == "process":
            return await runner.process(payload)
        return await runner.run(payload)

    def cancel(self, job_id: str) -> bool:
        task = self._tasks.get(job_id)
        if not task:
            return False
        task.cancel()
        return True
