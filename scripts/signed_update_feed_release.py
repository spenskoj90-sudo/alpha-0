#!/usr/bin/env python3
"""Offline source-only signed-update feed producer. Never publishes or creates keys.

Requires an independently approved APK and an owner-controlled P-256 feed key.
Public pin, APK identity and monotonically increasing version must be supplied
from the independently reviewed release record, not inferred from the feed.
"""
import argparse
import base64
import hashlib
import hmac
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

MAX_APK = 256 * 1024 * 1024
# Existing independently checked release signer; a new lineage needs a source+Owner gate.
APPROVED_SIGNER = "2acd1cfff4f34db1250d3f6c81f0887493c4602d3cfa65310993c058089db88e"
FINGERPRINT = re.compile(r"[0-9a-f]{64}\Z")
PACKAGE = re.compile(r"^package: name='([^']+)' versionCode='([0-9]+)'", re.MULTILINE)
CERT = re.compile(r"Signer #\d+ certificate SHA-256 digest: ([0-9a-fA-F:]{64,95})")
INSTALL_PERMISSION = re.compile(r"(?m)^uses-permission:\s+name='android\.permission\.REQUEST_INSTALL_PACKAGES'(?:\s|$)")


def tool(args, *, data=None):
    # Tool stderr may contain filesystem or key metadata; never echo it.
    try:
        result = subprocess.run(args, input=data, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("required local verification tool unavailable") from exc
    if result.returncode != 0:
        raise ValueError("local verification or signing step failed")
    return result.stdout


def url(value, apk=False):
    parts = urlsplit(value)
    if not value.startswith("https://") or parts.scheme != "https" or not parts.hostname or \
       parts.username is not None or parts.password is not None or parts.query or parts.fragment or \
       parts.port not in (None, 443) or not re.fullmatch(r"[a-z0-9.-]+(?::443)?", parts.netloc) or \
       parts.hostname.endswith(".") or not parts.path.startswith("/") or \
       not re.fullmatch(r"/[A-Za-z0-9_./-]+", parts.path) or \
       any(p in ("", ".", "..") for p in parts.path[1:].split("/")):
        raise ValueError("feed and APK require strict HTTPS URLs without ambiguous paths")
    if apk and not parts.path.endswith(".apk"):
        raise ValueError("APK URL must end with .apk")
    return parts.hostname, parts.port


def notes(data):
    if len(data) > 1024:
        raise ValueError("release notes too long")
    value = data.decode("utf-8", "strict")
    if not value.strip() or len(value.splitlines()) > 12 or any(
        (ord(c) < 32 and c != "\n") or 0x7f <= ord(c) <= 0x9f or
        ord(c) == 0x61c or 0x200e <= ord(c) <= 0x200f or
        0x202a <= ord(c) <= 0x202e or 0x2066 <= ord(c) <= 0x2069
        for c in value
    ):
        raise ValueError("invalid release notes")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make(args):
    origin = url(args.feed_url)
    if origin != url(args.apk_url, apk=True):
        raise ValueError("APK must use the feed's exact HTTPS origin")
    expected = args.expected_signer.lower().replace(":", "")
    if expected != APPROVED_SIGNER or not FINGERPRINT.fullmatch(expected) or args.previous_version < 0:
        raise ValueError("invalid release signer or baseline")
    apk = Path(args.apk)
    if not apk.is_file() or not 0 < apk.stat().st_size <= MAX_APK:
        raise ValueError("APK size outside allowed bounds")
    # Hash the candidate before invoking external inspection tools; reject a
    # workspace race that changes the inspected file before feed signing.
    def apk_sha256():
        digest = hashlib.sha256()
        with apk.open("rb") as source:
            for block in iter(lambda: source.read(65536), b""):
                digest.update(block)
        return digest.hexdigest()
    initial_hash = apk_sha256()
    badging = tool([args.aapt2, "dump", "badging", str(apk)]).decode("utf-8", "strict")
    package = PACKAGE.search(badging)
    if not package or package.group(1) != "com.alpha0.app":
        raise ValueError("APK package does not match the existing application ID")
    version = int(package.group(2))
    if re.search(r"(?m)^application-debuggable(?:\s|$)", badging):
        raise ValueError("signedRelease APK must not be debuggable")
    if not args.previous_version < version <= 2_100_000_000:
        raise ValueError("release version must strictly exceed distributed baseline")
    signatures = CERT.findall(tool([args.apksigner, "verify", "--print-certs", str(apk)]).decode("ascii", "strict"))
    if len(signatures) != 1 or signatures[0].lower().replace(":", "") != expected:
        raise ValueError("APK must carry the separately approved single signing certificate")
    if apk_sha256() != initial_hash:
        raise ValueError("APK bytes changed during identity inspection")
    permissions = tool([args.aapt2, "dump", "permissions", str(apk)]).decode("utf-8", "strict")
    if not INSTALL_PERMISSION.search(permissions):
        raise ValueError("signedRelease APK must declare installer permission")
    if apk_sha256() != initial_hash:
        raise ValueError("APK bytes changed during manifest permission inspection")
    pin = base64.b64decode(args.verifying_key, validate=True)
    public = tool(["openssl", "pkey", "-in", str(args.feed_private_key), "-pubout", "-outform", "DER"])
    if not hmac.compare_digest(public, pin):
        raise ValueError("feed private key does not match the approved public pin")
    key_info = tool(["openssl", "pkey", "-pubin", "-inform", "DER", "-text_pub", "-noout"], data=public)
    if b"ASN1 OID: prime256v1" not in key_info or b"Public-Key: (256 bit)" not in key_info:
        raise ValueError("feed signature requires named P-256 curve")
    note_b64 = notes(Path(args.notes).read_bytes())
    manifest = ("SENTINEL-UPDATE-v1\npackage=com.alpha0.app\n"
                f"versionCode={version}\ncertificateSha256={expected}\n"
                f"apkUrl={args.apk_url}\napkSha256={initial_hash}\n"
                f"whatsNewBase64={note_b64}\n").encode("utf-8")
    if len(manifest) > 4096:
        raise ValueError("manifest exceeds bounded wire format")
    signature = tool(["openssl", "dgst", "-sha256", "-sign", str(args.feed_private_key)], data=manifest)
    encode = lambda payload: base64.urlsafe_b64encode(payload).rstrip(b"=")
    wire = b"SENTINEL-SIGNED-FEED-v1\n" + encode(manifest) + b"\n" + encode(signature) + b"\n"
    if len(wire) > 8192:
        raise ValueError("signed feed exceeds bounded wire format")
    # Reject changes made while signing or preparing output as well.
    if apk_sha256() != initial_hash:
        raise ValueError("APK bytes changed before signed-feed output")
    # Local artifact only; refuse replacing a prior manifest/feed silently.
    with open(args.output, "xb") as output:
        output.write(wire)
        output.flush()
        os.fsync(output.fileno())
    return initial_hash


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("apk", "aapt2", "apksigner", "feed-url", "apk-url", "notes",
                "feed-private-key", "verifying-key", "expected-signer", "output"):
        p.add_argument("--" + key, required=True, type=Path if key in ("apk", "notes", "feed-private-key", "output") else str)
    p.add_argument("--previous-version", type=int, required=True)
    args = p.parse_args(argv)
    make(args)
    print("PASS: offline signed feed written; publication, signing custody and device upgrade NOT_RUN")


if __name__ == "__main__":
    main()
