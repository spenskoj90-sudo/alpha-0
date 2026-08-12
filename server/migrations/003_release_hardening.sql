BEGIN;

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

ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS request_id TEXT;
CREATE INDEX IF NOT EXISTS audit_request_idx ON audit_events(request_id);

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

COMMIT;
