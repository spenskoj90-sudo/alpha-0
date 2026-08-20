CREATE TABLE IF NOT EXISTS users (
    identity_id UUID PRIMARY KEY REFERENCES identities(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'DISABLED')) DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS users_status_idx ON users(status);
