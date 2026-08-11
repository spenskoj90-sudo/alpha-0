CREATE TABLE IF NOT EXISTS wow_patches (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    family TEXT NOT NULL CHECK (family IN ('retail', 'classic')),
    protocol_generation TEXT NOT NULL,
    supported BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS wow_realms (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    realm_type TEXT NOT NULL CHECK (realm_type IN ('official', 'private')),
    patch_id TEXT NOT NULL REFERENCES wow_patches(id),
    source TEXT NOT NULL,
    monitoring_profile TEXT NOT NULL,
    client_integration TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS wow_realm_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    realm_id TEXT NOT NULL REFERENCES wow_realms(id) ON DELETE CASCADE,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL CHECK (status IN ('ONLINE', 'DEGRADED', 'OFFLINE', 'UNKNOWN')),
    latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    player_count INTEGER CHECK (player_count IS NULL OR player_count >= 0),
    endpoint_host TEXT,
    endpoint_port INTEGER CHECK (endpoint_port IS NULL OR endpoint_port BETWEEN 1 AND 65535),
    client_build TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_wow_observations_realm_time ON wow_realm_observations(realm_id, observed_at DESC);

INSERT INTO wow_patches (id, label, family, protocol_generation) VALUES
('retail-12.0.5', 'Retail / Midnight 12.0.5', 'retail', 'retail-12'),
('vanilla-1.12', 'Vanilla 1.12', 'classic', 'classic-1'),
('tbc-2.4.3', 'The Burning Crusade 2.4.3', 'classic', 'classic-2'),
('wotlk-3.3.5a', 'Wrath of the Lich King 3.3.5a', 'classic', 'classic-3'),
('cata-4.3.4', 'Cataclysm 4.3.4', 'classic', 'classic-4'),
('mop-5.4.8', 'Mists of Pandaria 5.4.8', 'classic', 'classic-5'),
('wod-6.2.4', 'Warlords of Draenor 6.2.4', 'classic', 'classic-6'),
('legion-7.3.5', 'Legion 7.3.5', 'classic', 'classic-7'),
('bfa-8.3.7', 'Battle for Azeroth 8.3.7', 'classic', 'classic-8'),
('shadowlands-9.2.7', 'Shadowlands 9.2.7', 'classic', 'classic-9'),
('dragonflight-10.2.7', 'Dragonflight 10.2.7', 'classic', 'classic-10')
ON CONFLICT (id) DO UPDATE SET label = EXCLUDED.label, supported = TRUE;

INSERT INTO wow_realms (id, name, realm_type, patch_id, source, monitoring_profile, client_integration) VALUES
('mmotop-uwow', 'Uwow', 'private', 'legion-7.3.5', 'MMOTOP', 'legion-private', 'launcher-plus-addon'),
('mmotop-skyblood', 'SkyBlood', 'private', 'legion-7.3.5', 'MMOTOP', 'legion-private', 'launcher-plus-addon'),
('mmotop-wow-prime', 'WoW-Prime', 'private', 'legion-7.3.5', 'MMOTOP', 'custom-launcher', 'launcher-plus-addon'),
('mmotop-neverest', 'Neverest', 'private', 'wotlk-3.3.5a', 'MMOTOP', 'wotlk-private', 'launcher-plus-addon'),
('mmotop-epicwow', 'EpicWoW', 'private', 'legion-7.3.5', 'MMOTOP', 'legion-private', 'launcher-plus-addon'),
('mmotop-1001wow', '1001WOW', 'private', 'wotlk-3.3.5a', 'MMOTOP', 'wotlk-private', 'launcher-plus-addon'),
('mmotop-northwind', 'Northwind', 'private', 'vanilla-1.12', 'MMOTOP', 'vanilla-private', 'launcher-plus-addon'),
('mmotop-poligon7', 'Poligon7', 'private', 'vanilla-1.12', 'MMOTOP', 'vanilla-private', 'launcher-plus-addon'),
('mmotop-nozdor', 'Nozdor', 'private', 'wotlk-3.3.5a', 'MMOTOP', 'wotlk-private', 'launcher-plus-addon'),
('mmotop-turbo-wow', 'Turbo-WoW', 'private', 'dragonflight-10.2.7', 'MMOTOP', 'dragonflight-private', 'launcher-plus-addon')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, patch_id = EXCLUDED.patch_id, enabled = TRUE;
