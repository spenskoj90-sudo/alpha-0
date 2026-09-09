# Companion Compatibility and Version Negotiation v1

## Purpose

This increment adds deterministic compatibility negotiation ahead of the existing Companion handshake. It selects a supported version no newer than the peer's offered version, requires the same major version, and fails closed when any required dimension has no compatible version.

## Negotiated dimensions

The negotiation covers:

- Companion protocol version;
- UGS schema version;
- adapter contract version;
- Core protocol version;
- capability profile.

Version dimensions use strict `major.minor` syntax. The selected version is the highest mutually compatible supported minor version. Capability profiles remain exact identifiers rather than version-ranged values.

## Security boundary

Negotiation does not authenticate a peer or grant authorization. A successful result only establishes compatible protocol metadata. Existing peer authentication and the Companion handshake remain separate boundaries.

Any malformed version or unsupported compatibility dimension fails closed. No fallback to a different major version is permitted.

## Resource and determinism constraints

Inputs are finite tuples and strict version strings. Negotiation performs deterministic bounded comparisons and returns an immutable result. It does not perform network I/O or external provider calls.

## Scope

This increment does not claim transport integration, peer authentication, authorization, real-device latency, or production deployment. Those remain separate acceptance gates.
