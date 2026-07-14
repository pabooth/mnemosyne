---
description: A decision-branching procedure for a scenario where the right actions depend on conditions — assess, then follow the branch that matches. Less linear than a runbook and usually broader than one system (security incident, major outage, customer escalation). Structure guiding judgment, not steps to follow blindly.
tier: tier-1
---

# Document title

## Scenario

The situation this playbook handles, and the outcome it drives toward.

## Roles

Who is involved when this playbook runs and what each role owns
(e.g. incident lead, communications, subject-matter responder).

## Entry conditions

How to recognise that this playbook applies, and the first assessment
to make on arrival.

## Decision points

The branching logic. For each decision point: the question to answer,
the signals that answer it, and the branch each answer leads to.

### Branch A — Condition

Actions for this branch, in order, and the point at which it rejoins the
main flow or exits.

### Branch B — Condition

As above. Add branches as the scenario requires; every branch must end
somewhere explicit.

## Communications

Who must be informed, when, and through which channels while the playbook
is running.

## Exit criteria

How to know the scenario is resolved and the playbook is complete,
including any follow-up obligations (e.g. a postmortem).

## Related

The runbooks this playbook delegates to, and adjacent playbooks.
