CREATE TABLE IF NOT EXISTS sentinel_sessions (
    session_id VARCHAR(128) PRIMARY KEY,
    subject_id VARCHAR(256) NOT NULL,
    token_hash BYTEA NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    CONSTRAINT sentinel_session_token_hash_size CHECK (octet_length(token_hash) = 32),
    CONSTRAINT sentinel_session_subject_nonempty CHECK (length(subject_id) BETWEEN 1 AND 256),
    CONSTRAINT sentinel_session_expiry_present CHECK (expires_at IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_sentinel_sessions_expiry
    ON sentinel_sessions (expires_at);

CREATE INDEX IF NOT EXISTS idx_sentinel_sessions_subject
    ON sentinel_sessions (subject_id);

CREATE INDEX IF NOT EXISTS idx_sentinel_sessions_active
    ON sentinel_sessions (session_id)
    WHERE revoked_at IS NULL;
