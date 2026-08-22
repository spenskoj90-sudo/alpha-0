from __future__ import annotations

from base64 import b64decode
from hashlib import sha256

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature


class DeviceIdentityError(ValueError):
    pass


def fingerprint_from_spki(spki_der: bytes) -> str:
    return sha256(spki_der).hexdigest()


def verify_device_public_key(spki_der: bytes, fingerprint: str) -> bool:
    try:
        public_key = serialization.load_der_public_key(spki_der)
    except (ValueError, TypeError):
        return False
    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        return False
    if public_key.curve.name != "secp256r1":
        return False
    return fingerprint_from_spki(spki_der) == fingerprint.lower()


def verify_signature(spki_der: bytes, message: bytes, signature: bytes) -> bool:
    try:
        public_key = serialization.load_der_public_key(spki_der)
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            return False
        if public_key.curve.name != "secp256r1":
            return False
        public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


def verify_registration(public_key_b64: str, fingerprint: str) -> bytes:
    try:
        spki = b64decode(public_key_b64, validate=True)
    except Exception as exc:
        raise DeviceIdentityError("invalid public key encoding") from exc
    if len(spki) > 4096 or not verify_device_public_key(spki, fingerprint):
        raise DeviceIdentityError("invalid device public key")
    return spki
