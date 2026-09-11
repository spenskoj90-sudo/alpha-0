# Companion Persistent Runtime Telemetry v1

Composes the bounded local Companion telemetry sink with the existing PostgreSQL persistence sink when an engine is explicitly supplied.

Persistence is therefore opt-in at construction time and cannot silently appear in local tests or default runtime construction. The persistent sink retains its bounded event contract and retention semantics.
