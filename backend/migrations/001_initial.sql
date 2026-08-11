BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE device_status AS ENUM ('ACTIVE','ROTATING','REVOKED');
CREATE TYPE session_status AS ENUM ('ACTIVE','REVOKED','EXPIRED');
CREATE TYPE knowledge_kind AS ENUM ('FACT','INFERENCE','RECOMMENDATION');
CREATE TYPE outbox_status AS ENUM ('PENDING','PROCESSING','DONE','DEAD');

CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','DISABLED')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE
);

CREATE TABLE permissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  action text NOT NULL UNIQUE
);

CREATE TABLE role_permissions (
  role_id uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permission_id uuid NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
  PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE user_roles (
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, role_id)
);

CREATE TABLE scopes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scope_key text NOT NULL UNIQUE,
  owner_user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  scope_type text NOT NULL CHECK (scope_type IN ('SYSTEM','USER','CHARACTER','DEVICE'))
);

CREATE TABLE policies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  action text NOT NULL REFERENCES permissions(action),
  effect text NOT NULL CHECK (effect IN ('ALLOW','DENY')),
  expression jsonb NOT NULL DEFAULT '{}'::jsonb,
  priority integer NOT NULL DEFAULT 100,
  enabled boolean NOT NULL DEFAULT true
);
CREATE INDEX policies_action_priority_idx ON policies(action, priority);

CREATE TABLE devices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  platform text NOT NULL,
  fingerprint_sha256 char(64) NOT NULL UNIQUE,
  status device_status NOT NULL DEFAULT 'ACTIVE',
  created_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz
);
CREATE INDEX devices_user_status_idx ON devices(user_id, status);

CREATE TABLE device_keys (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id uuid NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  version integer NOT NULL,
  public_key_spki bytea NOT NULL,
  fingerprint_sha256 char(64) NOT NULL,
  status device_status NOT NULL DEFAULT 'ACTIVE',
  created_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz,
  UNIQUE(device_id, version),
  UNIQUE(device_id, fingerprint_sha256)
);
CREATE INDEX device_keys_device_status_idx ON device_keys(device_id, status);

CREATE TABLE sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  device_id uuid NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  token_hash char(64) NOT NULL UNIQUE,
  status session_status NOT NULL DEFAULT 'ACTIVE',
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz
);
CREATE INDEX sessions_device_status_idx ON sessions(device_id, status);

CREATE TABLE session_nonces (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  nonce text NOT NULL UNIQUE,
  request_hash bytea NOT NULL,
  expires_at timestamptz NOT NULL,
  consumed_at timestamptz
);
CREATE INDEX session_nonces_expiry_idx ON session_nonces(expires_at);

CREATE TABLE entitlements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  entitlement_key text NOT NULL,
  source text NOT NULL,
  status text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','REVOKED','EXPIRED')),
  starts_at timestamptz NOT NULL DEFAULT now(),
  ends_at timestamptz
);
CREATE INDEX entitlements_user_key_idx ON entitlements(user_id, entitlement_key, status);

CREATE TABLE subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider text NOT NULL,
  provider_subscription_id text NOT NULL,
  status text NOT NULL,
  current_period_end timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(provider, provider_subscription_id)
);

CREATE TABLE billing_ledger (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider text NOT NULL,
  provider_event_id text NOT NULL UNIQUE,
  event_type text NOT NULL,
  payload_hash char(64) NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE characters (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  game_id text NOT NULL,
  name text NOT NULL,
  state jsonb NOT NULL DEFAULT '{}'::jsonb,
  version bigint NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, game_id, name)
);
CREATE INDEX characters_user_game_idx ON characters(user_id, game_id);

CREATE TABLE character_versions (
  character_id uuid NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  version bigint NOT NULL,
  state jsonb NOT NULL,
  changed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(character_id, version)
);

CREATE TABLE source_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type text NOT NULL,
  source_uri text,
  content_hash char(64) NOT NULL UNIQUE,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE knowledge_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  character_id uuid REFERENCES characters(id) ON DELETE CASCADE,
  kind knowledge_kind NOT NULL,
  statement text NOT NULL,
  confidence numeric(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  source_id uuid REFERENCES source_records(id),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz
);
CREATE INDEX knowledge_character_kind_idx ON knowledge_items(character_id, kind, confidence DESC);

CREATE TABLE events (
  event_id uuid PRIMARY KEY,
  actor_user_id uuid REFERENCES users(id),
  device_id uuid REFERENCES devices(id),
  event_type text NOT NULL,
  aggregate_type text NOT NULL,
  aggregate_id uuid NOT NULL,
  aggregate_version bigint,
  occurred_at timestamptz NOT NULL,
  payload jsonb NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX events_aggregate_idx ON events(aggregate_type, aggregate_id, aggregate_version);
CREATE INDEX events_received_idx ON events(received_at);

CREATE TABLE outbox_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id uuid NOT NULL UNIQUE REFERENCES events(event_id) ON DELETE CASCADE,
  topic text NOT NULL,
  payload jsonb NOT NULL,
  status outbox_status NOT NULL DEFAULT 'PENDING',
  attempts integer NOT NULL DEFAULT 0,
  next_attempt_at timestamptz NOT NULL DEFAULT now(),
  locked_at timestamptz,
  processed_at timestamptz,
  last_error text
);
CREATE INDEX outbox_pending_idx ON outbox_events(status, next_attempt_at);

CREATE TABLE consumer_checkpoints (
  consumer text NOT NULL,
  event_id uuid NOT NULL REFERENCES events(event_id),
  processed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(consumer, event_id)
);

CREATE TABLE dead_letters (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  outbox_id uuid REFERENCES outbox_events(id),
  consumer text NOT NULL,
  error text NOT NULL,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz
);
CREATE INDEX dead_letters_open_idx ON dead_letters(consumer, created_at) WHERE resolved_at IS NULL;

CREATE TABLE audit_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id uuid REFERENCES users(id),
  device_id uuid REFERENCES devices(id),
  action text NOT NULL,
  resource text NOT NULL,
  decision text NOT NULL CHECK (decision IN ('ALLOW','DENY')),
  request_id uuid,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_actor_time_idx ON audit_log(actor_user_id, created_at DESC);
CREATE INDEX audit_request_idx ON audit_log(request_id);

CREATE TABLE idempotency_keys (
  actor_user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  key text NOT NULL,
  request_hash char(64) NOT NULL,
  response_code integer,
  response_body jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(actor_user_id, key)
);

CREATE TABLE telemetry_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id uuid REFERENCES users(id),
  device_id uuid REFERENCES devices(id),
  event_name text NOT NULL,
  properties jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX telemetry_name_time_idx ON telemetry_events(event_name, created_at DESC);

-- RLS: enable for user-owned tables. Runtime roles receive explicit policies later.
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE entitlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE characters ENABLE ROW LEVEL SECURITY;
ALTER TABLE character_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE telemetry_events ENABLE ROW LEVEL SECURITY;

-- The application role must set `app.user_id` in a transaction before accessing user data.
CREATE OR REPLACE FUNCTION sentinel_current_user_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('app.user_id', true), '')::uuid
$$;

CREATE POLICY devices_user_policy ON devices
  USING (user_id = sentinel_current_user_id())
  WITH CHECK (user_id = sentinel_current_user_id());
CREATE POLICY sessions_user_policy ON sessions
  USING (user_id = sentinel_current_user_id())
  WITH CHECK (user_id = sentinel_current_user_id());
CREATE POLICY entitlements_user_policy ON entitlements
  USING (user_id = sentinel_current_user_id())
  WITH CHECK (user_id = sentinel_current_user_id());
CREATE POLICY subscriptions_user_policy ON subscriptions
  USING (user_id = sentinel_current_user_id())
  WITH CHECK (user_id = sentinel_current_user_id());
CREATE POLICY characters_user_policy ON characters
  USING (user_id = sentinel_current_user_id())
  WITH CHECK (user_id = sentinel_current_user_id());
CREATE POLICY character_versions_user_policy ON character_versions
  USING (EXISTS (SELECT 1 FROM characters c WHERE c.id = character_versions.character_id AND c.user_id = sentinel_current_user_id()))
  WITH CHECK (EXISTS (SELECT 1 FROM characters c WHERE c.id = character_versions.character_id AND c.user_id = sentinel_current_user_id()));
CREATE POLICY knowledge_user_policy ON knowledge_items
  USING (user_id = sentinel_current_user_id() OR EXISTS (SELECT 1 FROM characters c WHERE c.id = knowledge_items.character_id AND c.user_id = sentinel_current_user_id()))
  WITH CHECK (user_id = sentinel_current_user_id());
CREATE POLICY events_user_policy ON events
  USING (actor_user_id = sentinel_current_user_id())
  WITH CHECK (actor_user_id = sentinel_current_user_id());
CREATE POLICY audit_user_policy ON audit_log
  USING (actor_user_id = sentinel_current_user_id());
CREATE POLICY telemetry_user_policy ON telemetry_events
  USING (actor_user_id = sentinel_current_user_id())
  WITH CHECK (actor_user_id = sentinel_current_user_id());

INSERT INTO permissions(action) VALUES
 ('character.read'),('character.write'),('device.read'),('device.rotate'),('device.revoke'),
 ('knowledge.read'),('event.ingest'),('audit.read'),('billing.read')
ON CONFLICT DO NOTHING;

COMMIT;
