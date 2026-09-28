# SENTINEL Staging Synthetic Gate

**Status:** ACTIVE  
**Tracking issue:** #388

A green repository build does not prove that deployed staging surfaces are connected.

For each protected-main push, the `Staging Synthetic Runtime` workflow waits for the exact source SHA on Control Bridge and then verifies:

- Core `/healthz` is UP and reports repository VERSION;
- authenticated Web root is reachable;
- Web `/api/session/login` actually reaches Core, using a unique nonexistent `@example.invalid` identity and requiring the authoritative `401 INVALID_CREDENTIALS` response;
- Public Website root is reachable;
- the pre-release robots guard still disallows indexing.

The check creates no account and uses no real user identity, payment, email, federated provider or device binding. Its JSON artifact is exact-SHA runtime evidence, not visual acceptance or production readiness.
