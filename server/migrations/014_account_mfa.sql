-- User account MFA: encrypted TOTP seed, one-time recovery codes and hashed login challenges.
-- The application encryption key is environment-injected; raw recovery codes/challenges are never persisted.

CREATE TABLE IF NOT EXISTS account_mfa_totp (
    identity_id UUID PRIMARY KEY REFERENCES identities(id) ON DELETE CASCADE,
    secret_ciphertext TEXT NOT NULL,
    enabled_at TIMESTAMPTZ,
    last_totp_counter BIGINT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS account_mfa_recovery_codes (
    identity_id UUID NOT NULL REFERENCES identities(id) ON DELETE CASCADE,
    code_hash CHAR(64) NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(identity_id, code_hash)
);

CREATE TABLE IF NOT EXISTS account_mfa_login_challenges (
    challenge_hash CHAR(64) PRIMARY KEY,
    identity_id UUID NOT NULL REFERENCES identities(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS account_mfa_login_challenges_identity_expiry_idx
    ON account_mfa_login_challenges(identity_id, expires_at);

DO $$
DECLARE
    table_name text;
    policy_name text;
    protected_tables text[] := ARRAY[
        'account_mfa_totp',
        'account_mfa_recovery_codes',
        'account_mfa_login_challenges'
    ];
BEGIN
    FOREACH table_name IN ARRAY protected_tables LOOP
        policy_name := table_name || '_service_policy';
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', policy_name, table_name);
        EXECUTE format(
            'CREATE POLICY %I ON %I USING (current_setting(''app.service_role'', true) = ''true'') WITH CHECK (current_setting(''app.service_role'', true) = ''true'')',
            policy_name,
            table_name
        );
    END LOOP;
END $$;
