from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from pydantic import ValidationError

from app.core.exact_environment_evidence import (
    ExactEnvironmentEvidenceBundle,
    validate_exact_environment_evidence,
)


_MAX_BUNDLE_BYTES = 2 * 1024 * 1024
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_ENVIRONMENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a SENTINEL exact-environment WoW L3 evidence bundle.",
    )
    parser.add_argument("bundle", help="Path to the captured JSON evidence bundle")
    parser.add_argument(
        "--expected-source-sha",
        required=True,
        help="Exact 40-character SENTINEL Git SHA expected on the packaged host",
    )
    parser.add_argument(
        "--expected-environment-id",
        required=True,
        help="Exact stable environment identifier for the target game/client/server test stand",
    )
    return parser


def _load_bundle(path: Path) -> ExactEnvironmentEvidenceBundle:
    if not path.is_absolute():
        path = path.resolve()
    stat = path.lstat()
    if path.is_symlink() or not stat.is_file():
        raise ValueError("evidence bundle must be a regular non-symlink file")
    if stat.st_size <= 1 or stat.st_size > _MAX_BUNDLE_BYTES:
        raise ValueError("evidence bundle size is outside the accepted bound")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("evidence bundle is not valid bounded UTF-8 JSON") from exc
    return ExactEnvironmentEvidenceBundle.model_validate(payload)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not _GIT_SHA_RE.fullmatch(args.expected_source_sha):
        print("L3_EVIDENCE_REJECTED: --expected-source-sha must be lowercase 40-character Git SHA", file=sys.stderr)
        return 2
    if not _ENVIRONMENT_ID_RE.fullmatch(args.expected_environment_id):
        print("L3_EVIDENCE_REJECTED: --expected-environment-id is invalid", file=sys.stderr)
        return 2

    try:
        bundle = _load_bundle(Path(args.bundle))
        summary = validate_exact_environment_evidence(bundle)
        if summary.source_sha != args.expected_source_sha:
            raise ValueError("evidence source SHA does not match the explicitly expected SHA")
        if summary.environment_id != args.expected_environment_id:
            raise ValueError("evidence environment_id does not match the explicitly expected environment")
    except (OSError, ValueError, ValidationError) as exc:
        message = str(exc).splitlines()[0][:512] or "invalid evidence"
        print(f"L3_EVIDENCE_REJECTED: {message}", file=sys.stderr)
        return 2

    print(json.dumps(summary.model_dump(mode="json"), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
