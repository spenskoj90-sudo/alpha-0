# SENTINEL — Autonomous Permissions & Tool Matrix

**Tracking issue:** #167  
**Status:** ACTIVE — approved by Human Owner on 2026-09-06.  
**Canonical governance:** `docs/GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md`

This document records the capabilities required for autonomous engineering and the actions that remain Owner-gated. Actual tool availability and repository policy always prevail.

## 1. Engineering capabilities

| Capability | Current rule |
|---|---|
| GitHub repository read | Required and available through connected integration |
| GitHub repository write | Required for normal branches/commits/PRs where permitted |
| GitHub Actions/checks/status read | Required for exact-SHA validation |
| Workflow write | Permitted only within task scope; never to weaken gates |
| Pull-request write | Required for normal PR lifecycle |
| Issue write | Required for task/evidence tracking |
| Local/isolated execution | Required for full code/test/build autonomy where available |
| Workspace write | Required for implementation where available |
| Network access | Least privilege; only task-required external access |

## 2. Observed GitHub integration permissions

Previously observed repository permissions include `contents: write`, `pull_requests: write`, `issues: write`, `actions: write`, `workflows: write`, `checks: read`, `statuses: read`, `metadata: read` and `emails: read`. These permissions do not grant access to secret values and never override repository policy or Owner gates.

## 3. GPT autonomous actions

Within actual granted permissions and active scope GPT may inspect, branch, edit, test, build, commit, push permitted branches, create/update PRs/issues, inspect CI/checks/logs/artifacts exposed by the connector, diagnose/fix failures and merge a PR when the exact-SHA merge gate is fully satisfied.

## 4. Owner-only actions

- production secret/credential access or mutation;
- signing keys, certificates and release keystore custody changes;
- branch-protection or required-check policy changes;
- irreversible destructive repository/database operations;
- production/live deployment;
- release publication/tagging;
- fundamental product-direction decisions;
- actions requiring explicit legal/compliance/operator approval.

## 5. Permission blocker protocol

If a required action fails because of permissions, GPT must capture the exact error, classify the blocker, identify the minimum required permission, continue independent work, and request Owner action only for the protected boundary. Security controls must never be bypassed.

## 6. Least privilege

Grant/use the smallest permissions needed for the active task. Never inspect or print secrets unnecessarily. Never grant administrative access merely to simplify execution. Never change required checks to manufacture a green result.

## 7. Non-delegation

No external AI is authorized as a fallback, reviewer, researcher, security auditor, implementer or CI agent. GPT is the sole AI engineering participant.
