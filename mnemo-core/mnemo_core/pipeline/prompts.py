from datetime import date

from ..models import DocumentInput

STANDARD_TEMPLATE = """
## Introduction

Why this standard exists and what problem it solves.

## Scope

Who and what this standard applies to. Explicitly state any exclusions.

## Policies

The rules of this standard. Use RFC 2119 language throughout:
- MUST / MUST NOT — mandatory, non-negotiable
- SHOULD / SHOULD NOT — strongly recommended, exceptions require justification
- MAY — optional, permitted but not required

## Compliance

How compliance is measured or assured. Who is responsible for compliance.
What happens when compliance is not met.

## Technology

Technology that supports or is required for compliance with this standard.
May also describe technology this standard applies to.

## Exceptions

The process for requesting an exception to this standard.
Who reviews and approves exceptions. How exceptions are documented.

## Related processes and how-tos

Direct links to actionable documents that implement this standard.

## Related documents and internal references

Further reading. Related standards, principles, policies, or external references.

## Dependencies

What this standard depends on — other standards, principles, external regulations,
or organisational decisions that underpin it.

## Review

Review cycle, next review date, and owner responsible for review.

## Change log

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 0.1 | | | Initial draft |
"""

TEMPLATES: dict[tuple[str, str], str] = {
    ("reference", "standard"): STANDARD_TEMPLATE,
}

SYSTEM_PROMPT = """You are a technical documentation specialist working with the Diataxis framework.
Given raw content, produce a structured JSON object with these exact fields:
- title: string — concise, imperative or noun-phrase title
- type: one of "tutorial", "how-to", "reference", "explanation"
- sub_label: one of "standard", "principle", "policy", "glossary", "process", "procedure",
  "runbook", "onboarding", "learning-path", "architecture", "adr", "requirements", "strategy" or "" if none applies
- status: one of "draft", "proposed", "accepted", "modified", "superseded" — default to "draft"
- tags: array of 3-6 lowercase kebab-case strings
- summary: string — one sentence, under 160 chars
- owner: string — keep as-is if provided, else "unset"
- last_reviewed: string — today's date in YYYY-MM-DD format
- flags: array of strings — concerns like "needs-review", "outdated", "incomplete", "missing-examples"; empty if none
- body: string — the full Markdown article body (no frontmatter), well-structured with headers

Diataxis classification rules — apply these strictly:

tutorial: learning-oriented. Guides a beginner through a complete exercise with a defined outcome.
  Examples: onboarding guides, walkthroughs, structured learning paths.

how-to: task-oriented. Practical steps to achieve a specific goal. Assumes competence.
  Examples: procedures, runbooks, step-by-step processes for an end user.

reference: information-oriented. Factual, accurate, consulted not read end-to-end.
  Examples: standards, principles, policies, API docs, configuration options, glossaries.
  Sub-labels: standard, principle, policy, glossary.

explanation: understanding-oriented. Discusses concepts, rationale, context, decisions.
  Examples: requirements documents, architecture documents, design decisions, background context,
  system overviews, governance frameworks, anything that answers "why" or "what is this".
  Sub-labels: architecture, adr, requirements, strategy.
  Key signal: if the document describes a SYSTEM or PRODUCT rather than instructing a USER,
  it is explanation. Requirements and architecture documents are ALWAYS explanation.

how-to sub-labels: process, procedure, runbook.
tutorial sub-labels: onboarding, learning-path.

Common misclassifications to avoid:
- Requirements and architecture documents are EXPLANATION, not how-to or reference
- Standards and principles are REFERENCE, not explanation
- A document with numbered steps is not automatically a how-to — check whether it is
  instructing an end user to perform a task, or describing how a system works
- Requirements documents are ALWAYS explanation, never reference or how-to
- Architecture documents are ALWAYS explanation, never reference

If a template is provided in the user message, use it as the structure for the body.
Populate each section with content derived from the raw input.
Do not remove sections — if there is no content for a section, leave a brief placeholder.

Return ONLY valid JSON, no other text."""


def build_user_message(doc: DocumentInput, *, today: date | None = None) -> str:
    today = today or date.today()
    template_key = (doc.type, doc.sub_label) if doc.type and doc.sub_label else None
    template = TEMPLATES.get(template_key, "")
    template_block = f"\nUse this template for the body:\n{template}" if template else ""

    return f"""Today's date: {today.isoformat()}

Title hint: {doc.title or '(none — please infer)'}
Owner: {doc.owner or 'unset'}
Diataxis type hint: {doc.type or '(none — please infer)'}
Sub-label hint: {doc.sub_label or '(none — please infer)'}
{template_block}
Raw content:
{doc.content}"""
