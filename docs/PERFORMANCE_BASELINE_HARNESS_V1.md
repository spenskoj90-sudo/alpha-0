# Performance Baseline Harness v1

`measure_latency_samples` turns externally measured `(sent_at, received_at)` pairs into the existing bounded latency statistics. It performs no sleeps, network calls or synthetic wall-clock measurements, so the resulting snapshot can be tied to real runtime evidence without overstating it.
