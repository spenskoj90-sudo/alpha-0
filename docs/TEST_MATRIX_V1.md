# SENTINEL Test Matrix v1

| Gate | Area | Evidence | Release condition |
|---|---|---|---|
| A | Key management | Operator recovery-package verification + no private key in repository | PASS evidence recorded |
| B | Backend security | Security unit/integration suite: default deny, scope, device proof, replay, session, IDOR boundaries | All tests pass |
| C | Persistence | Migration/schema lint + application tests | Schema is syntactically valid and tests pass |
| D | Android | Debug build + unit tests + instrumented Keystore identity test | All Android checks pass |
| E | API | OpenAPI contract present and endpoint smoke checks | Contract and smoke checks pass |
| F | Security testing | Negative authorization and cryptographic verification tests | All negative tests pass |
| G | Reliability | Idempotency, replay, malformed-input and health checks | All reliability tests pass |
| H | Performance | Authorization/event smoke budget; no benchmark claim | Budget passes; benchmark remains separate |
| I | Deployment | Container/config validation and secret hygiene | Config validates without embedded secrets |
| J | Release | Version consistency, artifact existence and clean release metadata | RC1 artifact/evidence complete |

## RC1 commands

### Server

```bash
cd server
python -m pytest
```

### Android

```bash
gradle --no-daemon assembleDebug
gradle --no-daemon test
gradle --no-daemon connectedDebugAndroidTest
```

### Release signing

```bash
gradle --no-daemon assembleRelease
```

Release signing is intentionally not required for ordinary pull-request validation. It is required for the final signed RC1 artifact and must use the verified release keystore outside source control.
