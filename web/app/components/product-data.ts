export type Security = {
  email: string | null;
  email_verified: boolean;
  password_enabled: boolean;
  mfa_enabled: boolean;
  mfa_recovery_codes_remaining: number;
  providers: string[];
};
export type Game = { id: string; name: string; family: string; platform: string; interaction_mode: string };
export type AuditEvent = { action: string; decision: string; reason_code: string; resource: string; created_at?: string };
export type ProductData =
  | { state: 'SIGNED_OUT' }
  | { state: 'ERROR'; message: string }
  | { state: 'READY'; security: Security; games: Game[]; events: AuditEvent[] };

function isSecurity(value: unknown): value is Security {
  if (!value || typeof value !== 'object') return false;
  const data = value as Partial<Security>;
  return (data.email === null || typeof data.email === 'string') &&
    typeof data.email_verified === 'boolean' && typeof data.password_enabled === 'boolean' &&
    typeof data.mfa_enabled === 'boolean' && Number.isInteger(data.mfa_recovery_codes_remaining) &&
    Number(data.mfa_recovery_codes_remaining) >= 0 && Array.isArray(data.providers) &&
    data.providers.every(p => ['google', 'telegram', 'vk'].includes(p));
}

async function read(path: string): Promise<unknown> {
  const response = await fetch(path, { cache: 'no-store', signal: AbortSignal.timeout(45_000) });
  if (response.status === 401) throw new Error('SIGNED_OUT');
  if (!response.ok) throw new Error('UNAVAILABLE');
  return response.json();
}

export async function loadProductData(): Promise<ProductData> {
  try {
    // Serial requests avoid competing rotations of a shared HttpOnly refresh cookie.
    const security = await read('/api/account/security');
    if (!isSecurity(security)) throw new Error('INVALID');
    const catalog = await read('/api/games') as { games?: unknown };
    const audit = await read('/api/activity') as { events?: unknown };
    if (!Array.isArray(catalog?.games) || !Array.isArray(audit?.events)) throw new Error('INVALID');
    if (!catalog.games.every(g => g && ['id', 'name', 'family', 'platform', 'interaction_mode'].every(k => typeof g[k] === 'string'))) throw new Error('INVALID');
    if (!audit.events.every(e => e && ['action', 'decision', 'reason_code', 'resource'].every(k => typeof e[k] === 'string'))) throw new Error('INVALID');
    return { state: 'READY', security, games: catalog.games, events: audit.events.slice().reverse().sort((a, b) => (Date.parse(b.created_at ?? '') || 0) - (Date.parse(a.created_at ?? '') || 0)).slice(0, 100) };
  } catch (error) {
    if (error instanceof Error && error.message === 'SIGNED_OUT') return { state: 'SIGNED_OUT' };
    return { state: 'ERROR', message: 'Product data could not be verified. Check your connection and retry.' };
  }
}
