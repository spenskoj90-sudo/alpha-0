"""Offline reviewed publication using native operator custody; no serving import."""
import argparse
import os
import time
from pathlib import Path

from sqlalchemy import create_engine
from app.core.knowledge_packs import MAX_PACK_BYTES
from app.core.knowledge_publication import publish, revoke


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--digest', required=True)
    parser.add_argument('--revoke', action='store_true')
    parser.add_argument('--file', type=Path)
    parser.add_argument('--review-reference')
    parser.add_argument('--expected-revision', type=int)
    args = parser.parse_args()
    # Deliberately never fall back to the runtime URL or accept credentials on CLI.
    custody = os.getenv('DATABASE_MIGRATION_URL')
    if not custody:
        parser.error('Native DATABASE_MIGRATION_URL operator custody required')
    engine = None
    try:
        engine = create_engine(custody, pool_pre_ping=True)
        now = time.time_ns() // 1_000_000
        if args.revoke:
            revision = revoke(engine, args.digest, now_ms=now)
        else:
            if not args.file or not args.review_reference or args.expected_revision is None:
                parser.error('file, independent review-reference and expected-revision required')
            if args.file.stat().st_size > MAX_PACK_BYTES:
                parser.error('Pack size exceeds bound')
            revision = publish(engine, args.file.read_bytes(), args.digest, args.review_reference,
                               expected_revision=args.expected_revision, now_ms=now)
        print(f'KNOWLEDGE_REVISION={revision}')
    except Exception:
        # Operator SQL/connection exceptions can contain credentials or raw content.
        raise SystemExit('KNOWLEDGE_OPERATOR_OPERATION_FAILED') from None
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == '__main__':
    main()
