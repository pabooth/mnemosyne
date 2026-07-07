import base64
import hashlib
import hmac
import json

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request

from ...config import Settings, get_settings
from ...models import DocumentInput
from ...pipeline.runner import PipelineRunner
from ..deps import get_runner

router = APIRouter(prefix="/webhooks")


@router.post("/github", status_code=202)
async def github_push(
    request: Request,
    cfg: Settings = Depends(get_settings),
    runner: PipelineRunner = Depends(get_runner),
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
) -> dict:
    body = await request.body()
    _verify_signature(body, x_hub_signature_256, cfg.github_webhook_secret)
    if x_github_event != "push":
        return {"accepted": False, "reason": "Only push events are processed"}

    payload = json.loads(body)
    if payload.get("ref") != f"refs/heads/{cfg.github_webhook_branch}":
        return {"accepted": False, "reason": "Push was for an unwatched branch"}
    repo = payload.get("repository", {}).get("full_name", "")
    if not repo or (cfg.github_repo and repo != cfg.github_repo):
        raise HTTPException(status_code=400, detail="Unexpected repository")

    paths = _document_paths(payload, cfg)
    documents = await _fetch_documents(repo, payload.get("after", ""), paths, cfg)
    jobs = [
        request.app.state.job_manager.submit(
            "ingest",
            "github-webhook",
            DocumentInput(title=path.rsplit("/", 1)[-1].removesuffix(".md"), content=content),
            runner,
        )
        for path, content in documents
    ]
    return {"accepted": True, "jobs": jobs}


def _verify_signature(body: bytes, signature: str | None, secret: str) -> None:
    if not secret:
        raise HTTPException(status_code=503, detail="GITHUB_WEBHOOK_SECRET is not configured")
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


def _document_paths(payload: dict, cfg: Settings) -> list[str]:
    paths: set[str] = set()
    prefix = cfg.github_webhook_path_prefix.strip("/")
    for commit in payload.get("commits", []):
        for path in commit.get("added", []) + commit.get("modified", []):
            if not path.lower().endswith((".md", ".markdown")):
                continue
            if prefix and not path.startswith(f"{prefix}/"):
                continue
            paths.add(path)
    return sorted(paths)[: cfg.github_webhook_max_files]


async def _fetch_documents(
    repo: str,
    ref: str,
    paths: list[str],
    cfg: Settings,
) -> list[tuple[str, str]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if cfg.github_token:
        headers["Authorization"] = f"Bearer {cfg.github_token}"
    results: list[tuple[str, str]] = []
    async with httpx.AsyncClient(
        base_url="https://api.github.com", headers=headers, timeout=30
    ) as client:
        for path in paths:
            response = await client.get(f"/repos/{repo}/contents/{path}", params={"ref": ref})
            response.raise_for_status()
            data = response.json()
            if data.get("encoding") != "base64":
                continue
            content = base64.b64decode(data["content"]).decode("utf-8")
            results.append((path, content))
    return results
