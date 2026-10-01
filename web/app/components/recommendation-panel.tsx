'use client';

import { useEffect, useRef, useState } from 'react';
import { useLocale } from './locale-provider';

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
  const { t } = useLocale();
  const [view, setView] = useState<ViewState>('IDLE');
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [message, setMessage] = useState('');
  const generation = useRef(0);

  useEffect(() => {
    const revisions = generation;
    const reset = (event: Event) => {
      revisions.current++;
      setRecommendation(null);
      const session = (event as CustomEvent<boolean | null>).detail;
      setView(session === true ? 'IDLE' : session === false ? 'SIGNED_OUT' : 'ERROR');
      setMessage(session === true ? '' : session === false ? 'Sign in to request a live Core recommendation.' : 'Account data is unavailable. Check your connection and retry.');
    };
    window.addEventListener('sentinel-session-changed', reset);
    return () => { revisions.current++; window.removeEventListener('sentinel-session-changed', reset); };
  }, []);

  async function loadRecommendation() {
    const revision = ++generation.current;
    setView('LOADING');
    setMessage('');
    try {
      const response = await fetch('/api/intelligence/recommendations', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        cache: 'no-store',
        signal: AbortSignal.timeout(45_000),
      });
      if (revision !== generation.current) return;
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
        if (revision !== generation.current) return;
      } catch {
        if (revision !== generation.current) return;
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
      if (revision !== generation.current) return;
      setRecommendation(null);
      setMessage('Live recommendation request failed.');
      setView('ERROR');
    }
  }

  const confidence = recommendation ? `${Math.round(recommendation.confidence * 100)}%` : '—';
  const kind = recommendation?.kind.toUpperCase() ?? 'LIVE CORE';

  return (
    <article
      className="card recommendation-panel"
      aria-label={t("SENTINEL recommendation")}
      aria-busy={view === 'LOADING'}
    >
      <div className="recommendation-heading">
        <div>
          <span className="intelligence-kind" data-kind={kind}>{t(kind)}</span>
          <h2>{recommendation ? (kind === 'FACT' ? t("Observed fact") : kind === 'INFERENCE' ? t("Inference") : t("Recommendation")) : t("Trusted intelligence")}</h2>
        </div>
        <span className="confidence" aria-label={`${t("Confidence")} ${confidence}`}>{confidence}</span>
      </div>

      {view === 'READY' && recommendation ? (
        <div role="status" aria-live="polite" aria-atomic="true">
          <p className="recommendation-text">{recommendation.text}</p>
          {recommendation.kind === 'fact' && (
            <div className="recommendation-meta">
              <div><span className="label">{t("Source")}</span><strong>{recommendation.provenance.join(' · ') || t("UNREPORTED")}</strong></div>
              <div><span className="label">{t("Freshness")}</span><strong>{t("UNREPORTED")}</strong></div>
              <div><span className="label">{t("Evidence type")}</span><strong>{t("DIRECTLY OBSERVED")}</strong></div>
            </div>
          )}
          {recommendation.kind === 'inference' && (
            <div className="recommendation-meta">
              <div><span className="label">{t("Confidence")}</span><strong>{confidence}</strong></div>
              <div><span className="label">{t("Contributing signals")}</span><strong>{recommendation.provenance.join(' · ') || t("UNREPORTED")}</strong></div>
              <div><span className="label">{t("Freshness")}</span><strong>{t("UNREPORTED")}</strong></div>
            </div>
          )}
          {recommendation.kind === 'recommendation' && (
            <div className="recommendation-meta">
              <div><span className="label">{t("Action")}</span><strong>{recommendation.text}</strong></div>
              <div><span className="label">{t("Priority")}</span><strong>{t("UNREPORTED")}</strong></div>
              <div><span className="label">{t("Reason")}</span><strong>{t("UNREPORTED")}</strong></div>
              <div><span className="label">{t("Confidence")}</span><strong>{confidence}</strong></div>
              <div><span className="label">{t("Source / time")}</span><strong>{recommendation.provenance.join(' · ') || t("UNREPORTED")}{' '}{t("· time UNREPORTED")}</strong></div>
              <div><span className="label">{t("Acknowledgement")}</span><strong>{t("NOT RECORDED")}</strong></div>
            </div>
          )}
          <div className="microcopy">{t("Provider")}{' '}{recommendation.provider_id ?? t("unreported")}{' '}{t("· model")}{' '}{recommendation.model_id ?? t("unreported")}</div>
        </div>
      ) : (
        <p
          className="muted"
          role={view === 'ERROR' ? 'alert' : 'status'}
          aria-live={view === 'ERROR' ? 'assertive' : 'polite'}
          aria-atomic="true"
        >
          {view === 'LOADING' ? t("Requesting bounded intelligence from Core…") : t(message) || t("Request a live recommendation through the authenticated Core boundary.")}
        </p>
      )}

      <div className="button-row">
        <button className="ghost-btn" onClick={() => void loadRecommendation()} disabled={view === 'LOADING'}>
          {view === 'LOADING' ? t("Requesting…") : view === 'READY' ? t("Refresh") : t("Load live")}
        </button>
        {view === 'SIGNED_OUT' && <span className="microcopy">{t("Authentication is required.")}</span>}
        {view === 'ERROR' && <span className="microcopy">{t("Failure is bounded; no fallback is treated as live evidence.")}</span>}
      </div>

      <div className="recommendation-boundary">
        <span className="info" aria-hidden="true">●</span>{' '}{t("Observational only · no action execution")}{' '}</div>
    </article>
  );
}
