import argparse
import asyncio
import json

from .service import CuratorService
from .settings import Settings


async def _scan(resolve: bool) -> None:
    report = await CuratorService(Settings()).scan(resolve=resolve)
    print(report.model_dump_json(indent=2))


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
