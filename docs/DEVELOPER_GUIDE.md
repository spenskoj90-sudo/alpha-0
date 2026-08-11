# SENTINEL Developer Guide

## Local development

### Core

```bash
cd server
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest
uvicorn app.main:app --reload
```

### Android

Open the repository in Android Studio and run the `app` module. The CI build must remain the source of truth for release artifacts.

### Web

```bash
cd web
pnpm install
pnpm dev
```

Next.js App Router uses filesystem-based routes and server/client component boundaries. Keep privileged data access on the server side; never put authorization secrets in browser bundles.

## Coding rules

- Domain decisions are deterministic and testable.
- Controllers validate input and delegate to domain services.
- Database writes are transactional.
- Events are immutable facts.
- Every security-sensitive change gets a regression test.
- No custom cryptography beyond composition of established primitives.
- No AI-generated action is treated as an authorization decision.

## Pull request acceptance

Use the sequence `FAIL → root cause → FIX → regression → PASS → ACCEPTED`. A passing unit test alone does not make a component production-ready; integration, security and artifact checks are required.
