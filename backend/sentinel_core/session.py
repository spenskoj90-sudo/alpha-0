from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets
from uuid import UUID, uuid4

from .device_identity import verify_signature
from .security import canonical_session_message, ReplayGuard


@dataclass
class Challenge:
    session_id: UUID
    device_id: UUID
    nonce: str
    request_hash: bytes
    expires_at: datetime
    consumed: bool = False


class SessionProtocol:
    """Reference implementation of challenge-response session establishment.

    Persistence is deliberately injected so production can use PostgreSQL while unit
    tests can use an in-memory implementation. No client-controlled authorization data
    is accepted by this service.
    """

    def __init__(self, ttl_seconds: int = 900, challenge_ttl_seconds: int = 60) -> None:
        self.ttl_seconds = ttl_seconds
        self.challenge_ttl_seconds = challenge_ttl_seconds
        self._challenges: dict[UUID, Challenge] = {}
        self._sessions: dict[str, tuple[UUID, UUID, datetime]] = {}
        self._replay = ReplayGuard()

    def issue_challenge(self, device_id: UUID, request_body: bytes = b"") -> Challenge:
        session_id = uuid4()
        nonce = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        challenge = Challenge(
            session_id=session_id,
            device_id=device_id,
            nonce=nonce,
            request_hash=sha256(request_body).digest(),
            expires_at=now + timedelta(seconds=self.challenge_ttl_seconds),
        )
        self._challenges[session_id] = challenge
        return challenge

    def verify(
        self,
        session_id: UUID,
        device_id: UUID,
        public_key_spki: bytes,
        signature: bytes,
        request_hash: bytes,
    ) -> str:
        challenge = self._challenges.get(session_id)
        if challenge is None:
            raise ValueError("unknown session challenge")
        if challenge.device_id != device_id:
            raise ValueError("device mismatch")
        if challenge.consumed:
            raise ValueError("nonce replay")
        if challenge.request_hash != request_hash:
            raise ValueError("request hash mismatch")
        if not self._replay.verify_and_consume(challenge.nonce, challenge.expires_at):
            raise ValueError("nonce expired or replayed")

        message = canonical_session_message(
            str(session_id), str(device_id), challenge.nonce, request_hash
        )
        if not verify_signature(public_key_spki, message, signature):
            raise ValueError("invalid device signature")

        challenge.consumed = True
        token = secrets.token_urlsafe(48)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds)
        self._sessions[token] = (session_id, device_id, expires_at)
        return token

    def validate(self, token: str) -> tuple[UUID, UUID]:
        item = self._sessions.get(token)
        if item is None:
            raise ValueError("invalid session")
        session_id, device_id, expires_at = item
        if expires_at <= datetime.now(timezone.utc):
            self._sessions.pop(token, None)
            raise ValueError("session expired")
        return session_id, device_id

    def revoke(self, token: str) -> None:
        self._sessions.pop(token, None)
