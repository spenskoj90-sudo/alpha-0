from uuid import uuid4

from app.core.companion_handshake_service import CompanionCompatibility, CompanionHandshakeService
from app.core.companion_protocol import CompanionHandshake


def offered(**overrides):
    values = {
        "protocol_version": "1.0",
        "ugs_schema_version": "1.0",
        "adapter_contract_version": "1.0",
        "core_protocol_version": "1.0",
        "capability_profile": "baseline-v1",
        "instance_id": uuid4(),
    }
    values.update(overrides)
    return CompanionHandshake(**values)


def test_handshake_service_accepts_exact_compatibility():
    service = CompanionHandshakeService(CompanionCompatibility("1.0", "1.0", "1.0", "baseline-v1"))
    result = service.negotiate(offered())
    assert result.accepted is True
    assert result.reason_code == "HANDSHAKE_ACCEPTED"


def test_handshake_service_rejects_schema_mismatch():
    service = CompanionHandshakeService(CompanionCompatibility("1.0", "1.0", "1.0", "baseline-v1"))
    result = service.negotiate(offered(ugs_schema_version="1.1"))
    assert result.accepted is False
    assert result.reason_code == "UGS_SCHEMA_MISMATCH"
