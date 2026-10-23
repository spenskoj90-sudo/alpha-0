import type { Game, ResearchProfile } from './product-data';

export type GameEvidenceStatus = 'observer_pilot' | 'adapter_foundation' | 'catalog_foundation' | 'research_only';
export type GameInventoryEntry = {
  id: string; name: string; platform: string; patch: string | null; environment: string;
  evidence: GameEvidenceStatus; sources: 'account_catalog' | 'research_inventory' | 'both';
  executable: false; environmentVerified: false;
};
const rank: Record<GameEvidenceStatus, number> = {
  observer_pilot: 0, adapter_foundation: 1, catalog_foundation: 2, research_only: 3,
};
/** This read-only UI projection cannot grant entitlements or authorize actions. */
export function reconcileGameInventory(games: readonly Game[], research: readonly ResearchProfile[]): GameInventoryEntry[] {
  if (games.length > 256 || research.length > 256) throw new Error('GAME_INVENTORY_TOO_LARGE');
  const entries = new Map<string, GameInventoryEntry>();
  for (const game of games) {
    if (!game.id || !game.name || !game.platform || entries.has(game.id)) throw new Error('INVALID_ACCOUNT_GAME_CATALOG');
    entries.set(game.id, { id: game.id, name: game.name, platform: game.platform, patch: null,
      environment: 'unverified', evidence: 'catalog_foundation', sources: 'account_catalog',
      executable: false, environmentVerified: false });
  }
  const seen = new Set<string>();
  for (const profile of research) {
    if (!profile.id || seen.has(profile.id)) throw new Error('INVALID_RESEARCH_GAME_CATALOG');
    seen.add(profile.id);
    const existing = entries.get(profile.id);
    if (existing && (existing.name !== profile.name || existing.platform !== profile.platform))
      throw new Error('GAME_PROFILE_IDENTITY_CONFLICT');
    entries.set(profile.id, { id: profile.id, name: profile.name, platform: profile.platform, patch: profile.patch,
      environment: profile.environment, evidence: profile.implementation_status,
      sources: existing ? 'both' : 'research_inventory', executable: false, environmentVerified: false });
  }
  return [...entries.values()].sort((a, b) =>
    rank[a.evidence] - rank[b.evidence] || a.name.localeCompare(b.name, 'en') || a.id.localeCompare(b.id, 'en'));
}
