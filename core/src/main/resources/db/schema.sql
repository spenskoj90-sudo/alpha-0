CREATE TABLE IF NOT EXISTS sentinel_devices (
    fingerprint CHAR(64) PRIMARY KEY,
    public_key BYTEA NOT NULL,
    state VARCHAR(16) NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT sentinel_device_fingerprint_format CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
    CONSTRAINT sentinel_device_public_key_size CHECK (octet_length(public_key) BETWEEN 1 AND 512),
    CONSTRAINT sentinel_device_state CHECK (state IN ('PENDING', 'ACTIVE', 'REVOKED'))
);
CREATE INDEX IF NOT EXISTS idx_sentinel_devices_state ON sentinel_devices (state);
CREATE INDEX IF NOT EXISTS idx_sentinel_devices_updated ON sentinel_devices (updated_at);

CREATE TABLE IF NOT EXISTS sentinel_device_recovery_codes (
    device_fingerprint CHAR(64) NOT NULL REFERENCES sentinel_devices(fingerprint) ON DELETE CASCADE,
    code_hash BYTEA NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    PRIMARY KEY (device_fingerprint, code_hash),
    CONSTRAINT sentinel_recovery_hash_size CHECK (octet_length(code_hash) = 32),
    CONSTRAINT sentinel_recovery_expiry CHECK (expires_at IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_sentinel_recovery_expiry ON sentinel_device_recovery_codes (expires_at);

CREATE TABLE IF NOT EXISTS sentinel_device_challenges (
    challenge_id VARCHAR(256) PRIMARY KEY,
    nonce BYTEA NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    expected_fingerprint CHAR(64),
    consumed_at TIMESTAMPTZ,
    CONSTRAINT sentinel_challenge_nonce_size CHECK (octet_length(nonce) BETWEEN 32 AND 64),
    CONSTRAINT sentinel_challenge_fingerprint_format CHECK (expected_fingerprint IS NULL OR expected_fingerprint ~ '^[0-9a-f]{64}$'),
    CONSTRAINT sentinel_challenge_expiry CHECK (expires_at IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_sentinel_device_challenges_expiry ON sentinel_device_challenges (expires_at);
CREATE INDEX IF NOT EXISTS idx_sentinel_device_challenges_active ON sentinel_device_challenges (challenge_id) WHERE consumed_at IS NULL;

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
CREATE INDEX IF NOT EXISTS idx_sentinel_sessions_expiry ON sentinel_sessions (expires_at);
CREATE INDEX IF NOT EXISTS idx_sentinel_sessions_subject ON sentinel_sessions (subject_id);
CREATE INDEX IF NOT EXISTS idx_sentinel_sessions_active ON sentinel_sessions (session_id) WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS sentinel_audit_events (
    id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMPTZ NOT NULL,
    action VARCHAR(128) NOT NULL,
    subject_id VARCHAR(256) NOT NULL,
    outcome VARCHAR(8) NOT NULL,
    reason VARCHAR(256),
    fingerprint CHAR(64),
    CONSTRAINT sentinel_audit_outcome CHECK (outcome IN ('ALLOW', 'DENY')),
    CONSTRAINT sentinel_audit_fingerprint_format CHECK (fingerprint IS NULL OR fingerprint ~ '^[0-9a-f]{64}$')
);
CREATE INDEX IF NOT EXISTS idx_sentinel_audit_subject_time ON sentinel_audit_events (subject_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_sentinel_audit_action_time ON sentinel_audit_events (action, event_time DESC);
