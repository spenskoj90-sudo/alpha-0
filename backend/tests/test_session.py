from base64 import b64encode
from hashlib import sha256
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from sentinel_core.security import canonical_session_message
from sentinel_core.session import SessionProtocol


def test_challenge_response_and_replay_protection():
    protocol = SessionProtocol(ttl_seconds=60, challenge_ttl_seconds=30)
    private = ec.generate_private_key(ec.SECP256R1())
    public_der = private.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    device_id = uuid4()
    challenge = protocol.issue_challenge(device_id)
    request_hash = challenge.request_hash
    message = canonical_session_message(str(challenge.session_id), str(device_id), challenge.nonce, request_hash)
    signature = private.sign(message, ec.ECDSA(hashes.SHA256()))

    token = protocol.verify(challenge.session_id, device_id, public_der, signature, request_hash)
    assert protocol.validate(token) == (challenge.session_id, device_id)

    with pytest.raises(ValueError):
        protocol.verify(challenge.session_id, device_id, public_der, signature, request_hash)
