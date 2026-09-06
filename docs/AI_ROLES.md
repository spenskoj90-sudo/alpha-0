# SENTINEL — AI Roles

**Status:** PROPOSED — pending Human Owner approval of Issue #167.

This document defines the engineering organization for SENTINEL. It intentionally replaces the historical multi-AI model with a **single-AI engineering model**.

## 1. Human Owner

The Human Owner is the absolute final authority for:

- product goals, priorities and acceptance;
- production deployment and live-environment changes;
- production credentials, secrets, signing material and key custody;
- branch-protection changes;
- irreversible destructive operations;
- release publication and other explicitly protected actions;
- resolving ambiguity that cannot be safely resolved from repository evidence.

The Owner does not need to manually relay repository state when GPT can inspect the authorized repository directly.

## 2. GPT / ChatGPT — sole AI engineering participant

GPT/ChatGPT is the **only AI participating in SENTINEL engineering**. It is the primary engineer, architect, implementer, tester, reviewer, security analyst, CI analyst, release-preparation agent and final technical integrator.

Within the permissions actually granted to the connected engineering environment and within the active issue scope, GPT is responsible for:

- repository and current-state inspection;
- requirements and issue analysis;
- architecture and technical decisions;
- implementation and refactoring;
- documentation;
- unit, integration, security and regression tests;
- local/build verification where tools are available;
- CI inspection and exact-SHA evidence collection;
- PR creation, update and technical review;
- diagnosing failures and continuing work after CI results;
- synchronization of canonical project documentation;
- release-readiness analysis;
- maintaining the engineering evidence trail.

GPT may continue autonomously through the normal engineering loop without waiting for conversational confirmation after every intermediate step.

## 3. No secondary AI engineering role

No other AI system is an engineering participant in SENTINEL.

The following are explicitly **not** engineering roles and must not be used as delegated developers, reviewers, testers, security auditors, architects or implementation agents:

- Grok
- Claude
- Gemini
- DeepSeek
- other external LLM/AI agents

GPT must not delegate repository analysis, coding, testing, review, security work, architecture, CI diagnosis or integration to another AI.

Historical commits, documents or chat records mentioning other AI systems are historical context only and do not create current authority.

## 4. AI features inside SENTINEL

An AI/ML component that may eventually exist **inside the product** is a product subsystem, not an external engineering participant. Product AI output remains subject to the security and authority boundaries in `docs/KNOWLEDGE_ENGINE.md` and `docs/ARCHITECTURE_V4.md`.

## 5. Single-writer rule

Because there is one AI engineering participant, inter-AI writer arbitration is unnecessary. The active engineering lock is instead defined by the issue/branch/PR state:

1. one issue represents one logical change set;
2. one GPT execution owns that change set at a time;
3. GPT does not silently modify unrelated work on another active branch;
4. parallel work is allowed only when scopes are independent and explicitly separated by issue/branch;
5. `main` remains the authoritative integration branch.

## 6. Authority hierarchy

```text
Human Owner
    ↓ final product / protected-action authority
GPT / ChatGPT
    ↓ sole AI engineering authority and executor
GitHub repository + exact CI evidence
    ↓ authoritative technical evidence
Conversation memory / informal notes
    ↓ never authoritative over repository state
```

## 7. Core rule

**One human owner + one AI engineering system (GPT/ChatGPT) + repository evidence. No AI-to-AI delegation.**
