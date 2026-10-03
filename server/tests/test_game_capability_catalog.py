import pytest
from app.core.game_capability_catalog import catalog
from app.core.knowledge_packs import load_pack
from pathlib import Path
import json


def test_owner_games_have_environment_specific_unknown_metrics():
    data=catalog()
    assert len(data['profiles'])==26
    assert {'world-of-warcraft','shattered-pixel-dungeon','deadlock','luanti'} <= {p['game'] for p in data['profiles']}
    for profile in data['profiles']:
        assert profile['latency_ms'] is None
        assert profile['confidence'] is None
        assert not profile['deterministic_automation']
        assert not profile['user_confirmed_actions']
        assert profile['exact_environment_status']=='l3_pending'


def test_catalog_returns_independent_data():
    one=catalog(); one['profiles'].clear()
    assert len(catalog()['profiles'])==26


def test_wotlk_foundation_is_digest_bound_but_not_verified_strategy():
    data=Path(__file__).parents[1]/'app/data'
    entry=json.loads((data/'knowledge-pack-index.v1.json').read_text())['packs'][0]
    loaded=load_pack((data/entry['file']).read_bytes(),entry['sha256'])
    assert loaded.pack.status=='draft'
    assert not loaded.pack.rules
    assert {'tank_mitigation','healing_priority','dispels','boss_mechanics'} <= set(loaded.pack.coverage)
