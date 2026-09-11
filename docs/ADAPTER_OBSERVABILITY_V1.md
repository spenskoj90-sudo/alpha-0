# SENTINEL Adapter Observability v1

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Purpose

Expose privacy-safe adapter activity through the existing bounded Companion telemetry sink.

## Contract

- Only adapter metadata is emitted: adapter id, game id, event type, sequence and data quality.
- Raw adapter payload, actor names, chat text and other event contents are not copied into telemetry.
- The bridge is observational and performs no authorization or action execution.
- Sink bounds and failure semantics remain owned by the existing telemetry sink.

## Evidence boundary

This establishes a metadata-only observability bridge. It does not claim production telemetry ingestion.
