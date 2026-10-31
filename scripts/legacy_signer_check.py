#!/usr/bin/env python3
"""Owner-gated legacy key identity check. Emits public metadata only; no APK."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import secrets
import subprocess
import tempfile

REPOSITORY = "spenskoj90-sudo/alpha-0"
WORKFLOW = REPOSITORY + "/.github/workflows/legacy-signer-check.yml@refs/heads/main"
SECRET_NAMES = ("LEGACY_KEYSTORE_BASE64", "LEGACY_KEYSTORE_PASSWORD", "LEGACY_KEY_ALIAS", "LEGACY_KEY_PASSWORD")


class CheckFailed(Exception):
    """Deliberately carries no tool diagnostics or secret values."""


def validate_context(source_sha, env):
    expected = {"GITHUB_REPOSITORY": REPOSITORY, "GITHUB_REPOSITORY_ID": "1328718401",
                "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_SHA": source_sha, "GITHUB_WORKFLOW_REF": WORKFLOW}
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha) or any(env.get(k) != v for k, v in expected.items()):
        raise CheckFailed()


def require_memory_storage():
    mounts = Path("/proc/self/mountinfo").read_text().splitlines()
    if not any(" /dev/shm " in line and " - tmpfs " in line for line in mounts):
        raise CheckFailed()
    if len(Path("/proc/swaps").read_text().splitlines()) != 1:
        raise CheckFailed()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def write_private(path, data):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as output:
        output.write(data)


def run_tool(args, directory):
    # Never give subprocesses the GitHub token or the original secret environment.
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8", "HOME": str(directory)}
    result = subprocess.run(args, env=env, cwd=directory, capture_output=True, timeout=30)
    if result.returncode:
        raise CheckFailed()
    return result.stdout, result.stderr


def check(source_sha, expected_pin):
    evidence = {"schema": "sentinel.legacy-signer-check.v1", "status": "FAIL", "stage": "run-context",
                "sourceSha": source_sha if re.fullmatch(r"[0-9a-f]{40}", source_sha) else "INVALID",
                "privateKeyProof": "NOT_RUN", "custodyRestore": "NOT_RUN",
                "apkSigned": False, "keyExported": False}
    try:
        validate_context(source_sha, os.environ)
        evidence["stage"] = "input"
        if not re.fullmatch(r"[0-9a-f]{64}", expected_pin):
            raise CheckFailed()
        encoded, store_password, alias, key_password = (os.environ.pop(k, "") for k in SECRET_NAMES)
        if not all((encoded, store_password, alias, key_password)) or len(encoded) > 350000:
            raise CheckFailed()
        if alias.startswith("-") or len(alias) > 256 or any(ord(c) < 32 for c in alias):
            raise CheckFailed()
        if any(c in store_password + key_password for c in "\r\n\x00"):
            raise CheckFailed()
        blob = base64.b64decode("".join(encoded.split()), validate=True)
        if not blob or len(blob) > 256000:
            raise CheckFailed()
        evidence["stage"] = "memory-preflight"
        require_memory_storage()
        with tempfile.TemporaryDirectory(prefix="sentinel-key-check-", dir="/dev/shm") as tmp:
            directory = Path(tmp)
            key, store, password = (directory / n for n in ("legacy.keystore", "store-password", "key-password"))
            cert, request = directory / "certificate.der", directory / "proof.csr"
            write_private(key, blob)
            write_private(store, store_password.encode())
            write_private(password, key_password.encode())
            evidence["keystoreSha256"] = hashlib.sha256(blob).hexdigest()
            evidence["stage"] = "certificate-read"
            run_tool(["keytool", "-exportcert", "-keystore", str(key), "-storepass:file", str(store),
                      "-alias", alias, "-file", str(cert)], directory)
            pin = hashlib.sha256(cert.read_bytes()).hexdigest()
            evidence["certificateSha256"] = pin
            evidence["stage"] = "certificate-pin"
            if pin != expected_pin:
                raise CheckFailed()
            evidence["stage"] = "private-key-proof"
            run_tool(["keytool", "-certreq", "-keystore", str(key), "-storepass:file", str(store),
                      "-keypass:file", str(password), "-alias", alias, "-dname",
                      "CN=Custody Check " + secrets.token_hex(16), "-file", str(request)], directory)
            out, err = run_tool(["openssl", "req", "-in", str(request), "-verify", "-noout"], directory)
            if b"verify OK" not in out + err:
                raise CheckFailed()
            request_key, _ = run_tool(["openssl", "req", "-in", str(request), "-pubkey", "-noout"], directory)
            cert_key, _ = run_tool(["openssl", "x509", "-inform", "DER", "-in", str(cert), "-pubkey", "-noout"], directory)
            if request_key != cert_key or hashlib.sha256(key.read_bytes()).hexdigest() != evidence["keystoreSha256"]:
                raise CheckFailed()
            evidence.update(status="PASS", stage="complete", privateKeyProof="PASS")
    except Exception:
        # Command errors can contain aliases, paths or credentials: never print them.
        pass
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--expected-certificate-sha256", required=True)
    args = parser.parse_args()
    evidence = check(args.source_sha, args.expected_certificate_sha256)
    print(json.dumps(evidence, sort_keys=True))
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
