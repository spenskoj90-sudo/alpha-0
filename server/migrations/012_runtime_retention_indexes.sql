-- Bounded operational-retention support. These indexes keep scheduled cleanup
-- from degrading into full-table scans as transient runtime tables grow.

CREATE INDEX IF NOT EXISTS proof_request_ids_created_at_idx
    ON proof_request_ids(created_at);

CREATE INDEX IF NOT EXISTS security_failures_failed_at_idx
    ON security_failures(failed_at);

CREATE INDEX IF NOT EXISTS sessions_runtime_retention_idx
    ON sessions(expires_at, refresh_expires_at);

CREATE INDEX IF NOT EXISTS outbox_terminal_retention_idx
    ON outbox_events(available_at)
    WHERE status IN ('DONE', 'FAILED');

CREATE INDEX IF NOT EXISTS worker_terminal_retention_idx
    ON worker_jobs(available_at)
    WHERE status IN ('DONE', 'FAILED');
