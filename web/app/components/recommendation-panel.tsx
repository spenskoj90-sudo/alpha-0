'use client';

import { useEffect, useRef, useState } from 'react';
import { useLocale } from './locale-provider';
import { freshness, parseRecommendation, type Recommendation } from './intelligence-data';

type ViewState = 'IDLE' | 'LOADING' | 'SIGNED_OUT' | 'READY' | 'EMPTY' | 'OFFLINE' | 'ERROR' | 'DENIED';

export function RecommendationPanel() {
  const { t } = useLocale();
  const [view, setView] = useState<ViewState>('IDLE');
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [now, setNow] = useState(0);
  const generation = useRef(0);

  useEffect(() => {
    const invalidate = () => { generation.current++; };
    const reset = (event: Event) => {
      invalidate();
      setRecommendation(null); setAcknowledged(false);
      const session = (event as CustomEvent<boolean | null>).detail;
      setView(session === true ? 'IDLE' : session === false ? 'SIGNED_OUT' : 'ERROR');
    };
    const offline = () => { invalidate(); setRecommendation(null); setView('OFFLINE'); };
    const online = () => { setView(current => current === 'OFFLINE' ? 'IDLE' : current); };
    window.addEventListener('sentinel-session-changed', reset);
    window.addEventListener('offline', offline); window.addEventListener('online', online);
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => {
      invalidate(); window.clearInterval(timer);
      window.removeEventListener('sentinel-session-changed', reset);
      window.removeEventListener('offline', offline); window.removeEventListener('online', online);
    };
  }, []);

  async function loadRecommendation() {
    const revision = ++generation.current;
    setAcknowledged(false); setRecommendation(null);
    if (!navigator.onLine) { setView('OFFLINE'); return; }
    setView('LOADING');
    try {
      const response = await fetch('/api/intelligence/recommendations', {
        method: 'POST', headers: { 'content-type': 'application/json' }, cache: 'no-store', signal: AbortSignal.timeout(45_000),
      });
      if (revision !== generation.current) return;
      if (!response.ok) { setView(response.status === 401 ? 'SIGNED_OUT' : response.status === 403 ? 'DENIED' : 'ERROR'); return; }
      const payload: unknown = await response.json();
      if (revision !== generation.current) return;
      const items = payload && typeof payload === 'object' ? (payload as { recommendations?: unknown }).recommendations : undefined;
      if (Array.isArray(items) && items.length === 0) { setView('EMPTY'); return; }
      const first = Array.isArray(items) && items.length <= 20 ? parseRecommendation(items[0]) : null;
      if (!first) { setView('ERROR'); return; }
      setNow(Date.now()); setRecommendation(first); setView('READY');
    } catch {
      if (revision === generation.current) setView(navigator.onLine ? 'ERROR' : 'OFFLINE');
    }
  }

  const confidence = recommendation?.confidence == null ? t('Unknown') : `${Math.round(recommendation.confidence * 100)}%`;
  const kind = recommendation?.kind.toUpperCase() ?? 'INTELLIGENCE';
  const age = freshness(recommendation?.observed_at_ms, now);
  const message = {
    IDLE: 'Load intelligence when you need a clearer view.', LOADING: 'Reviewing available evidence…',
    SIGNED_OUT: 'Sign in to view your intelligence.', EMPTY: 'No recommendation is available for this context.',
    OFFLINE: 'You are offline. Reconnect to request updated intelligence.', ERROR: 'Intelligence is unavailable. Please retry.',
    DENIED: 'Your session does not permit this request.', READY: '',
  }[view];

  return (
    <article className="card recommendation-panel" aria-label={t('SENTINEL recommendation')} aria-busy={view === 'LOADING'}>
      <div className="recommendation-heading">
        <div><span className="intelligence-kind" data-kind={kind}>{t(kind)}</span><h2>{t('Trusted intelligence')}</h2></div>
        <span className="intelligence-source-mode">{t(recommendation?.engine === 'deterministic' ? 'Deterministic' : recommendation?.engine === 'ai-enhanced' ? 'AI enhanced' : 'Evidence based')}</span>
      </div>
      {view === 'READY' && recommendation ? (
        <div role="status" aria-live="polite" aria-atomic="true">
          <p className="recommendation-text">{recommendation.text}</p>
          {age === 'stale' && <p className="intelligence-notice">{t('Source evidence is stale. Request an update before acting.')}</p>}
          <dl className="intelligence-details">
            <div><dt>{t('Confidence')}</dt><dd>{confidence}</dd></div>
            <div><dt>{t('Freshness')}</dt><dd>{t(age === 'unknown' ? 'Unknown' : age === 'stale' ? 'Stale' : 'Fresh')}</dd></div>
            <div><dt>{t('Priority')}</dt><dd>{recommendation.priority ?? t('Unknown')}</dd></div>
          </dl>
          {recommendation.reason && <p className="intelligence-reason"><strong>{t('Reason')}</strong> {recommendation.reason}</p>}
          <details className="intelligence-provenance"><summary>{t('View evidence and explanation')}</summary><p>{recommendation.provenance.join(' · ')}</p><p className="muted">{t('Unknown confidence means no calibrated estimate is available.')}</p></details>
        </div>
      ) : <p className="intelligence-empty" role={view === 'ERROR' ? 'alert' : 'status'} aria-live={view === 'ERROR' ? 'assertive' : 'polite'} aria-atomic="true">{t(message)}</p>}
      <div className="button-row">
        <button className="ghost-btn" onClick={() => void loadRecommendation()} disabled={view === 'LOADING'}>{t(view === 'LOADING' ? 'Requesting…' : view === 'READY' ? 'Refresh' : 'Load intelligence')}</button>
        {view === 'READY' && recommendation?.kind === 'recommendation' && <button className="ghost-btn" aria-pressed={acknowledged} onClick={() => setAcknowledged(true)}>{t(acknowledged ? 'Acknowledged on this view' : 'Acknowledge')}</button>}
      </div>
      <div className="recommendation-boundary">{t('Recommendations guide you. You decide what happens next.')}</div>
    </article>
  );
}
