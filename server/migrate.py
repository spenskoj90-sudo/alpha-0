from __future__ import annotations

import hashlib
import os
from pathlib import Path

import psycopg

DATABASE_URL = os.environ["DATABASE_URL"]
MIGRATIONS = Path(__file__).resolve().parent / "migrations"


def main() -> None:
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            cur.execute("SELECT version, checksum FROM schema_migrations")
            applied = dict(cur.fetchall())
            for path in sorted(MIGRATIONS.glob("*.sql")):
                version = path.stem
                checksum = hashlib.sha256(path.read_bytes()).hexdigest()
                if version in applied:
                    if applied[version] != checksum:
                        raise RuntimeError(f"Migration checksum mismatch: {version}")
                    continue
                cur.execute(path.read_text(encoding="utf-8"))
                cur.execute(
                    "INSERT INTO schema_migrations(version, checksum) VALUES (%s, %s)",
                    (version, checksum),
                )


if __name__ == "__main__":
    main()
