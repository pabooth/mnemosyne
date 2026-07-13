import argparse
import asyncio
import json

from . import __version__
from .config import get_settings
from .llm.factory import get_provider
from .models import DocumentInput
from .pipeline.classify import classify_augment_format
from .pipeline.templates import get_template_set

CASES = [
    {
        "name": "guided-learning",
        "expected": "tutorial",
        "content": "In this lesson you will build your first service. Start with a new project and follow each step.",
    },
    {
        "name": "task-procedure",
        "expected": "how-to",
        "content": "To rotate the database credentials, create a new secret, update the deployment, and revoke the old key.",
    },
    {
        "name": "api-facts",
        "expected": "reference",
        "content": "POST /widgets accepts name, size, and owner. It returns 201 with the widget identifier.",
    },
    {
        "name": "architecture-rationale",
        "expected": "explanation",
        "content": "The service uses an event log because consumers need independent replay and failure isolation.",
    },
]


async def evaluate() -> dict:
    provider = get_provider(get_settings())
    templates = get_template_set()
    outcomes = []
    for case in CASES:
        document = await classify_augment_format(
            DocumentInput(content=case["content"]),
            provider,
            templates,
        )
        outcomes.append(
            {
                "name": case["name"],
                "expected": case["expected"],
                "actual": document.type,
                "passed": document.type == case["expected"],
            }
        )
    passed = sum(outcome["passed"] for outcome in outcomes)
    return {
        "provider": get_settings().llm_provider,
        "accuracy": passed / len(outcomes),
        "passed": passed,
        "total": len(outcomes),
        "outcomes": outcomes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mnemo-evaluate",
        description="Run the Mnemosyne Diátaxis evaluation set",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument("--minimum-accuracy", type=float, default=0.75)
    args = parser.parse_args()
    report = asyncio.run(evaluate())
    print(json.dumps(report, indent=2))
    if report["accuracy"] < args.minimum_accuracy:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
