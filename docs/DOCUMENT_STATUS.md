# SENTINEL Document Authority Map

**Status:** ACTIVE
**Purpose:** keep the working tree free of obsolete governance while preserving historical lineage in Git. Live code, provider state and exact-SHA evidence outrank prose.

## Active authority and orientation

- `AI_ORCHESTRATION_OPERATING_SYSTEM.md` — canonical GPT-orchestrated engineering governance.
- root/scoped `AGENTS.md` — compact context routing.
- `WORKFLOW_CONTRACT.md` and `AI_ORCHESTRATION_ROUTING.md` — active execution/routing rules.
- `CHATGPT_PROJECT_INSTRUCTIONS.md`, `CHATGPT_PROJECT_MEMORY.md`, `CHATGPT_WORKING_ENVIRONMENT.md` — compact ChatGPT Project/Work context.
- `SENTINEL_CURRENT_STATE.md` — semantic orientation only; live Git/runtime evidence remains authoritative.
- `TASKS.md` — active work queue, not implementation evidence.
- `SENTINEL_EVIDENCE_PROTOCOL.md`, `RELEASE_GATES.md`, `RELEASE_EVIDENCE_PREFLIGHT_V1.md`, `RELEASE_LINEAGE_V1.md`, `SUPPLY_CHAIN_EVIDENCE_V1.md`, `ARTIFACT_ATTESTATION_V1.md`, `FINAL_RELEASE_ACCEPTANCE_V1.md`, `USER_VISIBLE_ACCEPTANCE_CONTRACT.md` — active evidence/release contracts.
- `DESIGN_SYSTEM_V3.md` plus `../design/sentinel-design-system.v3.json` — active production design contract.
- `CONTROL_BRIDGE_ARCHITECTURE.md` plus `../control-bridge/` — compact project/runtime evidence foundation.
- `OBSERVABILITY.md` plus `../observability/telemetry-contract.v1.json` — active observability/privacy contract.
- `SENTINEL_DECISION_LOG.md` and `CHANGELOG.md` — dated decision/history ledgers.

## Active architecture and operations references

Active references include `README.md`, `ARCHITECTURE.md`, `ARCHITECTURE_V4.md`, `SENTINEL_MASTER_ARCHITECTURE_v0.3.md`, `SENTINEL_PRODUCT_VISION_CONTEXT.md`, `API.md`, `SECURITY.md`, `SECURITY_WHITEPAPER.md`, `DEPLOYMENT.md`, `DEVELOPER_GUIDE.md`, `CONTRIBUTING.md`, `FTL_POLICY.md`, `QUALITY_COVERAGE_POLICY.md`, `BRANCH_INVENTORY.md`, `PROVIDER_STATUS_MATRIX.md`, `PLATFORM_MODERNIZATION_2026Q3.md` and `SENTINEL_PERFORMANCE_BASELINE.md`.

Versioned component/contract documents remain active within their stated scope unless their own header says historical or draft.

## Retained historical evidence

Historical audits/handoffs that remain in the tree must carry an explicit historical banner. They are evidence records only and never override active contracts or live state.

## Removed obsolete paths

Obsolete duplicate governance/state/API snapshot files are intentionally removed from the working tree instead of being kept as superseded stubs. Their history remains available through Git:

- `GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md`;
- `AUTONOMOUS_ENGINEERING_CONTRACT.md`;
- `AUTONOMOUS_PERMISSIONS.md`;
- `OPERATING_PLAYBOOK.md`;
- `AI_ROLES.md`;
- `API_REFERENCE.md`;
- `PLATFORM_RC.md`;
- `PROJECT_STATE.md`;
- point-in-time `SENTINEL_AUDIT_2026-09-23.md`;
- `automation/ai-orchestration.v1.json`, replaced by v2.

Do not recreate these compatibility stubs. Use Git history when historical text is genuinely required.

## Classification rule

New persistent documents must be ACTIVE, HISTORICAL, or an explicit non-binding draft. When a document becomes redundant, consolidate useful content into the active authority and remove the obsolete working-tree copy after references/tests are reconciled.
