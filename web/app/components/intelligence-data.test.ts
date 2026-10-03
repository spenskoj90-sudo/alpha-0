import { describe, expect, it } from 'vitest';
import { parseRecommendation, freshness } from './intelligence-data';
const item = { kind: 'recommendation', text: 'Review.', confidence: null, provenance: ['source'], provider_id: 'sentinel-core', model_id: 'context-baseline-v1' };
describe('Intelligence presentation', () => {
  it('preserves unknown confidence without a synthetic zero', () => { expect(parseRecommendation(item)?.confidence).toBeNull(); });
  it('rejects nonfinite or malformed metadata', () => {
    expect(parseRecommendation({ ...item, confidence: NaN })).toBeNull();
    expect(parseRecommendation({ ...item, provenance: [''] })).toBeNull();
    expect(parseRecommendation({ ...item, confidence: 1.1 })).toBeNull();
  });
  it('keeps source freshness unknown when only retrieval time exists', () => {
    expect(freshness(null, 1000)).toBe('unknown');
    expect(freshness(1000, 900)).toBe('unknown');
    expect(freshness(1000, 3000)).toBe('fresh');
    expect(freshness(1000, 20000)).toBe('stale');
  });
});
