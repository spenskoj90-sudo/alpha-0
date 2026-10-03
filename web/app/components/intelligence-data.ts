export type Recommendation = {
  kind: 'fact' | 'inference' | 'recommendation';
  text: string;
  confidence: number | null;
  provenance: string[];
  provider_id: string | null;
  model_id: string | null;
  engine?: 'deterministic' | 'ai-enhanced' | null;
  reason?: string | null;
  priority?: number | null;
  observed_at_ms?: number | null;
};

export function parseRecommendation(value: unknown): Recommendation | null {
  if (!value || typeof value !== 'object') return null;
  const c = value as Partial<Recommendation>;
  const text = (v: unknown, max: number) => typeof v === 'string' && v.trim().length > 0 && v.length <= max;
  if (!['fact', 'inference', 'recommendation'].includes(c.kind ?? '') || !text(c.text, 2000)) return null;
  if (c.confidence !== null && (typeof c.confidence !== 'number' || !Number.isFinite(c.confidence) || c.confidence < 0 || c.confidence > 1)) return null;
  if (!Array.isArray(c.provenance) || !c.provenance.length || c.provenance.length > 20 || !c.provenance.every(s => text(s, 256))) return null;
  if (c.provider_id !== null && !text(c.provider_id, 128)) return null;
  if (c.model_id !== null && !text(c.model_id, 128)) return null;
  if (c.engine != null && c.engine !== 'deterministic' && c.engine !== 'ai-enhanced') return null;
  if (c.reason != null && !text(c.reason, 2000)) return null;
  if (c.priority != null && (!Number.isInteger(c.priority) || c.priority < 0 || c.priority > 100)) return null;
  if (c.observed_at_ms != null && (!Number.isSafeInteger(c.observed_at_ms) || c.observed_at_ms <= 0)) return null;
  return c as Recommendation;
}

export function freshness(observedAt: number | null | undefined, now: number): 'unknown' | 'fresh' | 'stale' {
  if (observedAt == null || observedAt > now) return 'unknown';
  return now - observedAt > 15_000 ? 'stale' : 'fresh';
}
