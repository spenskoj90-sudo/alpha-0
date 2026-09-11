# Recommendation Context Projection v1

Projects validated `UGSState` into a bounded recommendation context.

The projection preserves state identity, source identity, quality, selected player/target fields, event metadata and provenance while deliberately excluding raw adapter event payloads. It performs no authorization, network I/O or action execution.
