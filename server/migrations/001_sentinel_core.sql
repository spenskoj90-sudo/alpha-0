CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_handle TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS device_bindings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id UUID NOT NULL REFERENCES identities(id) ON DELETE CASCADE,
    fingerprint_sha256 CHAR(64) NOT NULL UNIQUE,
    public_key_der_b64 TEXT NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('android', 'windows')),
    state TEXT NOT NULL CHECK (state IN ('ACTIVE', 'REVOKED', 'SUSPENDED')) DEFAULT 'ACTIVE',
    key_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS scopes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_id TEXT NOT NULL,
    ruleset_version TEXT NOT NULL,
    resource_pattern TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(scope_id, ruleset_version)
);

CREATE TABLE IF NOT EXISTS games (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    family TEXT NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('windows', 'android')),
    versioning TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS entitlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id UUID NOT NULL REFERENCES identities(id) ON DELETE CASCADE,
    game_id TEXT NOT NULL REFERENCES games(id),
    source TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'EXPIRED', 'SUSPENDED')),
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (valid_until >= valid_from)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id UUID NOT NULL REFERENCES identities(id) ON DELETE CASCADE,
    plan_code TEXT NOT NULL,
    status TEXT NOT NULL,
    currency CHAR(3) NOT NULL CHECK (currency IN ('EUR', 'USD', 'RUB')),
    started_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id UUID REFERENCES identities(id) ON DELETE SET NULL,
    device_id UUID REFERENCES device_bindings(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('ALLOW', 'DENY')),
    reason_code TEXT NOT NULL,
    policy_version TEXT NOT NULL DEFAULT 'v1',
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_entitlements_identity_game ON entitlements(identity_id, game_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_identity_time ON audit_events(identity_id, created_at DESC);

INSERT INTO games (id, name, family, platform, versioning) VALUES
('diablo-1-pc', 'Diablo', 'Diablo', 'windows', 'release'),
('diablo-2-pc', 'Diablo II', 'Diablo', 'windows', 'release'),
('diablo-2-resurrected-pc', 'Diablo II: Resurrected', 'Diablo', 'windows', 'release'),
('diablo-3-pc', 'Diablo III', 'Diablo', 'windows', 'season-patch'),
('diablo-4-pc', 'Diablo IV', 'Diablo', 'windows', 'season-patch'),
('diablo-immortal-android', 'Diablo Immortal', 'Diablo', 'android', 'server-client-patch')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, enabled = TRUE;
