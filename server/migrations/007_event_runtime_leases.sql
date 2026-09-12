-- PASS 2 event-processing runtime: explicit lease ownership.
-- A lease token prevents one worker from completing another worker's claim.
ALTER TABLE outbox_events
    ADD COLUMN IF NOT EXISTS locked_by TEXT;

ALTER TABLE worker_jobs
    ADD COLUMN IF NOT EXISTS locked_by TEXT;

CREATE INDEX IF NOT EXISTS outbox_processing_lease_idx
    ON outbox_events(status, locked_until);

CREATE INDEX IF NOT EXISTS worker_processing_lease_idx
    ON worker_jobs(status, locked_until);
