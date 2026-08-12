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
    last_seen_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS device_bindings_identity_idx ON device_bindings(identity_id);

CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    version BIGINT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    UNIQUE(action, resource)
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY(role_id, permission_id)
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
CREATE INDEX IF NOT EXISTS entitlements_identity_game_idx ON entitlements(identity_id, game_id, status);

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id UUID NOT NULL REFERENCES identities(id) ON DELETE CASCADE,
    plan_code TEXT NOT NULL,
    status TEXT NOT NULL,
    currency CHAR(3) NOT NULL CHECK (currency IN ('EUR', 'USD', 'RUB')),
    started_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS billing_customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id UUID NOT NULL REFERENCES identities(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    provider_customer_id TEXT NOT NULL,
    status TEXT NOT NULL,
    UNIQUE(provider, provider_customer_id)
);

CREATE TABLE IF NOT EXISTS billing_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES billing_customers(id) ON DELETE CASCADE,
    provider_subscription_id TEXT NOT NULL UNIQUE,
    product_code TEXT NOT NULL,
    status TEXT NOT NULL,
    current_period_end TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id UUID NOT NULL REFERENCES identities(id) ON DELETE CASCADE,
    game_id TEXT NOT NULL,
    external_id TEXT NOT NULL,
    name TEXT NOT NULL,
    version BIGINT NOT NULL DEFAULT 0,
    state_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(identity_id, game_id, external_id)
);

CREATE TABLE IF NOT EXISTS knowledge_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace TEXT NOT NULL,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_json JSONB NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('fact', 'inference', 'recommendation')),
    confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    provenance_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    version BIGINT NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS knowledge_subject_idx ON knowledge_items(namespace, subject);

CREATE TABLE IF NOT EXISTS outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type TEXT NOT NULL,
    aggregate_id UUID,
    event_type TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING','PROCESSING','DONE','FAILED')) DEFAULT 'PENDING',
    attempts INTEGER NOT NULL DEFAULT 0,
    available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_until TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS outbox_claim_idx ON outbox_events(status, available_at);

CREATE TABLE IF NOT EXISTS worker_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING','PROCESSING','DONE','FAILED')) DEFAULT 'PENDING',
    attempts INTEGER NOT NULL DEFAULT 0,
    available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_until TIMESTAMPTZ,
    last_error TEXT
);
CREATE INDEX IF NOT EXISTS worker_claim_idx ON worker_jobs(status, available_at);

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
    request_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS audit_identity_time_idx ON audit_events(identity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS audit_resource_time_idx ON audit_events(resource, created_at DESC);

INSERT INTO games (id, name, family, platform, versioning) VALUES
('diablo-1-pc', 'Diablo', 'Diablo', 'windows', 'release'),
('diablo-2-pc', 'Diablo II', 'Diablo', 'windows', 'release'),
('diablo-2-resurrected-pc', 'Diablo II: Resurrected', 'Diablo', 'windows', 'release'),
('diablo-3-pc', 'Diablo III', 'Diablo', 'windows', 'season-patch'),
('diablo-4-pc', 'Diablo IV', 'Diablo', 'windows', 'season-patch'),
('diablo-immortal-android', 'Diablo Immortal', 'Diablo', 'android', 'server-client-patch')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, enabled = TRUE;
