'use client';

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';

type Plan = {
  code: string;
  name: string;
  currency: string;
  amount_minor: number;
  interval_days: number;
  entitlement_codes: string[];
};

type Subscription = {
  id: string;
  plan_code: string;
  currency: string;
  provider: string;
  provider_subscription_id: string;
  status: 'PENDING' | 'ACTIVE' | 'PAST_DUE' | 'CANCELED' | 'EXPIRED';
  started_at: string;
  expires_at?: string | null;
  updated_at: string;
};

type Entitlement = {
  id: string;
  game_id: string;
  game_name: string;
  platform: string;
  status: string;
  source: string;
  valid_from: string;
  valid_until: string;
};

type ViewState = 'CHECKING' | 'SIGNED_OUT' | 'READY' | 'ERROR';

function lifecycleText(status: Subscription['status']) {
  switch (status) {
    case 'PENDING': return 'Awaiting provider confirmation';
    case 'ACTIVE': return 'Active';
    case 'PAST_DUE': return 'Payment issue — server policy remains authoritative';
    case 'CANCELED': return 'Canceled';
    case 'EXPIRED': return 'Expired';
  }
}

function money(plan: Plan) {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency: plan.currency }).format(plan.amount_minor / 100);
}

async function responseJson<T>(response: Response): Promise<T | null> {
  try {
    return await response.json() as T;
  } catch {
    return null;
  }
}

export function AccountControl() {
  const [view, setView] = useState<ViewState>('CHECKING');
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [entitlements, setEntitlements] = useState<Entitlement[]>([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const loadAccount = useCallback(async () => {
    setMessage('');
    const plansResponse = await fetch('/api/billing/plans', { cache: 'no-store' });
    if (plansResponse.status === 401) {
      setPlans([]);
      setSubscriptions([]);
      setEntitlements([]);
      setView('SIGNED_OUT');
      return;
    }
    if (!plansResponse.ok) {
      setView('ERROR');
      setMessage(`Unable to load billing plans (${plansResponse.status}).`);
      return;
    }
    const plansPayload = await responseJson<{ plans: Plan[] }>(plansResponse);

    const subscriptionsResponse = await fetch('/api/billing/subscriptions', { cache: 'no-store' });
    if (!subscriptionsResponse.ok) {
      setView(subscriptionsResponse.status === 401 ? 'SIGNED_OUT' : 'ERROR');
      setMessage(subscriptionsResponse.status === 401 ? '' : `Unable to load subscriptions (${subscriptionsResponse.status}).`);
      return;
    }
    const subscriptionsPayload = await responseJson<{ subscriptions: Subscription[] }>(subscriptionsResponse);

    const entitlementsResponse = await fetch('/api/account/entitlements', { cache: 'no-store' });
    if (!entitlementsResponse.ok) {
      setView(entitlementsResponse.status === 401 ? 'SIGNED_OUT' : 'ERROR');
      setMessage(entitlementsResponse.status === 401 ? '' : `Unable to load entitlements (${entitlementsResponse.status}).`);
      return;
    }
    const entitlementsPayload = await responseJson<{ entitlements: Entitlement[] }>(entitlementsResponse);

    setPlans(plansPayload?.plans ?? []);
    setSubscriptions(subscriptionsPayload?.subscriptions ?? []);
    setEntitlements(entitlementsPayload?.entitlements ?? []);
    setView('READY');
  }, []);

  useEffect(() => {
    void loadAccount();
  }, [loadAccount]);

  const activePlanCodes = useMemo(() => new Set(
    subscriptions
      .filter(item => !['CANCELED', 'EXPIRED'].includes(item.status))
      .map(item => item.plan_code),
  ), [subscriptions]);

  async function authenticate(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    try {
      const response = await fetch(`/api/session/${mode}`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const payload = await responseJson<{ error?: string; code?: string }>(response);
      if (!response.ok) {
        setMessage(payload?.code ?? payload?.error ?? `Authentication failed (${response.status}).`);
        setView('SIGNED_OUT');
        return;
      }
      setPassword('');
      await loadAccount();
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    setBusy(true);
    try {
      await fetch('/api/session/logout', { method: 'POST' });
      setPlans([]);
      setSubscriptions([]);
      setEntitlements([]);
      setView('SIGNED_OUT');
      setMessage('Session cleared.');
    } finally {
      setBusy(false);
    }
  }

  async function createSubscription(planCode: string) {
    setBusy(true);
    setMessage('');
    try {
      const response = await fetch('/api/billing/subscriptions', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ plan_code: planCode }),
      });
      const payload = await responseJson<{ error?: string; code?: string }>(response);
      if (!response.ok) {
        setMessage(payload?.code ?? payload?.error ?? `Subscription intent failed (${response.status}).`);
        return;
      }
      await loadAccount();
      setMessage('Subscription intent recorded. Activation remains provider-confirmed and server-authoritative.');
    } finally {
      setBusy(false);
    }
  }

  if (view === 'CHECKING') {
    return <article className="card account-panel"><div className="label">ACCOUNT CONTROL</div><p className="muted">Checking secure Web session…</p></article>;
  }

  if (view === 'SIGNED_OUT') {
    return (
      <article className="card account-panel" aria-label="SENTINEL account sign in">
        <div className="panel-heading">
          <div><div className="label">ACCOUNT CONTROL</div><h2>{mode === 'login' ? 'Sign in' : 'Create account'}</h2></div>
          <span className="badge">HTTPONLY SESSION</span>
        </div>
        <form onSubmit={authenticate}>
          <label className="field-label">EMAIL<input type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} required /></label>
          <label className="field-label">PASSWORD<input type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={12} value={password} onChange={event => setPassword(event.target.value)} required /></label>
          <button className="btn" disabled={busy}>{busy ? 'WORKING…' : mode === 'login' ? 'SIGN IN' : 'REGISTER'}</button>
        </form>
        <button className="text-btn" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setMessage(''); }} disabled={busy}>
          {mode === 'login' ? 'Need an account? Register' : 'Already registered? Sign in'}
        </button>
        {message && <p className="status-message" role="status">{message}</p>}
        <p className="boundary-copy">Credentials are sent only to the same-origin Web control plane. Core access and refresh tokens are never exposed to client-side JavaScript.</p>
      </article>
    );
  }

  if (view === 'ERROR') {
    return (
      <article className="card account-panel" aria-label="SENTINEL account control unavailable">
        <div className="panel-heading"><div><div className="label">ACCOUNT CONTROL</div><h2>Control data unavailable</h2></div><span className="badge">FAIL-CLOSED</span></div>
        <p className="status-message" role="status">{message || 'Core account data could not be verified.'}</p>
        <div className="button-row"><button className="ghost-btn" onClick={() => void loadAccount()} disabled={busy}>RETRY</button><button className="text-btn" onClick={() => void logout()} disabled={busy}>CLEAR SESSION</button></div>
      </article>
    );
  }

  return (
    <div className="account-stack">
      <article className="card account-panel">
        <div className="panel-heading">
          <div><div className="label">ACCOUNT CONTROL</div><h2>Subscription & entitlement state</h2></div>
          <button className="ghost-btn" onClick={logout} disabled={busy}>SIGN OUT</button>
        </div>
        {message && <p className="status-message" role="status">{message}</p>}
        <div className="account-metrics">
          <div><span className="label">SESSION</span><strong className="ok">AUTHENTICATED</strong></div>
          <div><span className="label">SUBSCRIPTIONS</span><strong>{subscriptions.length}</strong></div>
          <div><span className="label">ENTITLEMENTS</span><strong>{entitlements.length}</strong></div>
        </div>
      </article>

      <section className="section billing-section">
        <article className="card">
          <div className="label">PLANS</div>
          {plans.length === 0 && <p className="muted">No plans returned by Core.</p>}
          {plans.map(plan => {
            const hasOpenIntent = activePlanCodes.has(plan.code);
            return <div className="item plan-row" key={plan.code}>
              <div><strong>{plan.name}</strong><div className="muted">{money(plan)} / {plan.interval_days} days · {plan.entitlement_codes.join(' + ')}</div></div>
              <button className="ghost-btn" disabled={busy || hasOpenIntent} onClick={() => void createSubscription(plan.code)}>{hasOpenIntent ? 'INTENT EXISTS' : 'CREATE INTENT'}</button>
            </div>;
          })}
          <p className="boundary-copy">Creating an intent does not charge a payment method. Paid activation remains pending until a configured provider produces a verified lifecycle event.</p>
        </article>

        <article className="card">
          <div className="label">SUBSCRIPTIONS</div>
          {subscriptions.length === 0 && <p className="muted">No subscription lifecycle records.</p>}
          {subscriptions.map(item => <div className="item" key={item.id}>
            <div className="row-between"><strong>{item.plan_code}</strong><span className={`state state-${item.status.toLowerCase()}`}>{item.status}</span></div>
            <div className="muted">{lifecycleText(item.status)}</div>
            <div className="microcopy">Provider: {item.provider} · Updated {new Date(item.updated_at).toLocaleString()}</div>
          </div>)}
        </article>
      </section>

      <article className="card entitlement-card">
        <div className="label">GAME ENTITLEMENTS</div>
        {entitlements.length === 0 && <p className="muted">No server-authoritative game entitlements.</p>}
        {entitlements.map(item => <div className="item" key={item.id}>
          <div className="row-between"><strong>{item.game_name}</strong><span className="state">{item.status}</span></div>
          <div className="muted">{item.platform} · {item.game_id}</div>
          <div className="microcopy">Source: {item.source} · Valid until {new Date(item.valid_until).toLocaleString()}</div>
        </div>)}
      </article>
    </div>
  );
}
