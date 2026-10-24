# SENTINEL Document Authority Map

**Status:** ACTIVE
**Purpose:** identify the smallest current instruction set. Live code/runtime/exact-SHA evidence always outranks prose.

## Active authority and orientation

- `ENGINEERING_BLOCKS.md` + `engineering-blocks.v1.json` — ACTIVE Owner-approved 2026-10-23 A–I platform/shared-system work registry; new block names replace historical completed productization labels but do not claim their new scope completed. Existing release/security gates are unchanged.

- `AI_ORCHESTRATION_OPERATING_SYSTEM.md` — canonical GPT-controlled governance.
- root/scoped `AGENTS.md` — compact context routing.
- `CHATGPT_PROJECT_INSTRUCTIONS.md` and `CHATGPT_WORKING_ENVIRONMENT.md` — compact ChatGPT/Work context.
- `WORKFLOW_CONTRACT.md` and `AI_ORCHESTRATION_ROUTING.md` — execution/routing contracts.
- `SENTINEL_CURRENT_STATE.md` — semantic orientation only; no mutable HEAD mirror.
- `TASKS.md` — work queue, not implementation evidence.
- `PLAYER_INTELLIGENCE_ROADMAP_V1.md` — ACTIVE Owner requirements/future backlog (#455): builds, adaptive analysis, modular full-game domains, subscription groups/Owner access, bounded execution, UX and continuity; not implemented-feature evidence.
- release/evidence contracts: `SENTINEL_EVIDENCE_PROTOCOL.md`, `RELEASE_GATES.md`, `RELEASE_EVIDENCE_PREFLIGHT_V1.md`, `RELEASE_LINEAGE_V1.md`, `SUPPLY_CHAIN_EVIDENCE_V1.md`, `ARTIFACT_ATTESTATION_V1.md`, `FINAL_RELEASE_ACCEPTANCE_V1.md`, `USER_VISIBLE_ACCEPTANCE_CONTRACT.md`.
- design authority: `DESIGN_SYSTEM_V3.md` + `../design/sentinel-design-system.v3.json`; the design laboratory is input, not production truth.
- `CONTROL_BRIDGE_ARCHITECTURE.md` + `../control-bridge/`.
- `STAGING_SYNTHETIC_GATE.md` + `.github/workflows/staging-synthetic.yml`.
- `EMAIL_ACTION_CODES_V1.md` — short email-code security, migration and mail/client presentation contract.
- `OBSERVABILITY.md` + `../observability/telemetry-contract.v1.json`.
- `SENTINEL_DECISION_LOG.md` and `CHANGELOG.md` are historical ledgers with current metadata.

- `DESIGN_PROGRAM_H_V2.md` + `../design/h-design-program.v2.json` — **ACTIVE Owner-approved H1–H11 deep product-design program (2026-10-24)**: brand/app icons, one icon language, components/interactions, Android/PC/Web and real multi-page site. Design/brand selection remains pending; v3 production contracts unchanged.

## Draft visual studies (non-binding)

- `DESIGN_STUDIES_H_2026-10-24.md` + `../design/h-design-studies.v1.json` — five bilingual B/C/D/E Figma directions awaiting Owner selection; ACTIVE production design remains `DESIGN_SYSTEM_V3.md` and its v3 machine contract. A visual study is not a native UI or Owner-accepted release.

## Active architecture/implementation references

Active within their stated scope: `README.md`, `ARCHITECTURE.md`, `ARCHITECTURE_V4.md`, `SENTINEL_MASTER_ARCHITECTURE_v0.3.md`, `SENTINEL_PRODUCT_VISION_CONTEXT.md`, `API.md`, `SECURITY.md`, `SECURITY_WHITEPAPER.md`, `DEPLOYMENT.md`, `DEVELOPER_GUIDE.md`, `CONTRIBUTING.md`, `FTL_POLICY.md`, `QUALITY_COVERAGE_POLICY.md`, `BRANCH_INVENTORY.md`, `PROVIDER_STATUS_MATRIX.md`, `PLATFORM_MODERNIZATION_2026Q3.md`, `SENTINEL_PERFORMANCE_BASELINE.md`, and versioned component/contract documents.

## Historical evidence retained intentionally

Point-in-time audit/evidence documents explicitly marked `HISTORICAL` remain for traceability. Their conclusions must be revalidated before current use.

Older design-system lineage (v1/v2.1) remains historical; v3 is active.

## Retired documents removed from the working tree

To prevent stale instructions from being loaded as current context, superseded operating/state/reference files are removed rather than kept as tombstones. Their history remains available through Git.

Removed on 2026-09-29:
- `GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md`
- `AUTONOMOUS_ENGINEERING_CONTRACT.md`
- `AUTONOMOUS_PERMISSIONS.md`
- `OPERATING_PLAYBOOK.md`
- `AI_ROLES.md`
- `API_REFERENCE.md`
- `PLATFORM_RC.md`
- `PROJECT_STATE.md`
- `SENTINEL_AUDIT_2026-09-23.md` — stale point-in-time file that incorrectly declared itself current and still asserted the retired GPT-only model.

## Classification rule

New persistent docs must declare `ACTIVE`, `HISTORICAL`, or an explicit non-binding draft status near the title.

Do not create new tombstone files for retired guidance. Remove obsolete working-tree instructions after their replacement is active and rely on Git history for provenance.
