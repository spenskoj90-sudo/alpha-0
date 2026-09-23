'use client';

import { useState } from 'react';

type Recommendation = {
  kind: 'fact' | 'inference' | 'recommendation';
  text: string;
  confidence: number;
  provenance: string[];
  provider_id: string | null;
  model_id: string | null;
};

type RecommendationPayload = {
  recommendations?: Recommendation[];
};

type ViewState = 'IDLE' | 'LOADING' | 'SIGNED_OUT' | 'READY' | 'ERROR';

function validRecommendation(value: unknown): value is Recommendation {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<Recommendation>;
  return (
    (candidate.kind === 'fact' || candidate.kind === 'inference' || candidate.kind === 'recommendation') &&
    typeof candidate.text === 'string' && candidate.text.length > 0 && candidate.text.length <= 2000 &&
    typeof candidate.confidence === 'number' && candidate.confidence >= 0 && candidate.confidence <= 1 &&
    Array.isArray(candidate.provenance) && candidate.provenance.length <= 20 && candidate.provenance.every(item => typeof item === 'string') &&
    (candidate.provider_id === null || typeof candidate.provider_id === 'string') &&
    (candidate.model_id === null || typeof candidate.model_id === 'string')
  );
}

export function RecommendationPanel() {
  const [view, setView] = useState<ViewState>('IDLE');
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [message, setMessage] = useState('');

  async function loadRecommendation() {
    setView('LOADING');
    setMessage('');
    try {
      const response = await fetch('/api/intelligence/recommendations', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        cache: 'no-store',
      });
      if (response.status === 401) {
        setRecommendation(null);
        setMessage('Sign in to request a live Core recommendation.');
        setView('SIGNED_OUT');
        return;
      }
      if (!response.ok) {
        setRecommendation(null);
        setMessage(`Live recommendation unavailable (${response.status}).`);
        setView('ERROR');
        return;
      }
      let payload: RecommendationPayload;
      try {
        payload = await response.json() as RecommendationPayload;
      } catch {
        setRecommendation(null);
        setMessage('Core returned an invalid recommendation response.');
        setView('ERROR');
        return;
      }
      const first = payload.recommendations?.[0];
      if (!validRecommendation(first)) {
        setRecommendation(null);
        setMessage('Core returned no valid bounded recommendation.');
        setView('ERROR');
        return;
      }
      setRecommendation(first);
      setView('READY');
    } catch {
      setRecommendation(null);
      setMessage('Live recommendation request failed.');
      setView('ERROR');
    }
  }

  const confidence = recommendation ? `${Math.round(recommendation.confidence * 100)}%` : '—';
  const kind = recommendation?.kind.toUpperCase() ?? 'UNAVAILABLE';
  const heading = kind === 'FACT' ? 'Observed fact' : kind === 'INFERENCE' ? 'Inference' : 'Recommendation';

  return (
    <article
      className="card recommendation-panel"
      aria-label="SENTINEL recommendation"
      aria-busy={view === 'LOADING'}
    >
      <div className="recommendation-heading">
        <div>
          <span className="intelligence-kind" data-kind={kind}>{kind}</span>
          <h2>{heading}</h2>
        </div>
        <span className="confidence" aria-label={`Confidence ${confidence}`}>{confidence}</span>
      </div>

      {view === 'READY' && recommendation ? (
        <div role="status" aria-live="polite" aria-atomic="true">
          <p className="recommendation-text">{recommendation.text}</p>
          <div className="recommendation-meta">
            <div><span className="label">Provider</span><strong>{recommendation.provider_id ?? 'unreported'}</strong></div>
            <div><span className="label">Model</span><strong>{recommendation.model_id ?? 'unreported'}</strong></div>
            <div><span className="label">Source / provenance</span><strong>{recommendation.provenance.join(' · ') || 'not reported'}</strong></div>
            <div><span className="label">Freshness</span><strong className="data-unavailable">not reported by Core</strong></div>
          </div>
        </div>
      ) : (
        <p
          className="muted"
          role={view === 'ERROR' ? 'alert' : 'status'}
          aria-live={view === 'ERROR' ? 'assertive' : 'polite'}
          aria-atomic="true"
        >
          {view === 'LOADING' ? 'Requesting bounded intelligence from Core…' : message || 'Request a live recommendation through the authenticated Core boundary.'}
        </p>
      )}

      <div className="button-row">
        <button className="ghost-btn" onClick={() => void loadRecommendation()} disabled={view === 'LOADING'}>
          {view === 'LOADING' ? 'Requesting…' : view === 'READY' ? 'Refresh' : 'Load live'}
        </button>
        {view === 'SIGNED_OUT' && <span className="microcopy">Authentication is required.</span>}
        {view === 'ERROR' && <span className="microcopy">Failure is bounded; no fallback is treated as live evidence.</span>}
      </div>

      <div className="recommendation-boundary">
        <span className="info" aria-hidden="true">●</span> Observational only · no action execution
      </div>
    </article>
  );
}
