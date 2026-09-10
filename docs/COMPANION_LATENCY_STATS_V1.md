# SENTINEL Companion Latency Statistics v1

**Status:** ACTIVE IMPLEMENTATION CONTRACT

## Purpose

Provide a bounded local statistics primitive for Companion transport/runtime latency observations. It supports reproducible operational evidence without retaining an unbounded history.

## Contract

- Only non-negative latency values are accepted.
- The retained sample window is bounded by `max_samples`.
- Statistics describe the latest retained observations, not an unbounded lifetime population.
- Snapshot fields are count, minimum, maximum, arithmetic mean and a deterministic p95 index.
- Empty snapshots expose no fabricated measurements.
- The primitive performs no network, persistence, authorization or action execution.

## Evidence boundary

This is measurement infrastructure, not evidence that a latency target has been achieved. Real end-to-end/device measurements remain required before performance claims are made.
