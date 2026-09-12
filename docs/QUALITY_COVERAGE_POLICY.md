# SENTINEL — Test Coverage Quality Policy

## Status

Approved engineering policy for the current SENTINEL development phase.

## Purpose

Code coverage is a quality signal and a regression guard. It is not a target to optimize at the expense of meaningful tests. SENTINEL prioritizes behavioral, integration, security, and critical-path coverage over raw line-count percentage.

## Coverage levels

| Level | Threshold | Meaning |
|---|---:|---|
| Absolute release floor | 80% | Existing release-candidate CI minimum; falling below this is a release-quality failure. |
| Engineering floor | 85% | New working baseline to protect against routine coverage regression. |
| Development target | 90%+ | Desired global coverage as the project approaches release acceptance. |
| Critical paths | 90–95%+ | Preferred coverage for security, authorization, identity, event processing, UGS, intelligence, recommendation, billing/entitlement, and other high-impact decision paths. |

The current observed baseline is 86.23%, so the 85% engineering floor is immediately achievable without artificially inflating coverage.

## Policy rules

1. Do not add tests solely to increase the percentage.
2. Prefer tests that validate behavior, invariants, failure modes, security boundaries, integration contracts, and recovery paths.
3. A future change that lowers global coverage below 85% should be treated as a quality regression and investigated before merge.
4. The 80% floor remains the hard release/CI minimum until an explicit future policy change raises it.
5. 90%+ is a development objective, not an unconditional release blocker at the current phase.
6. High-risk critical paths should receive stronger coverage than the global average; 90–95%+ is the preferred range where practical.
7. Coverage percentage must never be increased by weakening assertions, excluding meaningful code, or otherwise gaming the metric.
8. When coverage and meaningful behavioral coverage conflict, preserve the stronger behavioral/security test suite and document the trade-off.

## Governance

This policy is part of the SENTINEL engineering operating model and should be considered together with the repository's autonomous engineering and release-gate documentation. Any future change to these thresholds should be documented explicitly rather than inferred from an individual CI run.
