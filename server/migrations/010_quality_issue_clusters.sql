CREATE TABLE IF NOT EXISTS quality_issue_clusters (
    id uuid PRIMARY KEY,
    fingerprint char(64) NOT NULL UNIQUE,
    signature_kind varchar(16) NOT NULL,
    category varchar(32) NOT NULL,
    canonical_title varchar(160) NOT NULL,
    severity varchar(16) NOT NULL,
    severity_locked boolean NOT NULL DEFAULT false,
    status varchar(32) NOT NULL DEFAULT 'RECEIVED',
    priority_score integer NOT NULL DEFAULT 0,
    occurrence_count integer NOT NULL DEFAULT 0,
    affected_user_count integer NOT NULL DEFAULT 0,
    affected_device_count integer NOT NULL DEFAULT 0,
    affected_version_count integer NOT NULL DEFAULT 0,
    first_seen_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    last_app_version varchar(64) NULL,
    last_source_sha char(40) NULL,
    merged_into_id uuid NULL REFERENCES quality_issue_clusters(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT quality_issue_clusters_signature_kind_ck CHECK (signature_kind IN ('DIAGNOSTIC','TEXT')),
    CONSTRAINT quality_issue_clusters_category_ck CHECK (
        category IN ('DESIGN','FUNCTIONALITY','GAME_INTEGRATION','PERFORMANCE','ACCESSIBILITY','VOICE_AUDIO','SECURITY_PRIVACY','OTHER')
    ),
    CONSTRAINT quality_issue_clusters_severity_ck CHECK (severity IN ('CRITICAL','HIGH','MEDIUM','LOW')),
    CONSTRAINT quality_issue_clusters_status_ck CHECK (status IN ('RECEIVED','TRIAGED','IN_PROGRESS','RESOLVED','WONT_FIX')),
    CONSTRAINT quality_issue_clusters_priority_ck CHECK (priority_score BETWEEN 0 AND 100),
    CONSTRAINT quality_issue_clusters_counts_ck CHECK (
        occurrence_count >= 0 AND affected_user_count >= 0 AND affected_device_count >= 0 AND affected_version_count >= 0
    ),
    CONSTRAINT quality_issue_clusters_fingerprint_ck CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
    CONSTRAINT quality_issue_clusters_source_sha_ck CHECK (last_source_sha IS NULL OR last_source_sha ~ '^[0-9a-f]{40}$'),
    CONSTRAINT quality_issue_clusters_not_self_merged_ck CHECK (merged_into_id IS NULL OR merged_into_id <> id)
);

CREATE TABLE IF NOT EXISTS quality_cluster_users (
    cluster_id uuid NOT NULL REFERENCES quality_issue_clusters(id) ON DELETE CASCADE,
    user_id text NOT NULL,
    first_seen_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    PRIMARY KEY (cluster_id, user_id)
);

CREATE TABLE IF NOT EXISTS quality_cluster_devices (
    cluster_id uuid NOT NULL REFERENCES quality_issue_clusters(id) ON DELETE CASCADE,
    device_id uuid NOT NULL,
    first_seen_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    PRIMARY KEY (cluster_id, device_id)
);

CREATE TABLE IF NOT EXISTS quality_cluster_versions (
    cluster_id uuid NOT NULL REFERENCES quality_issue_clusters(id) ON DELETE CASCADE,
    app_version varchar(64) NOT NULL,
    first_seen_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    PRIMARY KEY (cluster_id, app_version)
);

ALTER TABLE quality_reports
    ADD COLUMN IF NOT EXISTS cluster_id uuid NULL REFERENCES quality_issue_clusters(id),
    ADD COLUMN IF NOT EXISTS issue_fingerprint char(64) NULL,
    ADD COLUMN IF NOT EXISTS inferred_severity varchar(16) NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'quality_reports_issue_fingerprint_ck'
    ) THEN
        ALTER TABLE quality_reports ADD CONSTRAINT quality_reports_issue_fingerprint_ck
            CHECK (issue_fingerprint IS NULL OR issue_fingerprint ~ '^[0-9a-f]{64}$');
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'quality_reports_inferred_severity_ck'
    ) THEN
        ALTER TABLE quality_reports ADD CONSTRAINT quality_reports_inferred_severity_ck
            CHECK (inferred_severity IS NULL OR inferred_severity IN ('CRITICAL','HIGH','MEDIUM','LOW'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS quality_issue_clusters_priority_idx
    ON quality_issue_clusters (priority_score DESC, last_seen_at DESC)
    WHERE merged_into_id IS NULL;

CREATE INDEX IF NOT EXISTS quality_issue_clusters_status_priority_idx
    ON quality_issue_clusters (status, priority_score DESC, last_seen_at DESC)
    WHERE merged_into_id IS NULL;

CREATE INDEX IF NOT EXISTS quality_issue_clusters_category_priority_idx
    ON quality_issue_clusters (category, priority_score DESC, last_seen_at DESC)
    WHERE merged_into_id IS NULL;

CREATE INDEX IF NOT EXISTS quality_reports_cluster_created_idx
    ON quality_reports (cluster_id, created_at DESC);

CREATE INDEX IF NOT EXISTS quality_reports_diagnostics_expiry_idx
    ON quality_reports (diagnostics_expires_at)
    WHERE diagnostics_json IS NOT NULL;
