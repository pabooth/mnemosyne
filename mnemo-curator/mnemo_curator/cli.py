import argparse
import asyncio
import json
import sys

import httpx
from pydantic import ValidationError

from .service import CuratorService
from .settings import Settings


async def _scan(resolve: bool) -> None:
    try:
        report = await CuratorService(Settings()).scan(resolve=resolve)
    except (RuntimeError, ValidationError, httpx.HTTPError) as exc:
        print(f"mnemo-curator scan failed: {_scan_error_message(exc)}", file=sys.stderr)
        raise SystemExit(1) from None
    print(report.model_dump_json(indent=2))


def _scan_error_message(exc: RuntimeError | ValidationError | httpx.HTTPError) -> str:
    if isinstance(exc, ValidationError):
        return f"configuration error: {exc}"
    if isinstance(exc, RuntimeError):
        return f"configuration error: {exc}"
    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        url = response.request.url
        if response.status_code in {401, 403}:
            return f"authentication error: HTTP {response.status_code} from {url}"
        return f"HTTP error: HTTP {response.status_code} from {url}"
    if isinstance(exc, httpx.RequestError):
        return f"network error: {exc}"
    return str(exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect and resolve Mnemosyne knowledge-base findings")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Scan repository content and record findings as issues")
    scan.add_argument("--resolve", action="store_true", help="Attempt inline resolution after issue creation")

    args = parser.parse_args()
    if args.command == "scan":
        asyncio.run(_scan(resolve=args.resolve))
    else:
        print(json.dumps({"error": f"Unknown command: {args.command}"}))
