---
description: An operational procedure for running, checking, or recovering a specific system, often executed under incident pressure — symptoms, diagnosis, remediation, verification, escalation. Mostly linear. Not a playbook (little branching) and not a postmortem (written before the fact, for live use).
tier: tier-1
---

# Document title

## System

The system or service this runbook operates, with links to its dashboards,
alerts, and source.

## When to use this runbook

The triggers: alert names, symptoms, or situations that should bring an
operator here.

## Prerequisites and access

Permissions, tools, and credentials the operator needs before starting.
An operator paged at 03:00 should be able to check this list in one minute.

## Diagnosis

How to confirm what is actually wrong before acting. Commands to run,
signals to read, and how to interpret them.

## Remediation

1. Numbered steps, in order, each with its expected result.
2. Call out clearly any step that is destructive, slow, or hard to reverse.

## Verification

How to confirm the system is healthy again — not just that the steps ran.

## Escalation

When to stop and escalate, and to whom. Include out-of-hours paths.

## Related

Adjacent runbooks, the playbook for the wider scenario, and relevant
postmortems.
