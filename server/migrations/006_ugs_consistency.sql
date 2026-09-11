CREATE TABLE IF NOT EXISTS game_event_outbox (
    id UUID PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE REFERENCES game_events(event_id) ON DELETE CASCADE,
    device_id UUID NOT NULL,
    identity_id UUID NOT NULL,
    kind TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    sequence BIGINT NOT NULL CHECK (sequence >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS game_event_outbox_sequence_idx
    ON game_event_outbox(device_id, sequence);

CREATE INDEX IF NOT EXISTS game_event_outbox_created_idx
    ON game_event_outbox(created_at);

CREATE OR REPLACE FUNCTION enqueue_game_event_outbox()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO game_event_outbox(
        id, event_id, device_id, identity_id, kind, payload_json, occurred_at, sequence
    ) VALUES (
        gen_random_uuid(), NEW.event_id, NEW.device_id, NEW.identity_id,
        'game.event',
        jsonb_build_object(
            'event_id', NEW.event_id,
            'type', NEW.type,
            'schema_version', NEW.schema_version,
            'payload', NEW.payload_json,
            'request_id', NEW.request_id
        ),
        NEW.occurred_at, NEW.sequence
    )
    ON CONFLICT (event_id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS game_events_enqueue_outbox ON game_events;
CREATE TRIGGER game_events_enqueue_outbox
AFTER INSERT ON game_events
FOR EACH ROW
EXECUTE FUNCTION enqueue_game_event_outbox();

CREATE OR REPLACE FUNCTION guard_character_projection_version()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.version < OLD.version THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS characters_monotonic_version ON characters;
CREATE TRIGGER characters_monotonic_version
BEFORE UPDATE ON characters
FOR EACH ROW
EXECUTE FUNCTION guard_character_projection_version();
