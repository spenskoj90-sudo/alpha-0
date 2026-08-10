DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'sentinel_device_recovery_codes_device_fingerprint_fkey'
    ) THEN
        ALTER TABLE sentinel_device_recovery_codes
            DROP CONSTRAINT sentinel_device_recovery_codes_device_fingerprint_fkey;
    END IF;
END $$;

ALTER TABLE sentinel_device_recovery_codes
    ADD CONSTRAINT sentinel_device_recovery_codes_device_fingerprint_fkey
    FOREIGN KEY (device_fingerprint)
    REFERENCES sentinel_devices(fingerprint)
    ON UPDATE CASCADE
    ON DELETE CASCADE;
