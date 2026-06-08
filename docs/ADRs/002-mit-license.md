# ADR-002: Adopt MIT License

> **Status:** `Accepted`\
> **Date:** 2026-06-08\
> **Review date:** 2027-06-08\

***

## Identity

| Field             | Value                     |
| ----------------- | ------------------------- |
| **ID**            | ADR-002                   |
| **Title**         | Adopt MIT License         |
| **Status**        | Accepted                  |
| **Date**          | 2026-06-08                |
| **Review date**   | 2027-06-08                |
| **Supersedes**    | —                         |
| **Superseded by** | —                         |
| **Tags**          | `licensing` `open-source` |

***

## Ownership

| Field                       | Value      |
| --------------------------- | ---------- |
| **Author / Decision Owner** | Paul Booth |
| **Contributors**            | —          |
| **Consulted**               | —          |

***

## Context

Mnemosyne is being released as an open source project. A licence must be chosen that governs how the software can be used, modified, and redistributed. The primary audience includes enterprise organisations, individual developers, and self-hosters — many of whom will have legal or procurement requirements that influence which licences they can adopt.

***

## Considered Options

### Option 1: MIT License *(chosen)*

A permissive licence allowing unrestricted use, modification, and redistribution, including in commercial products, with no obligation to open source derivative works.

**Pros:**

- Maximum adoption potential — lowest friction for enterprise and individual users alike
- Widely understood and accepted by legal and procurement teams
- No copyleft obligations that might deter commercial use
- Simple — one short file, no ambiguity

**Cons:**

- No obligation on users to contribute improvements back
- No explicit patent grant (unlike Apache 2.0)

### Option 2: Apache 2.0

Similar permissiveness to MIT but includes an explicit patent grant.

**Pros:**

- Explicit patent protection for contributors and users
- Preferred by some larger enterprises for this reason

**Cons:**

- More complex licence text
- Marginal practical difference for a project of this scale

### Option 3: GPL v3

Copyleft licence requiring derivative works to also be open sourced.

**Pros:**

- Ensures community improvements remain open

**Cons:**

- Likely to deter enterprise adoption
- Incompatible with many commercial use cases
- Too restrictive for the intended audience

### Option 4: AGPL v3

Extends GPL to close the SaaS loophole — organisations running modified versions as a service must also open source their changes.

**Pros:**

- Strongest protection against proprietary forks
- Relevant if Mnemosyne were offered as a hosted service

**Cons:**

- Most restrictive option; highest barrier to adoption
- Disproportionate for the current project goals

***

## Decision

Mnemosyne will be licensed under the MIT License.

***

## Justification

The primary goal of open sourcing Mnemosyne is adoption — particularly in enterprise environments where knowledge management tooling is most needed. MIT provides the lowest friction path to adoption across individual developers, SMEs, and large organisations. The absence of an explicit patent grant (vs Apache 2.0) is an acceptable trade-off given the project's current scale and the simplicity benefit MIT provides.

***

## Enforcement

- A `LICENSE` file containing the MIT License text is maintained in the repository root
- All release artefacts include the LICENSE file
- Contributors are implicitly licensing their contributions under MIT by submitting pull requests

***

## Consequences

Positive:

- No licence-related barriers to adoption for enterprise or commercial users
- Simple, well-understood terms for contributors

Negative / trade-offs:

- No obligation on users to contribute improvements back to the project
- If a commercial entity forks and ships Mnemosyne as a product, there is no reciprocity requirement

***

## Related

- [ADR-001: Monorepo with separate build artefacts](001-monorepo-structure.md)

***

*This ADR follows the Mnemosyne Project ADR standard.*\
*Template version: 1.0 — June 2026*
