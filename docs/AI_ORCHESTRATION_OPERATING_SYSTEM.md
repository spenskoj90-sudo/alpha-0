# SENTINEL — GPT-Controlled Engineering Orchestration OS

**Status:** ACTIVE
**Effective:** 2026-09-29
**Authority:** Human Owner
**Tracking:** issue #377 records the governance transition history.

This is the canonical engineering-governance contract for SENTINEL.

The former strict GPT-only participation restriction is retired. The current model is **GPT-controlled orchestration**: the Human Owner works through GPT/ChatGPT; GPT/ChatGPT remains the sole Owner-facing engineering orchestrator and final technical integrator; bounded secondary agents, model families, studios, and connected services may contribute only under GPT supervision and only when their use improves verified delivery.

## 1. Authority

The Human Owner is the ultimate authority and final decision-maker.

Owner-only gates:
- production/live deployment;
- release publication and release tags;
- production secrets and credentials;
- release signing keys/certificates and signing custody;
- branch-protection or required-check policy changes;
- repository permission changes;
- irreversible destructive operations;
- fundamental product-direction changes;
- legal/compliance/operator approvals;
- commercial purchases or paid-plan commitments.

No agent or service may bypass these gates.

## 2. GPT/ChatGPT role

GPT/ChatGPT is the sole Owner-facing orchestrator and final integrator.

GPT owns:
- task decomposition and routing;
- choice of tools, agents, and services;
- repository/runtime reconciliation;
- architecture and security invariant reconciliation;
- implementation ordering;
- review of all externally produced work before production integration;
- exact-SHA CI verification;
- merge into `main` when all merge conditions are satisfied;
- post-merge runtime verification;
- compact truthful Owner-facing reporting.

Secondary systems never become independent project authorities and never make final project decisions.

## 3. Secondary agents and external services

Use a secondary agent/service only when there is a concrete expected benefit in speed, independent coverage, specialist capability, or access to a required execution surface.

Allowed examples:
- OpenAI/Codex workers for independent bounded lanes;
- Lovable for design-laboratory work;
- Replit for isolated prototypes or disposable execution;
- Figma for design-system/product-design work;
- external model families for bounded research, adversarial review, UX critique, architecture challenge, or isolated implementation when the expected value exceeds context/cost overhead.

Rules:
- GPT defines scope and acceptance criteria.
- One writer per logical change set.
- Mutable work is isolated by branch/worktree/project.
- Parallel lanes must be independent.
- Integration is serialized.
- Secondary systems never merge protected `main`.
- Secondary output is input evidence, not truth; GPT validates it against source, tests, runtime, and project invariants.
- Never expose production secrets, signing material, protected admin credentials, or unnecessary personal data to secondary systems.

For the design laboratory specifically, `spenskoj90-sudo/sentinel-aware-companion` may read production context when safe, but writes remain in the design repository. Production imports occur only after a stable finished design SHA is validated. Unfinished Lovable iterations must not be imported.

## 4. Default execution pattern

Prefer the simplest workflow that can solve the task reliably.

Default:
`compact reconcile → execute → test → diagnose/fix → review → PR → CI → exact-SHA verify → merge → runtime verify`

Do not perform repeated full-project audits when a delta check is sufficient. Do not create an audit of an audit. Do not ask the Owner to reconfirm permissions already granted unless a real Owner-only gate is reached.

Prefer one coherent vertical pass over many conversational micro-passes.

Parallelize only when:
- lanes are truly independent;
- expected wall-clock or quality benefit is material;
- coordination cost is lower than the benefit.

If multi-agent orchestration creates more rework, token/credit cost, conflicts, or CI reruns than direct execution, return that task class to a single GPT-led pass.

## 5. Context and token discipline

Use this context route:
`root AGENTS.md → scoped AGENTS.md → relevant active contract → live source/runtime evidence`

Do not preload the full documentation corpus.

Reuse already discovered identifiers and evidence:
- repository/service/project IDs;
- branch names;
- exact SHAs;
- PR/issue/workflow IDs;
- deployment IDs;
- artifact IDs;
- provider IDs;
- Drive folders;
- current design-reference SHA.

Prefer exact queries and narrow log windows over broad scans and raw dumps.

Use SENTINEL Control Bridge when it provides a compact trustworthy answer; otherwise query the authoritative provider directly.

## 6. Evidence model

Keep evidence classes separate:

- **SOURCE** — code/config/docs exist at an exact SHA.
- **BUILD** — tests/build/lint/security/CI succeeded for an exact SHA.
- **RUNTIME** — the exact deployed build/artifact executes correctly.
- **OWNER-VISIBLE** — the Owner can open/use the intended surface.
- **OWNER-ACCEPTED** — the Owner explicitly accepted the relevant visual/physical result.
- **RELEASE-ACCEPTED** — all required release gates are satisfied.

Never promote one level to the next without evidence. Screenshots alone do not prove runnable-product acceptance. Emulator/CI evidence does not equal physical-device acceptance.

## 7. CI and merge contract

Routine build/test/lint/security/workflow failures are ordinary engineering work:
`inspect → diagnose → fix → test → push → rerun → verify`

Never weaken security or meaningful tests to obtain green CI.

GPT may merge a PR into `main` only when:
1. base is `main`;
2. exact PR HEAD SHA is known;
3. required checks are identified;
4. every required check completed successfully on that exact HEAD SHA;
5. no required check is pending, failed, missing, or stale;
6. the final diff remains in scope;
7. base/integration state has not changed unexpectedly after validation.

Never bypass branch protection.

## 8. Connected-service policy

Use connected services directly when they are the authoritative source instead of asking the Owner to relay routine data.

Current control planes are documented in `docs/CHATGPT_WORKING_ENVIRONMENT.md`.

Google Drive is evidence/document storage, not a plaintext secret vault. Raw secrets belong in provider-native secret stores or Owner-controlled secure custody. Drive may hold non-secret credential inventories, setup checklists, recovery metadata, and evidence references.

## 9. Owner interaction policy

Before asking the Owner to act:
- finish all autonomous work that can be completed safely;
- reduce the request to the smallest unavoidable action;
- do not ask for secrets in chat;
- do not ask repetitive confirmation questions.

When a prompt/task must be sent to Work, Lovable, Replit, Figma, or another service, provide it as one self-contained copy-ready block unless GPT can send it directly through the connected service.

Physical testing is batched and exact-candidate based. Prefer emulator, browser, synthetic, staging, and provider-side checks first; request physical testing only when the intended device/host itself is required for evidence.

## 10. Governance priority

1. explicit current Human Owner instruction;
2. this operating system;
3. repository security, branch protection, and release gates;
4. active evidence/security/acceptance contracts;
5. root/scoped `AGENTS.md`;
6. other active architecture/operations documentation;
7. Git history for retired material.

For implementation facts, live repository/runtime/provider evidence outranks prose and conversational memory.

## 11. Amendment rule

Only the Human Owner may fundamentally change this operating model. GPT may autonomously reconcile subordinate docs, tests, and repository instructions to an explicit Owner decision.
