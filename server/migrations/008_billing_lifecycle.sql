-- Provider-neutral subscription lifecycle. Provider credentials stay outside
-- the database; webhook payloads are retained only for replay/audit evidence.
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS provider_subscription_id TEXT NOT NULL DEFAULT '';
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
CREATE UNIQUE INDEX IF NOT EXISTS subscriptions_provider_external_idx
    ON subscriptions(provider, provider_subscription_id)
    WHERE provider_subscription_id <> '';

CREATE TABLE IF NOT EXISTS billing_webhook_events (
    event_id TEXT PRIMARY KEY,
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE','PAST_DUE','CANCELED','EXPIRED')),
    occurred_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS billing_webhook_subscription_idx
    ON billing_webhook_events(subscription_id, occurred_at DESC);

ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions FORCE ROW LEVEL SECURITY;
ALTER TABLE billing_webhook_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_webhook_events FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS subscriptions_service_policy ON subscriptions;
CREATE POLICY subscriptions_service_policy ON subscriptions
    USING (current_setting('app.service_role', true) = 'true')
    WITH CHECK (current_setting('app.service_role', true) = 'true');
DROP POLICY IF EXISTS billing_webhook_events_service_policy ON billing_webhook_events;
CREATE POLICY billing_webhook_events_service_policy ON billing_webhook_events
    USING (current_setting('app.service_role', true) = 'true')
    WITH CHECK (current_setting('app.service_role', true) = 'true');
