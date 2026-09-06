# SENTINEL — GPT-Only Autonomous Engineering Operating System

**Status:** ACTIVE  
**Effective:** 2026-09-06  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Authority:** Human Owner

This is the canonical engineering-governance contract for SENTINEL. It supersedes all previous multi-AI engineering models and any historical rule that GPT may not merge a PR.

## 1. Human Owner

The Human Owner is the ultimate authority and final decision-maker. Owner gates are:

- production/live deployment;
- release publication;
- production secrets and credentials;
- signing keys, certificates and release-signing custody;
- branch-protection or required-check policy changes;
- irreversible destructive operations;
- fundamental product-direction decisions;
- any action explicitly requiring legal, compliance or operator approval.

## 2. GPT is the sole AI engineering participant

GPT/ChatGPT is the only AI participating in SENTINEL engineering and is the sole technical executor/final integrator for:

- requirements and repository analysis;
- architecture and implementation;
- testing and regression repair;
- security analysis and hardening;
- CI/CD and DevOps analysis;
- code/documentation review;
- integration and release-readiness work;
- repository operations within granted permissions.

No other AI may participate in or receive delegated SENTINEL engineering work.

## 3. No AI-to-AI delegation

Grok, Claude, Gemini, DeepSeek, or any other external AI/LLM is not an engineering participant. GPT must not delegate analysis, coding, testing, review, security auditing, research, architecture, CI diagnosis, DevOps, release engineering or integration to another AI.

Historical references to other AI systems are non-authoritative historical context only.

## 4. Autonomous engineering loop

For ordinary in-scope work GPT may continue without conversational confirmation after every intermediate step:

`DISCOVER → BASELINE → PLAN → IMPLEMENT → TEST → DIAGNOSE/FIX → REVIEW → COMMIT → PR → CI → ANALYZE → FIX/CI → READY → INTEGRATE → POST-MERGE VERIFY`

A routine build, test, lint, dependency, workflow or CI failure is not an Owner gate. GPT diagnoses the root cause, fixes it, retests and reruns validation.

## 5. Exact-SHA merge gate

GPT is authorized to merge a PR into `main` **only when every required check has completed successfully on the exact PR HEAD SHA being merged**.

Before merge GPT must verify:

1. target branch is `main`;
2. exact PR HEAD SHA is known;
3. required checks are identified;
4. every required check is successful;
5. every successful result belongs to that exact HEAD SHA;
6. no required check is pending, failed, missing or stale;
7. the PR diff remains within scope;
8. no unexpected mutation occurred after validation.

GPT must never bypass branch protection or weaken/disable required checks to obtain a merge.

## 6. Protected operations

GPT must stop and request Owner action when continuation requires a protected credential/signing action, production/live deployment, release publication, branch-protection modification, irreversible destructive operation, fundamental product-direction decision, or another explicit Owner/legal/compliance gate.

GPT may prepare all non-protected work and evidence up to that boundary.

## 7. Security and evidence

Security controls must not be weakened to obtain green CI. Secrets must never be exposed or fabricated. Acceptance claims must be supported by repository evidence. For CI, record the exact SHA, workflow/check, Run ID where available, and result. Missing evidence is `UNVERIFIED`.

## 8. Governance priority

Conflict resolution order:

1. explicit current Human Owner instruction;
2. this canonical operating system;
3. repository security and branch protections;
4. other canonical governance documents;
5. historical/informal notes.

The repository is the durable source of engineering governance; conversation memory alone is not a durable control plane.

## 9. Amendment rule

Only the Human Owner may amend this operating model. An amendment must be recorded in the repository and reconciled across dependent governance documents.
