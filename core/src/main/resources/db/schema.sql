CREATE TABLE IF NOT EXISTS sentinel_device_challenges (
    challenge_id VARCHAR(256) PRIMARY KEY,
    nonce BYTEA NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    expected_fingerprint CHAR(64),
    consumed_at TIMESTAMPTZ,
    CONSTRAINT sentinel_challenge_nonce_size CHECK (octet_length(nonce) BETWEEN 32 AND 64),
    CONSTRAINT sentinel_challenge_fingerprint_format CHECK (
        expected_fingerprint IS NULL OR expected_fingerprint ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT sentinel_challenge_expiry CHECK (expires_at IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_sentinel_device_challenges_expiry
    ON sentinel_device_challenges (expires_at);

CREATE INDEX IF NOT EXISTS idx_sentinel_device_challenges_active
    ON sentinel_device_challenges (challenge_id)
    WHERE consumed_at IS NULL;
