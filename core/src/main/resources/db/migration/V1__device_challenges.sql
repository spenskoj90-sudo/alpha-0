CREATE TABLE IF NOT EXISTS sentinel_device_challenges (
    challenge_id VARCHAR(256) PRIMARY KEY,
    nonce BYTEA NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    expected_fingerprint CHAR(64),
    consumed_at TIMESTAMPTZ,
    CONSTRAINT sentinel_device_challenges_nonce_size
        CHECK (octet_length(nonce) BETWEEN 32 AND 64),
    CONSTRAINT sentinel_device_challenges_fingerprint_format
        CHECK (expected_fingerprint IS NULL OR expected_fingerprint ~ '^[0-9a-f]{64}$'),
    CONSTRAINT sentinel_device_challenges_consumed_after_issue
        CHECK (consumed_at IS NULL OR consumed_at >= (expires_at - INTERVAL '30 days'))
);

CREATE INDEX IF NOT EXISTS idx_sentinel_device_challenges_active_expiry
    ON sentinel_device_challenges (expires_at)
    WHERE consumed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_sentinel_device_challenges_consumed_at
    ON sentinel_device_challenges (consumed_at)
    WHERE consumed_at IS NOT NULL;

COMMENT ON TABLE sentinel_device_challenges IS
    'Single-use server-issued authentication challenges. Consumed state is authoritative for replay prevention.';
COMMENT ON COLUMN sentinel_device_challenges.nonce IS
    'Cryptographically random challenge nonce; verifier requires 32-64 bytes.';
COMMENT ON COLUMN sentinel_device_challenges.expected_fingerprint IS
    'Optional SHA-256 lowercase hex fingerprint of the device public key approved for this challenge.';
