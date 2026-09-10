type Recommendation = {
  kind: 'fact' | 'inference' | 'recommendation';
  text: string;
  confidence: number;
  provenance: string[];
  providerId: string;
  modelId: string;
};

const baseline: Recommendation = {
  kind: 'recommendation',
  text: 'Review the most recent character events before making a progression decision.',
  confidence: 0.72,
  provenance: ['sentinel-core:context-baseline'],
  providerId: 'sentinel-core',
  modelId: 'context-baseline-v1',
};

export function RecommendationPanel({ recommendation = baseline }: { recommendation?: Recommendation }) {
  const confidence = `${Math.round(recommendation.confidence * 100)}%`;

  return (
    <article className="card recommendation-panel" aria-label="SENTINEL recommendation">
      <div className="recommendation-heading">
        <div>
          <div className="label">INTELLIGENCE / {recommendation.kind.toUpperCase()}</div>
          <h2>Recommendation</h2>
        </div>
        <span className="confidence">{confidence}</span>
      </div>
      <p className="recommendation-text">{recommendation.text}</p>
      <div className="recommendation-meta">
        <div><span className="label">PROVIDER</span><strong>{recommendation.providerId}</strong></div>
        <div><span className="label">MODEL</span><strong>{recommendation.modelId}</strong></div>
        <div><span className="label">PROVENANCE</span><strong>{recommendation.provenance.join(' · ')}</strong></div>
      </div>
      <div className="recommendation-boundary">
        <span className="info">●</span> Observational only · no action execution
      </div>
    </article>
  );
}
