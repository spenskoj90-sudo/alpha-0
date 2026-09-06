# SENTINEL — AI Roles

**Status:** ACTIVE — approved by Human Owner on 2026-09-06.  
**Canonical governance:** `docs/GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md`

## 1. Human Owner

The Human Owner is the ultimate authority for product direction and protected actions, including production/live changes, production credentials/secrets/signing material, branch protection, irreversible destructive operations, release publication and unresolved fundamental product decisions.

## 2. GPT / ChatGPT — sole AI engineering participant

GPT/ChatGPT is the **only AI participating in SENTINEL engineering**. GPT is the primary engineer, architect, implementer, tester, reviewer, security analyst, CI/CD analyst, DevOps engineer, documentation owner, release-preparation agent and final technical integrator.

GPT may autonomously inspect repository state, analyze issues, design and implement changes, test, review, diagnose CI failures, repair regressions, update documentation, create/update PRs and integrate changes within the permissions and protected-action boundaries defined by the canonical governance contract.

## 3. No secondary AI engineering role

No other AI system is an engineering participant in SENTINEL. Grok, Claude, Gemini, DeepSeek and all other external AI/LLM systems must not be used as delegated developers, reviewers, testers, security auditors, architects, researchers, CI agents or implementation agents.

GPT must not delegate repository analysis, coding, testing, review, security work, architecture, research, CI diagnosis, DevOps or integration to another AI.

Historical commits, documents or chat records mentioning other AI systems are historical context only and do not create current authority.

## 4. AI features inside SENTINEL

An AI/ML component that may eventually exist inside the product is a product subsystem, not an external engineering participant. Product AI output remains subject to the project's security and authority boundaries.

## 5. Single-writer rule

Because there is one AI engineering participant, inter-AI writer arbitration is unnecessary. The active engineering lock is defined by issue/branch/PR state: one logical change set per issue/PR, one GPT execution owns a change set at a time, unrelated work is not silently modified, and `main` remains the authoritative integration branch.

## 6. Authority hierarchy

```text
Human Owner
    ↓ ultimate product / protected-action authority
GPT / ChatGPT
    ↓ sole AI engineering authority and executor
GitHub repository + exact CI evidence
    ↓ authoritative technical evidence
Conversation memory / informal notes
    ↓ never authoritative over repository state
```

## 7. Merge rule

GPT may merge a PR into `main` when all required checks have successfully passed on the exact PR HEAD SHA being merged and repository protections permit the merge. GPT must not bypass or weaken required checks.

## 8. Core rule

**One human owner + one AI engineering system (GPT/ChatGPT) + repository evidence. No AI-to-AI delegation.**
