# SENTINEL Engineering Contract

## Purpose

This file defines the machine-operable engineering loop for SENTINEL/ALPHA-0. GitHub is authoritative for implementation.

## Source hierarchy

1. Accepted Architecture v3
2. Accepted Implementation Contract v1
3. Accepted Test Matrix v1
4. Repository code and tests
5. CI/security evidence
6. Issues/PR discussion

Accepted architecture is not silently changed by an implementation agent.

## Standard loop

Requirement -> Issue -> Branch -> Implementation -> Tests -> Lint -> Build -> Security -> Device validation -> Review -> Human approval -> Merge -> Release -> Runtime observation -> Regression issue.

## Branching

- Feature work: `feature/<issue-or-scope>`
- Fixes: `fix/<issue-or-scope>`
- Automation: `automation/<scope>`
- Security: `security/<scope>`
- Never commit directly to `main` for engineering changes.

## Definition of implemented

A change is not implemented until:

1. the relevant tests exist or the reason for their absence is documented;
2. unit tests pass;
3. lint passes where applicable;
4. the relevant build passes;
5. security checks pass where applicable;
6. device/instrumentation tests pass when the change affects runtime behavior;
7. the PR records evidence and regression coverage.

Failure handling follows:

`FAIL -> root cause -> FIX -> regression -> PASS -> ACCEPTED`

## Agent permissions

Routine automation may inspect repositories, create branches, edit files, run tests through CI, analyze failures, and prepare PRs.

The agent must not autonomously:

- merge high-impact changes;
- publish production releases;
- alter production credentials;
- expose signing material or secrets;
- perform destructive production database operations;
- disable security controls to make CI pass;
- weaken Default Deny or Least Privilege controls.

Human approval is required for those actions.

## Security invariants

- Default Deny
- Least Privilege
- Server-side authorization
- RBAC + Scope
- Entitlement-aware access
- Policy-aware decisions
- Context-aware decisions
- Centralized authorization truth
- Auditability
- Traceability
- Versioned rules
- Measured performance claims only

## Review requirements

Every PR must state:

- what changed;
- why it changed;
- affected architecture/contract invariants;
- tests executed;
- security impact;
- rollback/regression strategy;
- whether human approval is required.

## Automation rule

Automation should maximize reversible, observable, testable work while preserving explicit approval boundaries for irreversible or high-impact actions.
