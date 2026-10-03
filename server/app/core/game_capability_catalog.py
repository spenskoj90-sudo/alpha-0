"""Research/implementation capability inventory, never an authorization registry."""
from __future__ import annotations
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data'


def catalog() -> dict:
    value = json.loads((DATA / 'game-capability-catalog.v1.json').read_text())
    profiles = value['profiles']
    if value['schema_version'] != 1 or len(profiles) > 256 or len({p['id'] for p in profiles}) != len(profiles):
        raise ValueError('GAME_CATALOG_INVALID')
    for profile in profiles:
        # Inventory cannot silently turn research declarations into executable capabilities.
        if profile['deterministic_automation'] or profile['user_confirmed_actions']:
            raise ValueError('GAME_CATALOG_ACTION_AUTHORITY_FORBIDDEN')
        if profile['exact_environment_status'] != 'l3_pending':
            raise ValueError('GAME_CATALOG_UNVERIFIED_PROMOTION')
    return value


def knowledge_index() -> dict:
    return json.loads((DATA / 'knowledge-pack-index.v1.json').read_text())
