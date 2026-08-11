from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from sentinel_core.device_identity import fingerprint_from_spki, verify_device_public_key, verify_signature


def test_p256_fingerprint_and_signature():
    private = ec.generate_private_key(ec.SECP256R1())
    spki = private.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    fingerprint = fingerprint_from_spki(spki)
    message = b"sentinel-test"
    signature = private.sign(message, ec.ECDSA(hashes.SHA256()))
    assert verify_device_public_key(spki, fingerprint)
    assert verify_signature(spki, message, signature)
    assert not verify_signature(spki, b"tampered", signature)
