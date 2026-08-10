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

CREATE INDEX IF NOT EXISTS idx_sentinel_devices_state
    ON sentinel_devices (state);

CREATE INDEX IF NOT EXISTS idx_sentinel_devices_updated
    ON sentinel_devices (updated_at);
