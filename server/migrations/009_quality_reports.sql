CREATE TABLE IF NOT EXISTS quality_reports (
    id uuid PRIMARY KEY,
    user_id text NOT NULL,
    device_id uuid NULL,
    category varchar(32) NOT NULL,
    title varchar(160) NOT NULL,
    description text NOT NULL,
    status varchar(32) NOT NULL DEFAULT 'RECEIVED',
    diagnostics_consent boolean NOT NULL DEFAULT false,
    quality_program_opt_in boolean NOT NULL DEFAULT false,
    diagnostics_json jsonb NULL,
    diagnostics_bytes integer NOT NULL DEFAULT 0,
    diagnostics_expires_at timestamptz NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT quality_reports_category_ck CHECK (
        category IN ('DESIGN','FUNCTIONALITY','GAME_INTEGRATION','PERFORMANCE','ACCESSIBILITY','VOICE_AUDIO','SECURITY_PRIVACY','OTHER')
    ),
    CONSTRAINT quality_reports_status_ck CHECK (
        status IN ('RECEIVED','TRIAGED','IN_PROGRESS','RESOLVED','WONT_FIX')
    ),
    CONSTRAINT quality_reports_diagnostics_bytes_ck CHECK (
        diagnostics_bytes >= 0 AND diagnostics_bytes <= 393216
    ),
    CONSTRAINT quality_reports_diagnostics_consent_ck CHECK (
        (
            diagnostics_consent
            AND diagnostics_expires_at IS NOT NULL
            AND (
                (diagnostics_json IS NOT NULL AND diagnostics_bytes > 0)
                OR (diagnostics_json IS NULL AND diagnostics_bytes = 0)
            )
        )
        OR
        (
            NOT diagnostics_consent
            AND diagnostics_json IS NULL
            AND diagnostics_bytes = 0
            AND diagnostics_expires_at IS NULL
        )
    )
);

CREATE INDEX IF NOT EXISTS quality_reports_created_at_idx
    ON quality_reports (created_at DESC);

CREATE INDEX IF NOT EXISTS quality_reports_status_created_idx
    ON quality_reports (status, created_at DESC);

CREATE INDEX IF NOT EXISTS quality_reports_user_created_idx
    ON quality_reports (user_id, created_at DESC);
