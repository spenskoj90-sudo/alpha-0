# SENTINEL — Autonomous Permissions & Tool Matrix

**Tracking issue:** #167  
**Status:** PROPOSED — pending Human Owner approval.

This document distinguishes repository permissions already visible to the connected GitHub integration from permissions/tools that still require verification or Owner action. Possession of a permission never overrides the workflow contract.

## 1. Required engineering capability

| Capability | Requirement | Current assessment |
|---|---|---|
| GitHub repository read | Files, history, issues, PRs, commits, CI metadata | **Available** |
| GitHub repository write | Branches, commits, PR updates, issue comments | **Available through connected integration where permitted** |
| GitHub Actions read | Runs, jobs, checks, logs/artifacts exposed by connector | **Available** |
| GitHub workflow write | Workflow changes where issue scope allows | **Permission visible; protected by scope/Owner gates** |
| GitHub contents write | Normal code/docs commits | **Permission visible** |
| Pull-request write | Create/update PRs | **Permission visible** |
| Issue write | Create/update issues/comments | **Permission visible** |
| Status/check read | Exact-SHA verification | **Available** |
| Local/Codex execution | Run tests, builds, linters, scripts in an isolated workspace | **Required; verify in the active Codex execution environment** |
| Workspace write | Edit checkout and create build/test artifacts | **Required for autonomous implementation** |
| Network access | Only for task-required external services/package retrieval | **Conditional; least privilege** |

## 2. Current GitHub integration permissions

The connected GitHub integration has been observed with repository permissions including:

- `contents: write`
- `pull_requests: write`
- `issues: write`
- `actions: write`
- `workflows: write`
- `checks: read`
- `statuses: read`
- `metadata: read`
- `emails: read`

The actual action available to GPT is determined by the connector/tool surface and repository policy at execution time. Never infer access to secret values from these permissions.

## 3. Repository-side controls already relevant

- `main` has required status checks and up-to-date-before-merge protection according to the current-state record.
- Routine Deploy is intentionally not a required merge check.
- CURRENT_STATE auto-sync is implemented through dedicated CI paths.
- PR #166 proposes using repository secret `SYNC_PAT` for automated CURRENT_STATE PR creation so required PR checks can execute without Owner approval; the secret value itself must never be inspected or printed by GPT.

## 4. Owner-only permissions/actions

These are intentionally excluded from normal autonomous execution:

- production secret/credential values;
- signing keys, certificates and release keystores;
- branch-protection modification;
- irreversible production/database deletion or destructive migrations;
- production/live deployment;
- release publication/tagging;
- final product-direction decisions;
- any action requiring explicit legal/compliance/operator approval.

## 5. External tools and services

These are **conditional**, not blanket requirements. GPT should connect/use them only when an active issue actually requires them and the repository proves the dependency:

| Tool/service | Purpose | Status/rule |
|---|---|---|
| GitHub | Source control, Issues, PRs, Actions, evidence | Mandatory |
| Codex/isolated execution environment | Code edits, tests, builds, scripts | Mandatory for full autonomy |
| Web/documentation research | Current technical documentation and external specifications | Use when needed |
| Android SDK/emulator | Android build/test verification | Required for Android tasks |
| Firebase Test Lab | Physical/cloud device validation | Conditional; #59 is an external IAM blocker and emulator CI remains preferred for routine checks |
| PostgreSQL/Supabase runtime | Persistence/runtime validation | Conditional; use project-configured environment, never invent credentials |
| Sentry | Android/runtime observability | Conditional for observability tasks; current project integration is already documented |
| PostHog | Telemetry contract | Conditional; #13 remains open |
| Figma | Design-system synchronization | Conditional; #11 remains open |
| Performance tooling | Measurable build/runtime baseline | Conditional; #10 remains open |
| Deployment infrastructure | Live rollout | Owner-gated; not part of default autonomous execution |

## 6. Least-privilege rule

Grant the smallest permissions that allow the active task. Prefer workspace-scoped write access for code execution, avoid unrestricted network access, never expose secrets to the model unnecessarily, and do not grant administrative repository privileges merely to simplify execution.

## 7. Permission blocker protocol

If an action fails because of permissions:

1. capture the exact error/evidence;
2. classify it as a permission/operator blocker;
3. identify the minimum permission required;
4. continue all independent work that remains possible;
5. ask the Owner only for the missing protected permission/action.

A permission blocker is not permission to bypass security controls.

## 8. Approval checklist for the final operating scheme

The Owner should explicitly approve:

- [ ] GPT/ChatGPT is the **only AI engineering participant**.
- [ ] GPT may autonomously execute the normal issue → branch → implementation → test → CI → repair → PR lifecycle.
- [ ] GPT may continue after CI results without conversational confirmation for routine non-protected work.
- [ ] Merge into `main` remains an Owner gate unless separately changed.
- [ ] Production deploy remains an Owner gate.
- [ ] Secrets/signing material remain Owner-only.
- [ ] Branch protection remains Owner-only.
- [ ] Irreversible destructive operations remain Owner-only.
- [ ] Repository documentation is the durable operating record and must stay synchronized with the approved policy.
