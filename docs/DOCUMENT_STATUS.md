# SENTINEL Document Authority Map

**Status:** ACTIVE  
**Purpose:** distinguish normative/current guidance from point-in-time history. A document never replaces live code, Git state or exact-SHA CI evidence.

## Active authority and orientation

- `GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md` — canonical governance; only the Human Owner may amend it.
- `WORKFLOW_CONTRACT.md`, `AUTONOMOUS_ENGINEERING_CONTRACT.md`, `AUTONOMOUS_PERMISSIONS.md`, `OPERATING_PLAYBOOK.md`, `AI_ROLES.md` — active subordinate operating contracts.
- `SENTINEL_CURRENT_STATE.md` — semantic orientation only; it deliberately contains no mutable HEAD mirror.
- `TASKS.md` — active work queue, never implementation evidence.
- `SENTINEL_EVIDENCE_PROTOCOL.md` and `RELEASE_GATES.md` — active evidence and release-acceptance contracts.
- `SENTINEL_DECISION_LOG.md` — active decision ledger; each entry retains its own current/superseded status.
- `CHANGELOG.md` — active historical ledger; entries are scoped to their date/version.

## Active architecture, implementation and operations references

The following are active within their stated scope but are not proof that a current build passed:

- `README.md`, `ARCHITECTURE.md`, `ARCHITECTURE_V4.md`, `SENTINEL_MASTER_ARCHITECTURE_v0.3.md` and `SENTINEL_PRODUCT_VISION_CONTEXT.md`;
- `API.md`, `SECURITY.md`, `SECURITY_WHITEPAPER.md`, `DEPLOYMENT.md`, `DEVELOPER_GUIDE.md`, `CONTRIBUTING.md`, `OBSERVABILITY.md`, `FTL_POLICY.md`, `QUALITY_COVERAGE_POLICY.md` and `SENTINEL_PERFORMANCE_BASELINE.md`;
- versioned component/contract documents (`*_V1.md`, `*_V2.md`, `UNIFIED_GAME_STATE_V1.md`, `GAME_ADAPTER_CONTRACT_V1.md`, and the Companion/recommendation/intelligence documents);
- `PASS_1_UGS_COMPLETION_V1.md` through `PASS_6_ANDROID_CORE_LOOP.md`, which are implementation-boundary records for their respective merged passes;
- `SENTINEL_GAME_CAPABILITY_MATRIX_v1.md` and `SENTINEL_REFERENCE_FAILURE_AUDIT_v1.md` remain active non-binding drafts where their own header says `DRAFT FOR OWNER REVIEW`.

When an active architecture document contains a future target, its target language is normative only after the applicable decision/acceptance process; it is not a claim of implementation.

## Historical

- root `HANDOVER_DOCUMENT.md`;
- `AUDIT_CLOSURE_2026-08-13.md`;
- `SENTINEL_AUDIT_2026-08-25.md`;
- `SENTINEL_FINAL_AUDIT_2026-08-26.md`;
- `SENTINEL_SECURITY_BOUNDARY_AUDIT_ISSUE9.md`.

Historical documents are retained for traceability. Their actors, SHA snapshots, failures and conclusions must be revalidated before use.

## Superseded

- `API_REFERENCE.md` — replaced by `API.md` and runtime OpenAPI.
- `PLATFORM_RC.md` — replaced by repository-first current-state/evidence rules.
- `PROJECT_STATE.md` — replaced by `SENTINEL_CURRENT_STATE.md` plus live Git/Actions evidence.

## Classification rule

New documents must declare `ACTIVE`, `HISTORICAL`, `SUPERSEDED`, or an explicit non-binding draft status near the title. A superseded document must name its replacement. Never edit historical conclusions to make them look current; add a banner or a new current decision instead.
