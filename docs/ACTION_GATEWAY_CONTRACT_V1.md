# SENTINEL — Action Gateway Contract v1

**Status:** ACTIVE FOUNDATION  
**Version:** 1.0  
**Scope:** Core policy boundary for action-capable integrations

## Purpose

The Action Gateway is the explicit boundary between an authenticated principal, policy evaluation, integration capability evidence and any future action executor.

The gateway authorizes **intent**. It does not execute game actions, manipulate processes, alter entitlements, bypass client/server controls, or become an authorization source outside the server policy engine.

## Decision flow

```text
Authenticated Principal
        |
        v
Action Intent + Integration Evidence
        |
        v
Policy Engine
        |
        +--> DENY
        |
        +--> CONFIRM / ALLOW
                    |
                    v
              Future Executor
```

## Invariants

1. **Server authority:** authorization is derived from the server-side policy engine and principal scopes/roles.
2. **Default deny:** no matching policy denies the request.
3. **Capability is not authorization:** capability status can gate an action prerequisite, but cannot grant permission.
4. **Unverified is not usable:** `UNVERIFIED` and `UNAVAILABLE` capability evidence cannot authorize an action.
5. **Automatic execution is disabled in this MVP boundary:** `AUTOMATIC` mode is denied even when policy and capability evidence otherwise permit the request.
6. **User confirmation:** a policy-approved recommendation is not an execution grant; it returns `CONFIRM` until the user explicitly confirms.
7. **Policy deny wins:** an explicit policy denial cannot be overridden by capability evidence.
8. **No execution surface:** the gateway exposes authorization decisions only; it contains no executor API.
9. **Bounded input:** action/resource/capability identifiers are length- and character-bounded.
10. **Fail closed:** malformed or insufficient evidence must not turn into permission.

## Action modes

- `RECOMMENDATION` — produce an action decision suitable for a user-facing recommendation; never an execution grant.
- `USER_CONFIRMED` — policy-approved, capability-supported intent after an explicit user confirmation boundary.
- `AUTOMATIC` — denied in the first vertical slice; autonomous game action is not MVP.

## Evidence semantics

`CapabilityStatus.AVAILABLE` is only valid with L3 evidence under the Game Adapter Contract. `LIMITED` may be usable where the integration contract permits it. Neither status overrides Policy Engine authorization.

## Non-goals

This contract does not define a game executor, launcher automation, memory/process access, authentication bypass, anti-cheat/DRM bypass, or production automation policy. Exact environment capabilities remain subject to the adapter and evidence contracts.
