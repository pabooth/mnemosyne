"""Classifier prompt assembly (ADR-003, ADR-018).

The four Diataxis types and their classification rules are fixed here.
The sub-label taxonomy is not: it is assembled from the knowledge base's
own template set, so each KB defines its own document types and the
descriptions its curators wrote are, verbatim, what the classifier knows
about them.
"""

from datetime import date

from ..models import DocumentInput
from .templates import Template, TemplateSet

_PROMPT_INTRO = """You are a technical documentation specialist working with the Diataxis framework.
Given raw content, produce a structured JSON object with these exact fields:
- title: string — concise, imperative or noun-phrase title
- type: one of "tutorial", "how-to", "reference", "explanation"
{sub_label_field}
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

explanation: understanding-oriented. Discusses concepts, rationale, context, decisions.
  Examples: requirements documents, architecture documents, design decisions, background context,
  system overviews, governance frameworks, anything that answers "why" or "what is this".
  Key signal: if the document describes a SYSTEM or PRODUCT rather than instructing a USER,
  it is explanation. Requirements and architecture documents are ALWAYS explanation.

Common misclassifications to avoid:
- Requirements and architecture documents are EXPLANATION, not how-to or reference
- Standards and principles are REFERENCE, not explanation
- A document with numbered steps is not automatically a how-to — check whether it is
  instructing an end user to perform a task, or describing how a system works
{sub_label_rules}
If a template is provided in the user message, use it as the structure for the body.
Populate each section with content derived from the raw input.
Do not remove sections — if there is no content for a section, leave a brief placeholder.

Return ONLY valid JSON, no other text."""

_SUB_LABEL_FIELD_EMPTY = (
    '- sub_label: always "" — this knowledge base defines no document sub-types'
)

_SUB_LABEL_FIELD = (
    '- sub_label: one of {names} or "" if none applies'
)


def _sub_label_rules(templates: TemplateSet) -> str:
    if len(templates) == 0:
        return ""
    lines = [
        "",
        "This knowledge base defines the following document sub-types. Assign",
        'sub_label by matching the descriptions below; use "" when none applies.',
        "",
    ]
    for doc_type in ("tutorial", "how-to", "reference", "explanation"):
        for template in templates.for_type(doc_type):
            lines.append(f"{doc_type} / {template.sub_label}: {template.description}")
    lines.append("")
    return "\n".join(lines)


def build_system_prompt(templates: TemplateSet) -> str:
    if len(templates) == 0:
        sub_label_field = _SUB_LABEL_FIELD_EMPTY
    else:
        names = ", ".join(f'"{name}"' for name in templates.sub_labels)
        sub_label_field = _SUB_LABEL_FIELD.format(names=names)
    return _PROMPT_INTRO.format(
        sub_label_field=sub_label_field,
        sub_label_rules=_sub_label_rules(templates),
    )


def build_user_message(
    doc: DocumentInput,
    template: Template | None = None,
    *,
    today: date | None = None,
) -> str:
    today = today or date.today()
    template_block = (
        f"\nUse this template for the body:\n{template.body}\n" if template else ""
    )

    return f"""Today's date: {today.isoformat()}

Title hint: {doc.title or '(none — please infer)'}
Owner: {doc.owner or 'unset'}
Diataxis type hint: {doc.type or '(none — please infer)'}
Sub-label hint: {doc.sub_label or '(none — please infer)'}
{template_block}
Raw content:
{doc.content}"""
