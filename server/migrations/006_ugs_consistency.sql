-- PASS 1 UGS consistency boundary.
-- game_events and outbox_events share the INSERT transaction through this trigger.
CREATE OR REPLACE FUNCTION enqueue_game_event_outbox()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO outbox_events(
        id,
        aggregate_type,
        aggregate_id,
        event_type,
        payload_json,
        status,
        attempts,
        available_at
    ) VALUES (
        gen_random_uuid(),
        'game_event',
        NEW.id,
        NEW.type,
        jsonb_build_object(
            'event_id', NEW.event_id,
            'device_id', NEW.device_id,
            'identity_id', NEW.identity_id,
            'type', NEW.type,
            'schema_version', NEW.schema_version,
            'occurred_at', NEW.occurred_at,
            'sequence', NEW.sequence,
            'payload', NEW.payload_json,
            'request_id', NEW.request_id
        ),
        'PENDING',
        0,
        now()
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS game_events_enqueue_outbox ON game_events;
CREATE TRIGGER game_events_enqueue_outbox
AFTER INSERT ON game_events
FOR EACH ROW
EXECUTE FUNCTION enqueue_game_event_outbox();

-- Character projections are versioned snapshots. A late/stale event must never
-- overwrite a newer snapshot, regardless of which caller performs the upsert.
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
