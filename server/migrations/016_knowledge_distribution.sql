-- Global reviewed distribution is not tenant data or action authority.
-- Serving connections can SELECT only, even if an over-broad table grant exists.
CREATE SEQUENCE knowledge_distribution_revision;
CREATE TABLE knowledge_packs (
    digest TEXT PRIMARY KEY CHECK (digest ~ '^[0-9a-f]{64}$'),
    raw BYTEA NOT NULL CHECK (octet_length(raw) BETWEEN 1 AND 262144),
    review_reference TEXT NOT NULL CHECK (length(review_reference) BETWEEN 1 AND 256),
    revoked_at_ms BIGINT CHECK (revoked_at_ms > 0),
    revocation_revision BIGINT NOT NULL DEFAULT 0 CHECK (revocation_revision >= 0)
);
CREATE TABLE knowledge_profile_bindings (
    profile_key TEXT PRIMARY KEY CHECK (profile_key ~ '^[0-9a-f]{64}$'),
    digest TEXT NOT NULL REFERENCES knowledge_packs(digest),
    revision BIGINT NOT NULL CHECK (revision > 0)
);

ALTER TABLE knowledge_packs ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_packs FORCE ROW LEVEL SECURITY;
ALTER TABLE knowledge_profile_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_profile_bindings FORCE ROW LEVEL SECURITY;
CREATE POLICY knowledge_packs_service_read ON knowledge_packs FOR SELECT
    USING (current_setting('app.service_role', true) = 'true');
CREATE POLICY knowledge_bindings_service_read ON knowledge_profile_bindings FOR SELECT
    USING (current_setting('app.service_role', true) = 'true');
-- Only the table owner/operator can publish. A transaction-local service flag
-- is deliberately insufficient for writes, deletion or revocation.
CREATE POLICY knowledge_packs_operator ON knowledge_packs FOR ALL
    USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid='knowledge_packs'::regclass)))
    WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid='knowledge_packs'::regclass)));
CREATE POLICY knowledge_bindings_operator ON knowledge_profile_bindings FOR ALL
    USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid='knowledge_profile_bindings'::regclass)))
    WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid='knowledge_profile_bindings'::regclass)));

CREATE FUNCTION protect_knowledge_pack() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' OR NEW.digest IS DISTINCT FROM OLD.digest
       OR NEW.raw IS DISTINCT FROM OLD.raw OR NEW.review_reference IS DISTINCT FROM OLD.review_reference
       OR OLD.revoked_at_ms IS NOT NULL OR NEW.revoked_at_ms IS NULL
       OR NEW.revocation_revision <= OLD.revocation_revision THEN
        RAISE EXCEPTION 'Immutable knowledge content and permanent revocation' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER knowledge_pack_immutable BEFORE UPDATE OR DELETE ON knowledge_packs
    FOR EACH ROW EXECUTE FUNCTION protect_knowledge_pack();

-- TRUNCATE ignores RLS and row triggers. Guard statements as well, including
-- CASCADE and excessive runtime table grants; no routine role may erase history.
CREATE FUNCTION protect_knowledge_truncate() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Knowledge distribution history cannot be truncated' USING ERRCODE='23514';
END $$;
CREATE TRIGGER knowledge_pack_no_truncate BEFORE TRUNCATE ON knowledge_packs
    FOR EACH STATEMENT EXECUTE FUNCTION protect_knowledge_truncate();
CREATE TRIGGER knowledge_binding_no_truncate BEFORE TRUNCATE ON knowledge_profile_bindings
    FOR EACH STATEMENT EXECUTE FUNCTION protect_knowledge_truncate();
