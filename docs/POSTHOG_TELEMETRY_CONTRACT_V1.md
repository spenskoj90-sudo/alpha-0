# SENTINEL — PostHog / Runtime Telemetry Contract v1

**Issue:** #13
**Status:** CONTRACT DEFINED — instrumentation rollout is separate
**Version:** 1.0

## 1. Purpose

Define the minimum privacy-preserving telemetry contract for product/runtime validation without making telemetry a CI acceptance dependency. The contract is intentionally small: startup, critical user flows, failures, performance signals and release validation.

PostHog is an optional sink. The event taxonomy is provider-neutral so the application can disable or replace the sink without changing product semantics.

## 2. Data-minimization rules

Telemetry MUST NOT contain:

- passwords, access/refresh tokens, enrollment secrets or API keys;
- private signing material or device private keys;
- raw authorization headers/cookies;
- full chat/voice transcripts by default;
- raw game payloads or high-cardinality combat logs;
- precise location unrelated to the product function;
- arbitrary request/response bodies.

Use opaque identifiers and coarse categories. Prefer counters/durations over raw payloads.

## 3. Event envelope

Every accepted telemetry event has:

```text
event_name
schema_version
event_id
occurred_at
session_id (opaque, short-lived)
app_version
platform
environment (debug|staging|production)
release_id
properties (allowlisted)
```

`properties` are allowlisted per event. Unknown properties are rejected or dropped at the telemetry boundary.

## 4. Event taxonomy

| Event | Purpose | Required properties |
|---|---|---|
| `app_started` | startup success/failure context | `startup_mode`, `cold_start` |
| `app_ready` | first usable UI | `startup_duration_ms`, `screen` |
| `auth_started` | auth funnel | `method` |
| `auth_succeeded` | auth success | `method`, `duration_ms` |
| `auth_failed` | auth failure | `method`, `failure_class`, `duration_ms` |
| `refresh_succeeded` | session continuity | `duration_ms` |
| `refresh_failed` | session continuity failure | `failure_class` |
| `critical_flow_started` | named product flow | `flow`, `entrypoint` |
| `critical_flow_completed` | named product flow success | `flow`, `duration_ms` |
| `critical_flow_failed` | named product flow failure | `flow`, `failure_class`, `duration_ms` |
| `api_request_failed` | client-visible API failure | `route_class`, `status_class`, `duration_ms` |
| `app_error` | non-fatal application error | `error_class`, `component` |
| `performance_sample` | coarse runtime performance | `metric`, `value`, `unit` |
| `release_validation` | release smoke result | `check`, `result`, `version` |

Event names are semantic and do not expose endpoint paths, SQL, exception text or user content.

## 5. Failure classes

Use a fixed low-cardinality vocabulary:

```text
network
unauthorized
forbidden
validation
server_5xx
timeout
storage
configuration
compatibility
unknown
```

Do not send raw exception messages to PostHog. Detailed diagnostics belong in appropriately scrubbed logs/error reporting.

## 6. Performance signals

Only emit measurements with deterministic meaning. Initial metrics:

- `startup_duration_ms`
- `auth_duration_ms`
- `critical_flow_duration_ms`
- `api_duration_ms`
- `refresh_duration_ms`

Runtime telemetry is for trend detection. Release/CI acceptance continues to require exact-SHA test/device evidence as defined by `docs/RELEASE_GATES.md` and `docs/SENTINEL_PERFORMANCE_BASELINE.md`.

## 7. Privacy and retention

Recommended default retention:

- product/runtime events: **30 days**;
- release-validation events: **90 days**;
- security-sensitive audit data: **not stored in PostHog;** use the repository's security/audit system.

Production rollout must honor the applicable privacy/legal requirements for the deployment jurisdiction. If consent or a user-facing telemetry control is required by the deployment context, telemetry MUST remain disabled until that requirement is satisfied.

## 8. Sampling

Do not sample correctness/failure signals required to detect release regressions. High-volume performance samples may use bounded sampling after their metric definition is validated. Sampling decisions must be documented and deterministic enough to preserve trend comparability.

## 9. Identity

Do not use email addresses or raw account identifiers as the default PostHog distinct ID. Prefer a rotating opaque installation/session identifier. Cross-session linkage, if later required, needs an explicit privacy review and a separate contract amendment.

## 10. Security boundary

The telemetry client is untrusted infrastructure from the authorization perspective. Failure to send telemetry MUST NOT fail authentication, authorization, gameplay-critical logic, or user actions.

Telemetry MUST be asynchronous/bounded and fail open with respect to product functionality while failing closed with respect to sensitive-data emission.

## 11. Acceptance for Issue #13

Issue #13 is complete at the contract-definition stage when:

1. taxonomy and allowlisted properties are versioned here;
2. retention/privacy rules are explicit;
3. measurable product/engineering signals are named;
4. telemetry is explicitly excluded from CI acceptance evidence;
5. rollout/instrumentation is treated as a separate implementation task.

Dashboards, alerts and broad instrumentation are deliberately not part of this issue.
