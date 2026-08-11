# SENTINEL CORE

FastAPI modular monolith. PostgreSQL is the authoritative persistence layer.

## Local development

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
export SENTINEL_ENVIRONMENT=development
uvicorn sentinel_core.main:app --reload
```

Production must not use the development enrollment registry or development enrollment token. Production deployment requires PostgreSQL migrations and a persistent device/session repository.

## Tests

```bash
pytest -q
```

## Security rules

- No authorization decisions from client-supplied roles, scopes, entitlements or billing fields.
- Unknown actions deny.
- Device keys are P-256 ECDSA and fingerprinted as SHA-256 of DER SubjectPublicKeyInfo.
- Session establishment uses server challenge + domain-separated signature.
- Challenges are one-time and time-bounded.
- AI/knowledge output is non-authoritative and cannot directly mutate canonical state.
