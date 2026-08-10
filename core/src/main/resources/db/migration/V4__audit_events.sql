CREATE TABLE IF NOT EXISTS sentinel_audit_events (
    id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMPTZ NOT NULL,
    action VARCHAR(128) NOT NULL,
    subject_id VARCHAR(256) NOT NULL,
    outcome VARCHAR(8) NOT NULL,
    reason VARCHAR(256),
    fingerprint CHAR(64),
    CONSTRAINT sentinel_audit_outcome CHECK (outcome IN ('ALLOW', 'DENY')),
    CONSTRAINT sentinel_audit_fingerprint_format CHECK (
        fingerprint IS NULL OR fingerprint ~ '^[0-9a-f]{64}$'
    )
);

CREATE INDEX IF NOT EXISTS idx_sentinel_audit_subject_time
    ON sentinel_audit_events (subject_id, event_time DESC);

CREATE INDEX IF NOT EXISTS idx_sentinel_audit_action_time
    ON sentinel_audit_events (action, event_time DESC);
