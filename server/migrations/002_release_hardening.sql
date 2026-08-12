BEGIN;

ALTER TABLE sessions
  ADD COLUMN IF NOT EXISTS refresh_token_hash text,
  ADD COLUMN IF NOT EXISTS refresh_expires_at timestamptz,
  ADD COLUMN IF NOT EXISTS refresh_used_at timestamptz;
CREATE UNIQUE INDEX IF NOT EXISTS sessions_refresh_hash_uidx
  ON sessions(refresh_token_hash)
  WHERE refresh_token_hash IS NOT NULL;

ALTER TABLE game_events
  ADD COLUMN IF NOT EXISTS request_id text;
CREATE INDEX IF NOT EXISTS game_events_device_time_idx
  ON game_events(device_id, received_at DESC);

ALTER TABLE audit_events
  ADD COLUMN IF NOT EXISTS request_id text;
CREATE INDEX IF NOT EXISTS audit_request_idx
  ON audit_events(request_id);

CREATE TABLE IF NOT EXISTS security_failures (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subject text NOT NULL,
  source text NOT NULL,
  failed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS security_failures_subject_time_idx
  ON security_failures(subject, failed_at DESC);

CREATE TABLE IF NOT EXISTS dead_letter_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id text NOT NULL,
  error_code text NOT NULL,
  payload_json jsonb NOT NULL,
  attempts integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz
);
CREATE INDEX IF NOT EXISTS dead_letter_events_pending_idx
  ON dead_letter_events(resolved_at, created_at);

COMMIT;
