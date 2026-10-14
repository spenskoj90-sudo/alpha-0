-- Device registration alone must never elevate account bearer authority.
-- Existing sessions receive FALSE and require fresh signed device proof.
-- Sessions minted by proven internal flows set TRUE; refresh retains the bit.
ALTER TABLE sessions
    ADD COLUMN device_proof_verified BOOLEAN NOT NULL DEFAULT FALSE;

-- No migration-time blanket upgrade: historic /bind-issued tokens may have
-- attached a device_id without proving possession of its private key.
COMMENT ON COLUMN sessions.device_proof_verified IS
    'True only for server-issued sessions from proven device paths; never inferred from device_id.';
