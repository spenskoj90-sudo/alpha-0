'use client';

import { FormEvent, useState } from 'react';
import { useLocale } from './locale-provider';

/** Verification does not authenticate or authorize game actions. */
export function EmailVerification({ initialEmail, onCancel, onComplete }: {
  initialEmail: string; onCancel: () => void; onComplete: () => void;
}) {
  const { t, locale } = useLocale();
  const [step, setStep] = useState<'request' | 'confirm'>('request');
  const [email, setEmail] = useState(initialEmail);
  const [token, setToken] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const code = token.replace(/\s/g, '');
    if (step === 'confirm' && !/^[0-9]{8}$/.test(code)) {
      setError(true); setMessage('Verification code invalid or expired.'); return;
    }
    setBusy(true); setMessage(''); setError(false);
    try {
      const response = await fetch('/api/session/email-verification/' + step, {
        method: 'POST', cache: 'no-store', signal: AbortSignal.timeout(45_000),
        headers: { 'content-type': 'application/json', 'accept-language': locale },
        body: JSON.stringify(step === 'request' ? { email } : { email, token: code }),
      });
      const payload = await response.json();
      if (response.status === 429) {
        setError(true); setMessage('Too many attempts. Retry later.'); return;
      }
      if (step === 'confirm' && response.status === 400 && payload?.error === 'AUTH_ACTION_TOKEN_INVALID') {
        setError(true); setMessage('Verification code invalid or expired.'); return;
      }
      if (step === 'request' && response.status === 202 && payload?.status === 'ACCEPTED') {
        setStep('confirm');
        setMessage('If your account is eligible and delivery is available, a verification email may arrive.');
        return;
      }
      if (step === 'confirm' && response.status === 200 && payload?.status === 'VERIFIED') {
        setToken(''); onComplete(); return;
      }
      setError(true); setMessage('Email verification unavailable. Retry later.');
    } catch {
      setError(true); setMessage('Email verification unavailable. Retry later.');
    } finally {
      setBusy(false);
    }
  }

  return <div aria-busy={busy}>
    <form onSubmit={submit}>
      <label className="field-label">{t("Email")}
        <input type="email" autoComplete="email" maxLength={320} value={email}
          onChange={event => setEmail(event.target.value)} required disabled={busy} />
      </label>
      {step === 'confirm' && <>
        <p className="muted">{t("Enter the 8-digit email code. It expires after 15 minutes.")}</p>
        <label className="field-label">{t("Verification code")}
          <input type="text" inputMode="numeric" autoComplete="one-time-code"
            spellCheck={false} pattern="[0-9]{8}" minLength={8} maxLength={8}
            value={token} onChange={event => setToken(event.target.value.replace(/\s/g, ''))}
            required disabled={busy} />
        </label>
      </>}
      <button className="btn" disabled={busy}>
        {busy ? t("Working…") : step === 'request' ? t("Request verification email") : t("Confirm email")}
      </button>
    </form>
    {message && <p className="status-message" role={error ? 'alert' : 'status'}
      aria-live={error ? 'assertive' : 'polite'}>{t(message)}</p>}
    <div className="recovery-actions">
      <button type="button" className="text-btn" disabled={busy} onClick={() => {
        setStep(step === 'request' ? 'confirm' : 'request');
        setToken(''); setError(false); setMessage('');
      }}>{step === 'request' ? t("I already have a verification code") : t("Request another code")}</button>
      <button type="button" className="text-btn" disabled={busy} onClick={onCancel}>{t("Back to sign in")}</button>
    </div>
  </div>;
}
