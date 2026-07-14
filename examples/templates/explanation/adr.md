---
description: An architecture decision record — one decision, the context that forced it, the options weighed, the choice made, and its consequences. Point-in-time — once accepted it changes only by amendment (partial updates) or supersession (full replacement), never silent edits. Not an RFC — an ADR records a decision made, an RFC argues for one not yet made.
tier: tier-2
---

# ADR-NNN: Short imperative title of the decision

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-NNN, numbered sequentially |
| **Status** | Proposed, Accepted, or Superseded |
| **Date** | Date of the decision |
| **Review date** | When to revisit — typically a year out |
| **Supersedes** | The ADR this one replaces entirely, if any |
| **Superseded by** | Set on this ADR when a successor replaces it |
| **Amends** | The accepted ADR this one partially changes, if any |
| **Amended by** | Set on this ADR when an amendment lands |

Amendment and supersession are reciprocal: partial changes to an accepted
ADR arrive as a new ADR using Amends/Amended by; replacing the whole
decision uses Supersedes/Superseded by. An accepted ADR is never edited
in place.

## Ownership

Author / decision owner, contributors, and who was consulted.

## Context

The situation that forces a decision: the problem, the constraints, and
why deciding now matters. Keep it factual — the argument for the chosen
option belongs in Justification.

## Considered options

Each option with its genuine pros and cons — including the option chosen,
marked *(chosen)* in its heading. An ADR with only one option recorded is
a press release, not a decision record.

## Decision

The choice made, stated plainly.

## Justification

Why the chosen option wins over the alternatives, and why the trade-offs
it carries are acceptable.

## Enforcement

How the decision is upheld in practice — conventions, checks, branch
protection, tests, documentation — and what should happen when a future
change conflicts with it (typically: reference and supersede this ADR).

## Consequences

What follows from the decision — the positives, the costs accepted, and
any follow-up work it creates.

## Related

The decisions this one builds on, amends, or supersedes, as links.
