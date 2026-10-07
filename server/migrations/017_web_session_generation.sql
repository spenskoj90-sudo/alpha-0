-- Browser session generations serialize credential mutations across Web workers.
-- The opaque family token is hashed before persistence and is revocation-only.
CREATE TABLE web_session_families (
    family_hash TEXT PRIMARY KEY,
    latest_operation BIGINT NOT NULL DEFAULT 0 CHECK (latest_operation >= 0),
    active_generation BIGINT NOT NULL DEFAULT 0 CHECK (active_generation >= 0),
    cancelled_operations BIGINT[] NOT NULL DEFAULT ARRAY[]::BIGINT[],
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (active_generation <= latest_operation)
);

ALTER TABLE sessions ADD COLUMN web_session_family_hash TEXT
    REFERENCES web_session_families(family_hash) ON DELETE RESTRICT;
ALTER TABLE sessions ADD COLUMN web_session_generation BIGINT
    CHECK (web_session_generation > 0);
ALTER TABLE sessions ADD COLUMN refresh_lineage_hash TEXT;
ALTER TABLE sessions ADD CONSTRAINT sessions_web_generation_pair CHECK (
    (web_session_family_hash IS NULL) = (web_session_generation IS NULL)
);
CREATE INDEX sessions_web_generation_idx
    ON sessions(web_session_family_hash, web_session_generation)
    WHERE web_session_family_hash IS NOT NULL;
CREATE INDEX sessions_refresh_lineage_idx
    ON sessions(refresh_lineage_hash)
    WHERE refresh_lineage_hash IS NOT NULL;

ALTER TABLE web_session_families ENABLE ROW LEVEL SECURITY;
ALTER TABLE web_session_families FORCE ROW LEVEL SECURITY;
CREATE POLICY web_session_families_service_policy ON web_session_families
    USING (current_setting('app.service_role', true) = 'true')
    WITH CHECK (current_setting('app.service_role', true) = 'true');
