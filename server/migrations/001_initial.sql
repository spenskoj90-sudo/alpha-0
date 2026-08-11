BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  external_subject text NOT NULL UNIQUE,
  status text NOT NULL CHECK (status IN ('ACTIVE','SUSPENDED','DELETED')) DEFAULT 'ACTIVE',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  version bigint NOT NULL DEFAULT 1
);

CREATE TABLE permissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  action text NOT NULL,
  resource text NOT NULL,
  UNIQUE(action, resource)
);

CREATE TABLE user_roles (
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  PRIMARY KEY(user_id, role_id)
);

CREATE TABLE role_permissions (
  role_id uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permission_id uuid NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
  PRIMARY KEY(role_id, permission_id)
);

CREATE TABLE scopes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE
);

CREATE TABLE user_scopes (
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  scope_id uuid NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
  PRIMARY KEY(user_id, scope_id)
);

CREATE TABLE policies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  effect text NOT NULL CHECK (effect IN ('ALLOW','DENY')),
  action text NOT NULL,
  resource_pattern text NOT NULL,
  condition_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  version bigint NOT NULL DEFAULT 1,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE devices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  state text NOT NULL CHECK (state IN ('GENERATED','ACTIVE','ROTATING','REVOKED')),
  platform text NOT NULL CHECK (platform IN ('android')),
  public_key_der bytea NOT NULL,
  fingerprint_sha256 text NOT NULL UNIQUE,
  key_version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz,
  revoked_at timestamptz
);
CREATE INDEX devices_user_idx ON devices(user_id);

CREATE TABLE device_challenges (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id uuid NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  nonce_hash text NOT NULL UNIQUE,
  expires_at timestamptz NOT NULL,
  consumed_at timestamptz
);
CREATE INDEX device_challenges_device_idx ON device_challenges(device_id, expires_at);

CREATE TABLE sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  device_id uuid REFERENCES devices(id) ON DELETE SET NULL,
  session_hash text NOT NULL UNIQUE,
  scopes_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  issued_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz
);
CREATE INDEX sessions_user_idx ON sessions(user_id, expires_at);

CREATE TABLE entitlements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  product_code text NOT NULL,
  source text NOT NULL,
  status text NOT NULL CHECK (status IN ('ACTIVE','EXPIRED','REVOKED')),
  starts_at timestamptz NOT NULL,
  ends_at timestamptz,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX entitlements_lookup_idx ON entitlements(user_id, product_code, status);

CREATE TABLE billing_customers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider text NOT NULL,
  provider_customer_id text NOT NULL,
  status text NOT NULL,
  UNIQUE(provider, provider_customer_id)
);

CREATE TABLE billing_subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid NOT NULL REFERENCES billing_customers(id) ON DELETE CASCADE,
  provider_subscription_id text NOT NULL UNIQUE,
  product_code text NOT NULL,
  status text NOT NULL,
  current_period_end timestamptz
);

CREATE TABLE characters (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  game_id text NOT NULL,
  external_id text NOT NULL,
  name text NOT NULL,
  version bigint NOT NULL DEFAULT 0,
  state_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, game_id, external_id)
);

CREATE TABLE knowledge_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  namespace text NOT NULL,
  subject text NOT NULL,
  predicate text NOT NULL,
  object_json jsonb NOT NULL,
  kind text NOT NULL CHECK (kind IN ('fact','inference','recommendation')),
  confidence double precision NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  provenance_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  version bigint NOT NULL DEFAULT 1
);
CREATE INDEX knowledge_subject_idx ON knowledge_items(namespace, subject);

CREATE TABLE game_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id text NOT NULL UNIQUE,
  device_id uuid NOT NULL REFERENCES devices(id),
  user_id uuid NOT NULL REFERENCES users(id),
  type text NOT NULL,
  schema_version integer NOT NULL,
  occurred_at timestamptz NOT NULL,
  sequence bigint NOT NULL,
  payload_json jsonb NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(device_id, sequence)
);
CREATE INDEX game_events_user_time_idx ON game_events(user_id, received_at DESC);

CREATE TABLE outbox_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  aggregate_type text NOT NULL,
  aggregate_id uuid,
  event_type text NOT NULL,
  payload_json jsonb NOT NULL,
  status text NOT NULL CHECK (status IN ('PENDING','PROCESSING','DONE','FAILED')) DEFAULT 'PENDING',
  attempts integer NOT NULL DEFAULT 0,
  available_at timestamptz NOT NULL DEFAULT now(),
  locked_until timestamptz
);
CREATE INDEX outbox_claim_idx ON outbox_events(status, available_at);

CREATE TABLE audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  actor_device_id uuid REFERENCES devices(id) ON DELETE SET NULL,
  action text NOT NULL,
  resource_type text NOT NULL,
  resource_id text,
  decision text NOT NULL,
  reason_code text NOT NULL,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_actor_time_idx ON audit_events(actor_user_id, created_at DESC);
CREATE INDEX audit_resource_time_idx ON audit_events(resource_type, resource_id, created_at DESC);

CREATE TABLE idempotency_keys (
  key text PRIMARY KEY,
  actor_id text NOT NULL,
  request_hash text NOT NULL,
  response_json jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL
);

CREATE TABLE worker_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind text NOT NULL,
  payload_json jsonb NOT NULL,
  status text NOT NULL CHECK (status IN ('PENDING','PROCESSING','DONE','FAILED')) DEFAULT 'PENDING',
  attempts integer NOT NULL DEFAULT 0,
  available_at timestamptz NOT NULL DEFAULT now(),
  locked_until timestamptz,
  last_error text
);
CREATE INDEX worker_claim_idx ON worker_jobs(status, available_at);

-- Defense in depth. Application authorization is still mandatory.
ALTER TABLE characters ENABLE ROW LEVEL SECURITY;
ALTER TABLE entitlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;

COMMIT;
