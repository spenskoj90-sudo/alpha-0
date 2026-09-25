# SENTINEL — Test Coverage Quality Policy

## Status

Approved engineering policy for the current SENTINEL development phase.

## Purpose

Code coverage is a quality signal and a regression guard. It is not a target to optimize at the expense of meaningful tests. SENTINEL prioritizes behavioral, integration, security, critical-path and recovery coverage over raw percentage.

## Coverage gates

| Gate | Threshold | Meaning |
|---|---:|---|
| Non-PostgreSQL Core line gate | 85% lines | Fast routine Core regression floor for the ordinary unit/API/security suite. |
| Combined Core gate | 90% lines | Hard exact-SHA gate after ordinary and PostgreSQL integration coverage are combined. |
| Combined Core branch gate | 85% branches | Hard exact-SHA branch-coverage gate on the same combined data set. |
| Web API/server gate | 85% statements / lines / functions, 80% branches | Hard Vitest/V8 gate over first-party `web/app/api/**/*.ts` production modules. |
| Critical Web auth/session/billing gate | 90% statements / lines / functions, 85% branches | Stronger file/glob thresholds for session authority, billing boundaries and selected admin authorization code. |
| Critical paths | 90–95%+ preferred | Security, authorization, identity, session/device proof, billing/entitlement, event processing and other high-impact decision paths should exceed the global floor where practical. |

The combined gate is measured with branch coverage enabled across production `app` code. PostgreSQL integration tests append into the same coverage data set before the line and branch thresholds are evaluated.

Web percentage gates deliberately cover server/API TypeScript where V8 line/branch coverage is an appropriate executable signal. React/Next page and component correctness is not claimed from headless line percentages alone; those surfaces remain governed by behavioral tests, accessibility-contract tests, lint/build validation and exact-candidate browser/physical acceptance where applicable. Excluding UI files from the numeric Web API gate is therefore a scope boundary, not a coverage waiver.

## Policy rules

1. Do not add tests solely to increase the percentage.
2. Prefer tests that validate behavior, invariants, failure modes, security boundaries, integration contracts and recovery paths.
3. A change that drops the non-PostgreSQL Core suite below 85% line coverage is a CI failure.
4. A change that drops combined Core coverage below 90% lines **or** 85% branches is a CI failure.
5. A change that drops Web API/server coverage below 85% statements/lines/functions or 80% branches is a CI failure; critical Web auth/session/billing paths must also satisfy their stronger configured thresholds.
6. Coverage must not be increased by weakening assertions, excluding meaningful server/API production code, marking reachable code as unmeasured, or otherwise gaming the metric.
7. UI code must not be added to or removed from percentage scope merely to manipulate a number; its acceptance requires the behavioral/accessibility/build/browser evidence defined for that surface.
8. High-risk critical paths should receive stronger coverage than the global average; 90–95%+ remains the preferred range where practical.
9. When percentage and meaningful behavioral coverage conflict, preserve the stronger behavioral/security test suite and improve the uncovered behavior rather than weakening the gate.
10. Threshold changes require an explicit policy/code change and repository verification; they must never be inferred from a single CI run.

## Governance

The hard thresholds are implemented in `.github/workflows/build.yml` and locked by `scripts/verify_repository.py`. Acceptance claims still require the exact commit SHA plus the applicable CI evidence.
