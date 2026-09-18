-- Account-security lifecycle: verification/reset tokens and federated identity bindings.
-- Raw recovery/verification credentials and provider tokens are never persisted.

ALTER TABLE users
    ALTER COLUMN password_hash DROP NOT NULL;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS auth_action_tokens (
    token_hash CHAR(64) PRIMARY KEY,
    identity_id UUID NOT NULL REFERENCES identities(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL CHECK (purpose IN ('EMAIL_VERIFY', 'PASSWORD_RESET')),
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS auth_action_tokens_identity_purpose_idx
    ON auth_action_tokens(identity_id, purpose, created_at DESC);
CREATE INDEX IF NOT EXISTS auth_action_tokens_expiry_idx
    ON auth_action_tokens(expires_at);

CREATE TABLE IF NOT EXISTS external_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id UUID NOT NULL REFERENCES identities(id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('google', 'vk', 'telegram')),
    provider_subject TEXT NOT NULL,
    email_at_link_time TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(provider, provider_subject),
    UNIQUE(identity_id, provider)
);

DO $$
DECLARE
    table_name text;
    policy_name text;
    protected_tables text[] := ARRAY['auth_action_tokens', 'external_identities'];
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
