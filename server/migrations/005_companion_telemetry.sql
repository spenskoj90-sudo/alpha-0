CREATE TABLE IF NOT EXISTS companion_telemetry_events (
    id UUID PRIMARY KEY,
    event_name TEXT NOT NULL CHECK (event_name LIKE 'companion.%'),
    observed_at TIMESTAMPTZ NOT NULL,
    attributes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    expires_at TIMESTAMPTZ NOT NULL,
    CHECK (expires_at > observed_at)
);

CREATE INDEX IF NOT EXISTS companion_telemetry_expiry_idx
    ON companion_telemetry_events(expires_at);
CREATE INDEX IF NOT EXISTS companion_telemetry_event_time_idx
    ON companion_telemetry_events(event_name, observed_at DESC);
