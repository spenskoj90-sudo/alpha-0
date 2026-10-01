'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useLocale } from './locale-provider';
import { PasswordRecovery } from './password-recovery';

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
type MessageTone = 'status' | 'error';

type AccountSnapshot =
  | { view: 'SIGNED_OUT'; message?: string }
  | { view: 'ERROR'; message: string }
  | { view: 'READY'; plans: Plan[]; subscriptions: Subscription[]; entitlements: Entitlement[] };

type CheckoutResponse = {
  checkout_url?: unknown;
  checkout_session_id?: unknown;
  subscription_id?: unknown;
  livemode?: unknown;
  error?: string;
  code?: string;
};

function lifecycleText(status: Subscription['status']) {
  switch (status) {
    case 'PENDING': return 'Awaiting provider confirmation';
    case 'ACTIVE': return 'Active';
    case 'PAST_DUE': return 'Payment issue — server policy remains authoritative';
    case 'CANCELED': return 'Canceled';
    case 'EXPIRED': return 'Expired';
  }
}

function money(plan: Plan, locale: string) {
  return new Intl.NumberFormat(locale, { style: 'currency', currency: plan.currency }).format(plan.amount_minor / 100);
}

async function responseJson<T>(response: Response): Promise<T | null> {
  try {
    return await response.json() as T;
  } catch {
    return null;
  }
}

function verifiedCheckoutUrl(payload: CheckoutResponse | null): string | null {
  if (!payload || typeof payload.checkout_url !== 'string') return null;
  try {
    const url = new URL(payload.checkout_url);
    if (url.protocol !== 'https:' || url.username || url.password) return null;
    return url.toString();
  } catch {
    return null;
  }
}

export async function fetchAccountSnapshot(): Promise<AccountSnapshot> {
  try {
    const plansResponse = await fetch('/api/billing/plans', { cache: 'no-store', signal: AbortSignal.timeout(45_000) });
    if (plansResponse.status === 401) return { view: 'SIGNED_OUT' };
    if (!plansResponse.ok) return { view: 'ERROR', message: `Unable to load billing plans (${plansResponse.status}).` };
    const plansPayload = await responseJson<{ plans: Plan[] }>(plansResponse);

    const subscriptionsResponse = await fetch('/api/billing/subscriptions', { cache: 'no-store', signal: AbortSignal.timeout(45_000) });
    if (subscriptionsResponse.status === 401) return { view: 'SIGNED_OUT' };
    if (!subscriptionsResponse.ok) return { view: 'ERROR', message: `Unable to load subscriptions (${subscriptionsResponse.status}).` };
    const subscriptionsPayload = await responseJson<{ subscriptions: Subscription[] }>(subscriptionsResponse);

    const entitlementsResponse = await fetch('/api/account/entitlements', { cache: 'no-store', signal: AbortSignal.timeout(45_000) });
    if (entitlementsResponse.status === 401) return { view: 'SIGNED_OUT' };
    if (!entitlementsResponse.ok) return { view: 'ERROR', message: `Unable to load entitlements (${entitlementsResponse.status}).` };
    const entitlementsPayload = await responseJson<{ entitlements: Entitlement[] }>(entitlementsResponse);

    if (!Array.isArray(plansPayload?.plans) || !Array.isArray(subscriptionsPayload?.subscriptions) || !Array.isArray(entitlementsPayload?.entitlements)) {
      return { view: 'ERROR', message: 'Account data could not be verified. Please retry.' };
    }
    const validPlans = plansPayload.plans.every(plan => plan &&
      typeof plan.code === 'string' && typeof plan.name === 'string' && /^[A-Z]{3}$/.test(plan.currency) &&
      Number.isSafeInteger(plan.amount_minor) && plan.amount_minor >= 0 &&
      Number.isSafeInteger(plan.interval_days) && plan.interval_days > 0 &&
      Array.isArray(plan.entitlement_codes) && plan.entitlement_codes.every(code => typeof code === 'string'));
    const validSubscriptions = subscriptionsPayload.subscriptions.every(item => item &&
      typeof item.id === 'string' && typeof item.plan_code === 'string' && typeof item.provider === 'string' &&
      ['PENDING', 'ACTIVE', 'PAST_DUE', 'CANCELED', 'EXPIRED'].includes(item.status) &&
      typeof item.updated_at === 'string' && Number.isFinite(Date.parse(item.updated_at)));
    const validEntitlements = entitlementsPayload.entitlements.every(item => item &&
      ['id', 'game_id', 'game_name', 'platform', 'status', 'source', 'valid_until'].every(key => typeof item[key as keyof Entitlement] === 'string') &&
      Number.isFinite(Date.parse(item.valid_until)));
    if (!validPlans || !validSubscriptions || !validEntitlements) {
      return { view: 'ERROR', message: 'Account data could not be verified. Please retry.' };
    }

    return {
      view: 'READY',
      plans: plansPayload?.plans ?? [],
      subscriptions: subscriptionsPayload?.subscriptions ?? [],
      entitlements: entitlementsPayload?.entitlements ?? [],
    };
  } catch {
    return { view: 'ERROR', message: 'Connection interrupted. Check your network and retry.' };
  }
}

export function AccountControl() {
  const { t, locale } = useLocale();
  const [view, setView] = useState<ViewState>('CHECKING');
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [recovering, setRecovering] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaRequired, setMfaRequired] = useState(false);
  const [mfaCode, setMfaCode] = useState('');
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [entitlements, setEntitlements] = useState<Entitlement[]>([]);
  const [message, setMessage] = useState('');
  const [messageTone, setMessageTone] = useState<MessageTone>('status');
  const [busy, setBusy] = useState(false);

  function applySnapshot(snapshot: AccountSnapshot) {
    if (snapshot.view === 'READY') {
      setPlans(snapshot.plans);
      setSubscriptions(snapshot.subscriptions);
      setEntitlements(snapshot.entitlements);
      setMessage('');
      setMessageTone('status');
      setView('READY');
      window.dispatchEvent(new CustomEvent('sentinel-session-changed', { detail: true }));
      return;
    }
    setPlans([]);
    setSubscriptions([]);
    setEntitlements([]);
    setMessage(snapshot.message ?? '');
    setMessageTone(snapshot.view === 'ERROR' ? 'error' : 'status');
    setView(snapshot.view);
    window.dispatchEvent(new CustomEvent('sentinel-session-changed', { detail: snapshot.view === 'ERROR' ? null : false }));
  }

  async function reloadAccount() {
    applySnapshot(await fetchAccountSnapshot());
  }

  useEffect(() => {
    let active = true;
    void fetchAccountSnapshot().then(snapshot => {
      if (!active) return;
      if (snapshot.view === 'READY') {
        setPlans(snapshot.plans);
        setSubscriptions(snapshot.subscriptions);
        setEntitlements(snapshot.entitlements);
        setMessage('');
        setMessageTone('status');
        setView('READY');
        window.dispatchEvent(new CustomEvent('sentinel-session-changed', { detail: true }));
        return;
      }
      setPlans([]);
      setSubscriptions([]);
      setEntitlements([]);
      setMessage(snapshot.message ?? '');
      setMessageTone(snapshot.view === 'ERROR' ? 'error' : 'status');
      setView(snapshot.view);
      window.dispatchEvent(new CustomEvent('sentinel-session-changed', { detail: snapshot.view === 'ERROR' ? null : false }));
    });
    return () => { active = false; };
  }, []);

  const activePlanCodes = useMemo(() => new Set(
    subscriptions
      .filter(item => !['CANCELED', 'EXPIRED'].includes(item.status))
      .map(item => item.plan_code),
  ), [subscriptions]);

  async function authenticate(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    setMessageTone('status');
    try {
      const response = await fetch(`/api/session/${mode}`, {
        method: 'POST',
        signal: AbortSignal.timeout(45_000),
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const payload = await responseJson<{ error?: string; code?: string; mfa_required?: boolean }>(response);
      if (!response.ok) {
        setMessage(payload?.code ?? payload?.error ?? `Authentication failed (${response.status}).`);
        setMessageTone('error');
        setView('SIGNED_OUT');
        return;
      }
      if (payload?.mfa_required === true) {
        setPassword('');
        setMfaRequired(true);
        setMfaCode('');
        setMessage('Second-factor verification required.');
        setMessageTone('status');
        setView('SIGNED_OUT');
        return;
      }
      setPassword('');
      await reloadAccount();
    } catch {
      setMessage('Connection interrupted. Check your network and retry.');
      setMessageTone('error');
    } finally {
      setBusy(false);
    }
  }

  async function completeMfa(event: FormEvent) {
    event.preventDefault();
    if (!mfaRequired || mfaCode.trim().length < 6) return;
    setBusy(true);
    setMessage('');
    try {
      const response = await fetch('/api/session/mfa', {
        method: 'POST',
        signal: AbortSignal.timeout(45_000),
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ code: mfaCode.trim() }),
      });
      const payload = await responseJson<{ error?: string; code?: string }>(response);
      if (!response.ok) {
        setMessage(payload?.code ?? payload?.error ?? `MFA verification failed (${response.status}).`);
        setMessageTone('error');
        return;
      }
      setMfaRequired(false);
      setMfaCode('');
      await reloadAccount();
    } catch {
      setMessage('Connection interrupted. Check your network and retry.');
      setMessageTone('error');
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    setBusy(true);
    try {
      const response = await fetch('/api/session/logout', { method: 'POST', signal: AbortSignal.timeout(45_000) });
      if (!response.ok) {
        setMessage('Sign out could not be confirmed. Please retry.');
        setMessageTone('error');
        return;
      }
      setPlans([]);
      setSubscriptions([]);
      setEntitlements([]);
      setMfaRequired(false);
      setMfaCode('');
      setView('SIGNED_OUT');
      window.dispatchEvent(new CustomEvent('sentinel-session-changed', { detail: false }));
      setMessage('Session cleared.');
      setMessageTone('status');
    } catch {
      setMessage('Connection interrupted. Check your network and retry.');
      setMessageTone('error');
    } finally {
      setBusy(false);
    }
  }

  async function createSubscription(plan: Plan) {
    setBusy(true);
    setMessage('');
    setMessageTone('status');
    try {
      if (plan.amount_minor > 0) {
        const response = await fetch('/api/billing/checkout-sessions', {
          method: 'POST',
          signal: AbortSignal.timeout(45_000),
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ plan_code: plan.code }),
        });
        const payload = await responseJson<CheckoutResponse>(response);
        if (!response.ok) {
          setMessage(payload?.code ?? payload?.error ?? `Checkout setup failed (${response.status}).`);
          setMessageTone('error');
          return;
        }
        const checkoutUrl = verifiedCheckoutUrl(payload);
        if (!checkoutUrl) {
          setMessage('INVALID_Checkout_RESPONSE');
          setMessageTone('error');
          return;
        }
        window.location.assign(checkoutUrl);
        return;
      }

      const response = await fetch('/api/billing/subscriptions', {
        method: 'POST',
        signal: AbortSignal.timeout(45_000),
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ plan_code: plan.code }),
      });
      const payload = await responseJson<{ error?: string; code?: string }>(response);
      if (!response.ok) {
        setMessage(payload?.code ?? payload?.error ?? `Subscription intent failed (${response.status}).`);
        setMessageTone('error');
        return;
      }
      await reloadAccount();
      setMessage('Free subscription intent recorded. Server policy remains authoritative.');
      setMessageTone('status');
    } catch {
      setMessage('Connection interrupted. Check your network and retry.');
      setMessageTone('error');
    } finally {
      setBusy(false);
    }
  }

  if (view === 'CHECKING') {
    return <article className="card account-panel" aria-busy="true"><div className="label">{t("Account")}</div><p className="muted" role="status" aria-live="polite">{t("Checking secure Web session…")}</p></article>;
  }

  if (view === 'SIGNED_OUT') {
    return (
      <article className="card account-panel auth-panel" aria-label={t("SENTINEL account sign in")} aria-busy={busy}>
        <div className="auth-intro">
          <div className="eyebrow">{t("YOUR SENTINEL ACCOUNT")}</div>
          <h3>{t("One secure place.")}<br />{t("A clearer view.")}</h3>
          <p className="muted">{t("Review your security, connected devices and intelligence with access you control.")}</p>
          <p className="auth-assurance">{t("Your session stays private. You decide what connects.")}</p>
        </div>
        <div className="auth-form">
        <div className="panel-heading">
          <div><div className="label">{t("Account")}</div><h2>{recovering ? t("Recover account") : mode === 'login' ? t("Sign in") : t("Create account")}</h2></div>
          <span className="badge">{t("Secure Web session")}</span>
        </div>
        {recovering ? <PasswordRecovery initialEmail={email} onCancel={() => { setRecovering(false); setMode('login'); setMessage(''); }} onComplete={() => {
          setRecovering(false); setMode('login'); setPassword(''); setMfaRequired(false); setMfaCode('');
          setMessage('Password updated. Sign in with your new password.'); setMessageTone('status');
          window.dispatchEvent(new CustomEvent('sentinel-session-changed', { detail: false }));
        }} /> : mfaRequired ? (
          <form onSubmit={completeMfa}>
            <label className="field-label">{t("Authenticator or recovery code")}{' '}<input
                type="text"
                autoComplete="one-time-code"
                value={mfaCode}
                onChange={event => setMfaCode(event.target.value)}
                required
              />
            </label>
            <div className="microcopy">{t("A session is issued only after this second factor succeeds.")}</div>
            <button className="btn" disabled={busy || mfaCode.trim().length < 6}>{busy ? t("Working…") : t("Verify MFA")}</button>
          </form>
        ) : (
          <>
            <form onSubmit={authenticate}>
              <label className="field-label">{t("Email")}<input type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} required /></label>
              <label className="field-label">{t("Password")}{' '}<input
                  type="password"
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  minLength={12}
                  aria-describedby="password-requirement"
                  value={password}
                  onChange={event => setPassword(event.target.value)}
                  required
                />
              </label>
              <div id="password-requirement" className="microcopy">{t("Minimum 12 characters.")}</div>
              <button className="btn" disabled={busy}>{busy ? t("Working…") : mode === 'login' ? t("Sign in") : t("Create account")}</button>
            </form>
            <button className="text-btn" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setMfaRequired(false); setMfaCode(''); setMessage(''); setMessageTone('status'); }} disabled={busy}>
              {mode === 'login' ? t("Need an account? Register") : t("Already registered? Sign in")}
            </button>
            {mode === 'login' && <button className="text-btn" disabled={busy} onClick={() => { setRecovering(true); setPassword(''); setMessage(''); }}>{t("Forgot password?")}</button>}
          </>
        )}
        {message && <p className="status-message" role={messageTone === 'error' ? 'alert' : 'status'} aria-live={messageTone === 'error' ? 'assertive' : 'polite'}>{t(message)}</p>}
        <p className="boundary-copy">{t("Your session is protected by secure cookies. Access tokens stay on the server.")}</p>
        </div>
      </article>
    );
  }

  if (view === 'ERROR') {
    return (
      <article className="card account-panel" aria-label={t("SENTINEL account control unavailable")} aria-busy={busy}>
        <div className="panel-heading"><div><div className="label">{t("Account")}</div><h2>{t("Control data unavailable")}</h2></div><span className="badge">{t("Fail-closed")}</span></div>
        <p className="status-message" role="alert" aria-live="assertive">{t(message) || t("Core account data could not be verified.")}</p>
        <div className="button-row"><button className="ghost-btn" onClick={async () => { setBusy(true); await reloadAccount(); setBusy(false); }} disabled={busy}>{t("Retry")}</button><button className="text-btn" onClick={() => void logout()} disabled={busy}>{t("Clear session")}</button></div>
      </article>
    );
  }

  return (
    <div className="account-stack" aria-busy={busy}>
      <article className="card account-panel">
        <div className="panel-heading">
          <div><div className="label">{t("Account")}</div><h2>{t("Access")}</h2></div>
          <button className="ghost-btn" onClick={logout} disabled={busy}>{t("Sign out")}</button>
        </div>
        {message && <p className="status-message" role={messageTone === 'error' ? 'alert' : 'status'} aria-live={messageTone === 'error' ? 'assertive' : 'polite'}>{t(message)}</p>}
        <div className="account-metrics">
          <div><span className="label">{t("Session")}</span><strong className="ok">{t("AUTHENTICATED")}</strong></div>
          <div><span className="label">{t("Subscriptions")}</span><strong>{subscriptions.length}</strong></div>
          <div><span className="label">{t("Entitlements")}</span><strong>{entitlements.length}</strong></div>
        </div>
      </article>

      <section id="access" className="section billing-section">
        <article className="card">
          <div className="label">{t("Plans")}</div>
          {plans.length === 0 && <p className="muted">{t("No plans returned by Core.")}</p>}
          {plans.map(plan => {
            const hasOpenIntent = activePlanCodes.has(plan.code);
            const paid = plan.amount_minor > 0;
            const actionLabel = hasOpenIntent ? `${plan.name}: ${t('Intent exists')}` : paid ? `${t('Start checkout for')} ${plan.name}` : `${t('Activate free plan')} ${plan.name}`;
            return <div className="item plan-row" key={plan.code}>
              <div><strong>{plan.name}</strong><div className="muted">{money(plan, locale)} / {plan.interval_days}{' '}{t("days ·")}{' '}{plan.entitlement_codes.join(' + ')}</div></div>
              <button className="ghost-btn" aria-label={actionLabel} disabled={busy || hasOpenIntent} onClick={() => void createSubscription(plan)}>{hasOpenIntent ? t("Intent exists") : paid ? t("Checkout") : t("Activate free")}</button>
            </div>;
          })}
          <p className="boundary-copy">{t("Paid checkout uses a server-created hosted provider session. The browser cannot select price IDs, provider mode, entitlement state, or payment confirmation. Paid features activate only after a verified provider lifecycle event.")}</p>
        </article>

        <article className="card">
          <div className="label">{t("Subscriptions")}</div>
          {subscriptions.length === 0 && <p className="muted">{t("No subscription lifecycle records.")}</p>}
          {subscriptions.map(item => <div className="item" key={item.id}>
            <div className="row-between"><strong>{item.plan_code}</strong><span className={`state state-${item.status.toLowerCase()}`}>{item.status}</span></div>
            <div className="muted">{t(lifecycleText(item.status))}</div>
            <div className="microcopy">{t("Provider:")}{' '}{item.provider}{' '}{t("· Updated")}{' '}{new Date(item.updated_at).toLocaleString(locale === 'ru' ? 'ru-RU' : 'en-US')}</div>
          </div>)}
        </article>
      </section>

      <article className="card entitlement-card">
        <div className="label">{t("GAME Entitlements")}</div>
        {entitlements.length === 0 && <p className="muted">{t("No server-authoritative game entitlements.")}</p>}
        {entitlements.map(item => <div className="item" key={item.id}>
          <div className="row-between"><strong>{item.game_name}</strong><span className="state">{item.status}</span></div>
          <div className="muted">{item.platform} · {item.game_id}</div>
          <div className="microcopy">{t("Source:")}{' '}{item.source}{' '}{t("· Valid until")}{' '}{new Date(item.valid_until).toLocaleString(locale === 'ru' ? 'ru-RU' : 'en-US')}</div>
        </div>)}
      </article>
    </div>
  );
}
