ALTER TABLE sentinel_device_challenges
    ALTER COLUMN expected_fingerprint SET NOT NULL;

ALTER TABLE sentinel_audit_events
    ADD CONSTRAINT sentinel_audit_action_nonempty CHECK (length(action) BETWEEN 1 AND 128),
    ADD CONSTRAINT sentinel_audit_subject_nonempty CHECK (length(subject_id) BETWEEN 1 AND 256),
    ADD CONSTRAINT sentinel_audit_reason_size CHECK (reason IS NULL OR length(reason) <= 256);

ALTER TABLE sentinel_devices
    ADD CONSTRAINT sentinel_device_updated_not_before_registered CHECK (updated_at >= registered_at);
