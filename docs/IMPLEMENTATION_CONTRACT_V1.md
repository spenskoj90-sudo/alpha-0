# SENTINEL Implementation Contract v1

Status: RC1 baseline
Version: 1.0.0-RC1

## Architectural decisions

| ID | Decision | Contract |
|---|---|---|
| D-001 | Modular Monolith | SENTINEL CORE remains a modular monolith; split into services only when scale or trust boundaries require it. |
| D-002 | Core SSOT | SENTINEL CORE is the authoritative source for identity, authorization, entitlement and server game projections. |
| D-003 | Centralized authorization | Privileged authorization is evaluated server-side through one authorization boundary. |
| D-004 | Default deny | Missing policy, missing scope, invalid proof, stale request or ambiguous state is denied. |
| D-005 | Least privilege | Sessions carry only explicitly granted scopes. |
| D-006 | Role is not authorization | Roles are policy inputs; a role alone never grants access. |
| D-007 | First-class scopes | Scopes are explicit, enumerable and versionable; clients cannot self-escalate them. |
| D-008 | Payment → Order → Subscription → Entitlement | Access is derived from entitlement state, not directly from a payment provider response. |
| D-009 | Billing separate | Billing/provider state cannot directly authorize an operation. |
| D-010 | Knowledge separate from interaction | Knowledge and recommendation logic cannot mutate authoritative game state directly. |
| D-011 | Local-first telemetry | Android queues non-authoritative telemetry/events locally; server remains authoritative. |
| D-012 | Legal/data governance | Consent, retention, privacy classification and audit requirements are architecture concerns. |
| D-013 | Character/equipment separation | Character identity, equipment state, actual items and transmog are separate domain concepts. |
| D-014 | Knowledge/context/confidence | Recommendations carry context, confidence and provenance and are never an authority. |
| D-015 | Performance ≠ benchmark | Architecture performance gates validate safety/latency budgets; benchmark claims require dedicated benchmark infrastructure. |
| D-016 | GitHub SSOT | Source, contracts, tests and release evidence are versioned in GitHub. |
| D-017 | Baseline artifacts | Architecture v4, this Implementation Contract v1 and Test Matrix v1 form the RC1 baseline. |
| D-018 | Portable workspace | The project must build from a clean checkout without ChatGPT-workspace-local state. |
| D-019 | Ownership unchanged | Repository ownership and package/application identity remain unchanged. |
| D-020 | Minimal RC | 1.0.0-RC1 is the next milestone; no speculative feature expansion is release-blocking. |

## Non-negotiable security invariants

1. Android private keys never leave Android Keystore.
2. Device proof uses P-256 ECDSA/SHA-256 and canonical request bytes.
3. Session tokens are opaque and stored server-side only as hashes.
4. Challenges/nonces are one-time and expire.
5. Replay outside the timestamp window is denied.
6. Authorization denies on no match, missing scope, invalid device or ambiguous policy state.
7. Audit data is append-oriented and security relevant decisions are recorded.
8. AI/recommendation output cannot grant access, change billing, revoke devices or execute game actions.
9. Secrets are never committed to GitHub.
10. Release signing is isolated from ordinary debug/CI validation.

## Acceptance rule

`FAIL → root cause → FIX → regression → PASS → ACCEPTED`.

A gate is accepted only when its automated evidence exists or when an explicitly recorded external evidence item is supplied by the release operator.
