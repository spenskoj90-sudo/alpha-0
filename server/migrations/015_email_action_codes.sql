-- Account/purpose-bound short codes; preserve existing opaque-token rows.
ALTER TABLE auth_action_tokens ADD COLUMN IF NOT EXISTS code_hash TEXT;
ALTER TABLE auth_action_tokens ADD COLUMN IF NOT EXISTS failed_attempts SMALLINT NOT NULL DEFAULT 0
    CHECK (failed_attempts BETWEEN 0 AND 5);
CREATE INDEX IF NOT EXISTS auth_action_codes_request_budget_idx
    ON auth_action_tokens(identity_id, purpose, created_at) WHERE code_hash IS NOT NULL;
