from __future__ import annotations

import json
import os

from sqlalchemy import create_engine

from app.core.operational_maintenance import PostgresOperationalMaintenance


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print(json.dumps({"status": "SKIPPED", "reason": "DATABASE_URL_NOT_CONFIGURED"}))
        return
    engine = create_engine(database_url, pool_pre_ping=True, connect_args={"options": "-c app.service_role=true"})
    try:
        counts = PostgresOperationalMaintenance(engine).run_batch()
    finally:
        engine.dispose()
    print(json.dumps({"status": "OK", "deleted_or_scrubbed": counts}, sort_keys=True))


if __name__ == "__main__":
    main()
