-- Federated authentication state and provider-only account support.
-- Long-term provider credentials never enter repository state. Ephemeral state/nonces
-- are stored only as SHA-256 digests and are single-use.

ALTER TABLE users
    ALTER COLUMN email DROP NOT NULL;

CREATE TABLE IF NOT EXISTS federated_auth_challenges (
    challenge_hash CHAR(64) PRIMARY KEY,
    provider TEXT NOT NULL CHECK (provider IN ('google', 'telegram', 'vk')),
    purpose TEXT NOT NULL CHECK (purpose IN ('OIDC_NONCE', 'OAUTH_STATE')),
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS federated_auth_challenges_expiry_idx
    ON federated_auth_challenges(expires_at);

ALTER TABLE federated_auth_challenges ENABLE ROW LEVEL SECURITY;
ALTER TABLE federated_auth_challenges FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS federated_auth_challenges_service_policy ON federated_auth_challenges;
CREATE POLICY federated_auth_challenges_service_policy ON federated_auth_challenges
    USING (current_setting('app.service_role', true) = 'true')
    WITH CHECK (current_setting('app.service_role', true) = 'true');
