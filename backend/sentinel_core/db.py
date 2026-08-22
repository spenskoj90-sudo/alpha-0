from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


class Database:
    def __init__(self, dsn: str) -> None:
        self.pool = AsyncConnectionPool(dsn, open=False, kwargs={"row_factory": dict_row}, min_size=1, max_size=10)

    async def open(self) -> None:
        await self.pool.open()
        await self.pool.wait()

    async def close(self) -> None:
        await self.pool.close()

    @asynccontextmanager
    async def connection(self) -> AsyncIterator:
        async with self.pool.connection() as conn:
            yield conn

    async def register_device(
        self, user_id: UUID, platform: str, fingerprint: str, public_key_spki: bytes
    ) -> UUID:
        async with self.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO devices(user_id, platform, fingerprint_sha256)
                    VALUES (%s,%s,%s)
                    RETURNING id
                    """,
                    (user_id, platform, fingerprint),
                )
                device_id = (await cur.fetchone())["id"]
                await cur.execute(
                    """
                    INSERT INTO device_keys(device_id, version, public_key_spki, fingerprint_sha256)
                    VALUES (%s,1,%s,%s)
                    """,
                    (device_id, public_key_spki, fingerprint),
                )
            await conn.commit()
        return device_id

    async def get_device_key(self, device_id: UUID) -> dict | None:
        async with self.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT d.id, d.user_id, d.status, k.public_key_spki
                    FROM devices d
                    JOIN device_keys k ON k.device_id=d.id AND k.status='ACTIVE'
                    WHERE d.id=%s AND d.status='ACTIVE'
                    ORDER BY k.version DESC LIMIT 1
                    """,
                    (device_id,),
                )
                return await cur.fetchone()

    async def create_challenge(self, session_id: UUID, device_id: UUID, nonce: str, request_hash: bytes, expires_at) -> None:
        async with self.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO sessions(id,user_id,device_id,token_hash,expires_at) "
                    "SELECT %s,user_id,%s,%s,%s FROM devices WHERE id=%s",
                    (session_id, device_id, "", expires_at, device_id),
                )
                await cur.execute(
                    "INSERT INTO session_nonces(session_id,nonce,request_hash,expires_at) VALUES (%s,%s,%s,%s)",
                    (session_id, nonce, request_hash, expires_at),
                )
            await conn.commit()

    async def consume_nonce(self, session_id: UUID, nonce: str, request_hash: bytes) -> bool:
        async with self.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE session_nonces
                    SET consumed_at=now()
                    WHERE session_id=%s AND nonce=%s AND request_hash=%s
                      AND consumed_at IS NULL AND expires_at > now()
                    RETURNING id
                    """,
                    (session_id, nonce, request_hash),
                )
                ok = await cur.fetchone() is not None
            await conn.commit()
        return ok
