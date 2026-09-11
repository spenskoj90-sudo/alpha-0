# Companion + Intelligence Acceptance v1

This increment tightens the current vertical slice at the presentation, provider-metadata, and local performance evidence boundaries.

## Integrated blocks

1. Bounded presentation-text normalization at the Companion composition boundary.
2. Explicit rejection of oversized presentation content rather than silent truncation.
3. Bounded provider/model/provenance/confidence validation before presentation.
4. Preservation of the presentation-only action boundary (`action_capable == false`).
5. Deterministic local callable performance samples.
6. Deterministic summary statistics over supplied local samples.
7. Existing Companion transport latency samples remain reproducible from explicit timestamps.
8. Bounded provider registry description exposes only provider/model/default metadata and no credentials or implementation internals.
9. Regression coverage for the above boundaries.
10. Documentation of the evidence limits and non-goals.

## Evidence limits

The performance primitives measure local callable or supplied timestamp intervals. They do not claim remote end-to-end latency, production throughput, or production resource usage.

Provider metadata is descriptive only. It does not provision credentials or perform external AI calls.

Companion presentation remains observational: presentation messages cannot authorize or execute actions.

Exact WoW 3.3.5a/private-server capability validation remains UNVERIFIED until exact-environment L3 evidence is available.
