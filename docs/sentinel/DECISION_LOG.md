# SENTINEL — Decision Log

Current accepted decisions. No silent architectural drift is permitted.

- D-001: Start as a modular monolith.
- D-002: Sentinel Core is the single source of truth.
- D-003: Authorization is centralized and server-side.
- D-004: Default Deny is mandatory.
- D-005: Least Privilege is mandatory.
- D-006: Role is not direct authorization; effective access requires Identity + Role + Permission + Scope + Entitlement + Policy + Context.
- D-007: Scope is first-class, dynamic and versionable.
- D-008: Commercial lifecycle is Payment → Order → Subscription → Entitlement.
- D-009: Billing/Finance is separate from Authorization.
- D-010: Game Knowledge and live Game Interaction are separate concerns.
- D-011: Telemetry follows Local-First / Server-Minimal principles.
- D-012: Legal/Data Governance is architectural.
- D-013: Character Identity, Equipment State, Actual Item and Transmog are separate concepts.
- D-014: AI uses Knowledge Engine, Context Engine and Confidence System.
- D-015: Architecture performance PASS does not equal a measured benchmark.
- D-016: Actual source code is authoritative in GitHub.
- D-017: Accepted baseline is Architecture v3 + Implementation Contract v1 + Test Matrix v1.
- D-018: Sentinel must be transferable through durable project-state documentation.
- D-019: The GitHub repository remains in place; this is a ChatGPT context migration, not repository ownership transfer.
- D-020: The next implementation milestone is the Minimal Alpha Release Candidate.

## Change rule

Any change to an accepted architectural invariant must identify the reason, affected components, affected tests, updated version/document, and be recorded here before it is treated as accepted.
