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
CREATE INDEX IF NOT EXISTS audit_request_idx ON audit_events(request_id);

CREATE TABLE IF NOT EXISTS wow_patches (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    family TEXT NOT NULL CHECK (family IN ('retail', 'classic')),
    protocol_generation TEXT NOT NULL,
    supported BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS wow_realms (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    realm_type TEXT NOT NULL CHECK (realm_type IN ('official', 'private')),
    patch_id TEXT NOT NULL REFERENCES wow_patches(id),
    source TEXT NOT NULL,
    monitoring_profile TEXT NOT NULL,
    client_integration TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS wow_realm_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    realm_id TEXT NOT NULL REFERENCES wow_realms(id) ON DELETE CASCADE,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL CHECK (status IN ('ONLINE', 'DEGRADED', 'OFFLINE', 'UNKNOWN')),
    latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    player_count INTEGER CHECK (player_count IS NULL OR player_count >= 0),
    endpoint_host TEXT,
    endpoint_port INTEGER CHECK (endpoint_port IS NULL OR endpoint_port BETWEEN 1 AND 65535),
    client_build TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_wow_observations_realm_time ON wow_realm_observations(realm_id, observed_at DESC);

CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  identity_id UUID NOT NULL REFERENCES identities(id) ON DELETE CASCADE,
  device_id UUID REFERENCES device_bindings(id) ON DELETE SET NULL,
  session_hash TEXT NOT NULL UNIQUE,
  scopes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  refresh_token_hash TEXT UNIQUE,
  refresh_expires_at TIMESTAMPTZ,
  refresh_used_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS sessions_identity_expiry_idx ON sessions(identity_id, expires_at);
CREATE INDEX IF NOT EXISTS sessions_refresh_expiry_idx ON sessions(refresh_token_hash, refresh_expires_at);

CREATE TABLE IF NOT EXISTS device_challenges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID NOT NULL REFERENCES device_bindings(id) ON DELETE CASCADE,
  nonce_hash TEXT NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS device_challenges_device_expiry_idx ON device_challenges(device_id, expires_at);

CREATE TABLE IF NOT EXISTS game_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id TEXT NOT NULL UNIQUE,
  device_id UUID NOT NULL REFERENCES device_bindings(id) ON DELETE RESTRICT,
  identity_id UUID NOT NULL REFERENCES identities(id) ON DELETE RESTRICT,
  type TEXT NOT NULL,
  schema_version INTEGER NOT NULL CHECK (schema_version > 0),
  occurred_at TIMESTAMPTZ NOT NULL,
  sequence BIGINT NOT NULL CHECK (sequence >= 0),
  payload_json JSONB NOT NULL,
  request_id TEXT,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(device_id, sequence)
);
CREATE INDEX IF NOT EXISTS game_events_identity_time_idx ON game_events(identity_id, received_at DESC);
CREATE INDEX IF NOT EXISTS game_events_device_time_idx ON game_events(device_id, received_at DESC);

CREATE TABLE IF NOT EXISTS idempotency_keys (
  key TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  response_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  PRIMARY KEY(key, actor_id)
);
CREATE INDEX IF NOT EXISTS idempotency_expiry_idx ON idempotency_keys(expires_at);

CREATE TABLE IF NOT EXISTS proof_request_ids (
  device_id UUID NOT NULL REFERENCES device_bindings(id) ON DELETE CASCADE,
  request_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(device_id, request_id)
);

CREATE TABLE IF NOT EXISTS security_failures (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject TEXT NOT NULL,
  source TEXT NOT NULL,
  failed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS security_failures_subject_time_idx ON security_failures(subject, failed_at DESC);

INSERT INTO games (id, name, family, platform, versioning) VALUES
('diablo-1-pc', 'Diablo', 'Diablo', 'windows', 'release'),
('diablo-2-pc', 'Diablo II', 'Diablo', 'windows', 'release'),
('diablo-2-resurrected-pc', 'Diablo II: Resurrected', 'Diablo', 'windows', 'release'),
('diablo-3-pc', 'Diablo III', 'Diablo', 'windows', 'season-patch'),
('diablo-4-pc', 'Diablo IV', 'Diablo', 'windows', 'season-patch'),
('diablo-immortal-android', 'Diablo Immortal', 'Diablo', 'android', 'server-client-patch')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, enabled = TRUE;

INSERT INTO wow_patches (id, label, family, protocol_generation) VALUES
('retail-12.0.5', 'Retail / Midnight 12.0.5', 'retail', 'retail-12'),
('vanilla-1.12', 'Vanilla 1.12', 'classic', 'classic-1'),
('tbc-2.4.3', 'The Burning Crusade 2.4.3', 'classic', 'classic-2'),
('wotlk-3.3.5a', 'Wrath of the Lich King 3.3.5a', 'classic', 'classic-3'),
('cata-4.3.4', 'Cataclysm 4.3.4', 'classic', 'classic-4'),
('mop-5.4.8', 'Mists of Pandaria 5.4.8', 'classic', 'classic-5'),
('wod-6.2.4', 'Warlords of Draenor 6.2.4', 'classic', 'classic-6'),
('legion-7.3.5', 'Legion 7.3.5', 'classic', 'classic-7'),
('bfa-8.3.7', 'Battle for Azeroth 8.3.7', 'classic', 'classic-8'),
('shadowlands-9.2.7', 'Shadowlands 9.2.7', 'classic', 'classic-9'),
('dragonflight-10.2.7', 'Dragonflight 10.2.7', 'classic', 'classic-10')
ON CONFLICT (id) DO UPDATE SET label = EXCLUDED.label, supported = TRUE;

INSERT INTO wow_realms (id, name, realm_type, patch_id, source, monitoring_profile, client_integration) VALUES
('mmotop-uwow', 'Uwow', 'private', 'legion-7.3.5', 'MMOTOP', 'legion-private', 'launcher-plus-addon'),
('mmotop-skyblood', 'SkyBlood', 'private', 'legion-7.3.5', 'MMOTOP', 'legion-private', 'launcher-plus-addon'),
('mmotop-wow-prime', 'WoW-Prime', 'private', 'legion-7.3.5', 'MMOTOP', 'custom-launcher', 'launcher-plus-addon'),
('mmotop-neverest', 'Neverest', 'private', 'wotlk-3.3.5a', 'MMOTOP', 'wotlk-private', 'launcher-plus-addon'),
('mmotop-epicwow', 'EpicWoW', 'private', 'legion-7.3.5', 'MMOTOP', 'legion-private', 'launcher-plus-addon'),
('mmotop-1001wow', '1001WOW', 'private', 'wotlk-3.3.5a', 'MMOTOP', 'wotlk-private', 'launcher-plus-addon'),
('mmotop-northwind', 'Northwind', 'private', 'vanilla-1.12', 'MMOTOP', 'vanilla-private', 'launcher-plus-addon'),
('mmotop-poligon7', 'Poligon7', 'private', 'vanilla-1.12', 'MMOTOP', 'vanilla-private', 'launcher-plus-addon'),
('mmotop-nozdor', 'Nozdor', 'private', 'wotlk-3.3.5a', 'MMOTOP', 'wotlk-private', 'launcher-plus-addon'),
('mmotop-turbo-wow', 'Turbo-WoW', 'private', 'dragonflight-10.2.7', 'MMOTOP', 'dragonflight-private', 'launcher-plus-addon')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, patch_id = EXCLUDED.patch_id, enabled = TRUE;
