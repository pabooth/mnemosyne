import ipaddress
import socket
from typing import Literal
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field, HttpUrl

from ...config import Settings, get_settings
from ...models import DocumentInput
from ...pipeline.runner import PipelineRunner
from ..deps import get_runner

router = APIRouter(prefix="/sources")


class UrlSource(BaseModel):
    url: HttpUrl
    title: str = Field(default="", max_length=200)
    owner: str = Field(default="", max_length=100)


class GitHubSource(BaseModel):
    path: str = Field(min_length=1, max_length=500, pattern=r"^[\w./ -]+$")
    ref: str = Field(default="", max_length=200)
    owner: str = Field(default="", max_length=100)


@router.post("/file", status_code=202)
async def upload_file(
    request: Request,
    file: UploadFile = File(),
    kind: Literal["process", "ingest"] = Query(default="ingest"),
    runner: PipelineRunner = Depends(get_runner),
    cfg: Settings = Depends(get_settings),
) -> dict:
    if file.content_type not in {
        "text/plain",
        "text/markdown",
        "text/x-markdown",
        "application/octet-stream",
    }:
        raise HTTPException(status_code=415, detail="Only plain text and Markdown are supported")
    content = await file.read(cfg.request_max_body_bytes + 1)
    if len(content) > cfg.request_max_body_bytes:
        raise HTTPException(status_code=413, detail="Uploaded document is too large")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Uploaded document must be UTF-8") from None
    document = DocumentInput(
        title=(file.filename or "").rsplit("/", 1)[-1].rsplit(".", 1)[0],
        content=text,
    )
    return request.app.state.job_manager.submit(
        kind, getattr(request.state, "actor", "shared-token"), document, runner
    )


def _is_public_host(host: str) -> bool:
    try:
        addrinfo = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False

    for info in addrinfo:
        ip_str = info[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        ):
            return False
    return True


def _resolve_public_ip(host: str) -> str:
    try:
        addrinfo = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise HTTPException(status_code=403, detail="Unable to resolve URL host") from exc

    for info in addrinfo:
        ip_str = info[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        ):
            continue
        return ip_str

    raise HTTPException(status_code=403, detail="URL host resolves to a non-public address")


@router.post("/url", status_code=202)
async def ingest_url(
    source: UrlSource,
    request: Request,
    kind: Literal["process", "ingest"] = Query(default="ingest"),
    runner: PipelineRunner = Depends(get_runner),
    cfg: Settings = Depends(get_settings),
) -> dict:
    allowed = {
        host.strip().lower()
        for host in cfg.source_url_allowed_hosts.split(",")
        if host.strip()
    }
    parsed_url = urlparse(str(source.url))
    host = (parsed_url.hostname or "").lower()
    if parsed_url.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Only HTTP(S) URLs are supported")
    if not allowed or host not in allowed:
        raise HTTPException(status_code=403, detail="URL host is not allow-listed")
    if not _is_public_host(host):
        raise HTTPException(status_code=403, detail="URL host resolves to a non-public address")
    resolved_ip = _resolve_public_ip(host)
    request_path = parsed_url.path or "/"
    if parsed_url.query:
        request_path = f"{request_path}?{parsed_url.query}"
    target_url = f"{parsed_url.scheme}://{resolved_ip}{request_path}"
    headers = {"Host": host}
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        response = await client.get(target_url, headers=headers)
        response.raise_for_status()
    if len(response.content) > cfg.request_max_body_bytes:
        raise HTTPException(status_code=413, detail="Remote document is too large")
    document = DocumentInput(title=source.title, owner=source.owner, content=response.text)
    return request.app.state.job_manager.submit(
        kind, getattr(request.state, "actor", "shared-token"), document, runner
    )


@router.post("/github", status_code=202)
async def ingest_github_file(
    source: GitHubSource,
    request: Request,
    kind: Literal["process", "ingest"] = Query(default="ingest"),
    runner: PipelineRunner = Depends(get_runner),
    cfg: Settings = Depends(get_settings),
) -> dict:
    if not cfg.github_repo or not cfg.github_token:
        raise HTTPException(status_code=503, detail="GitHub source access is not configured")
    headers = {
        "Authorization": f"Bearer {cfg.github_token}",
        "Accept": "application/vnd.github.raw+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    params = {"ref": source.ref} if source.ref else None
    async with httpx.AsyncClient(
        base_url="https://api.github.com", headers=headers, timeout=30
    ) as client:
        response = await client.get(
            f"/repos/{cfg.github_repo}/contents/{source.path}", params=params
        )
        response.raise_for_status()
    document = DocumentInput(
        title=source.path.rsplit("/", 1)[-1].rsplit(".", 1)[0],
        owner=source.owner,
        content=response.text,
    )
    return request.app.state.job_manager.submit(
        kind, getattr(request.state, "actor", "shared-token"), document, runner
    )
