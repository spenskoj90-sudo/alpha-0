'use client';

import { FormEvent, useState } from 'react';
import { useLocale } from './locale-provider';

export function PasswordRecovery({ initialEmail, onCancel, onComplete }: {
  initialEmail: string; onCancel: () => void; onComplete: () => void;
}) {
  const { t, locale } = useLocale();
  const [step, setStep] = useState<'request' | 'confirm'>('request');
  const [email, setEmail] = useState(initialEmail);
  const [token, setToken] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (step === 'confirm' && password !== confirmation) {
      setMessage('Passwords do not match.'); setError(true); return;
    }
    setBusy(true); setMessage(''); setError(false);
    try {
      const response = await fetch(`/api/session/password-reset/${step}`, {
        method: 'POST', headers: { 'content-type': 'application/json', 'accept-language': locale },
        body: JSON.stringify(step === 'request' ? { email } : { email, token: token.replace(/\s/g, ''), password }),
        signal: AbortSignal.timeout(45_000), cache: 'no-store',
      });
      const payload = await response.json();
      if (!response.ok) {
        setError(true);
        setMessage(payload?.error === 'AUTH_ACTION_TOKEN_INVALID' ? 'This recovery code is invalid or expired. Request a new email.' :
          response.status === 429 ? 'Too many attempts. Please wait before trying again.' :
          payload?.error === 'RECOVERY_INPUT_INVALID' ? 'Check your email, recovery code and password requirements.' :
          'Recovery is unavailable right now. Please retry.');
        return;
      }
      if (step === 'request' && payload?.status === 'ACCEPTED') {
        setStep('confirm');
        setMessage('If an eligible account exists and email delivery is available, a recovery email will arrive.');
      } else if (step === 'confirm' && payload?.status === 'PASSWORD_UPDATED') {
        setToken(''); onComplete();
      } else {
        setError(true); setMessage('Recovery could not be confirmed. Please retry.');
      }
    } catch {
      setError(true); setMessage('Connection interrupted. Check your network and retry.');
    } finally {
      if (step === 'confirm') { setPassword(''); setConfirmation(''); }
      setBusy(false);
    }
  }

  return <div aria-busy={busy}>
    <form onSubmit={submit}>
      <label className="field-label">{t("Recovery email")}<input type="email" autoComplete="email" maxLength={320} value={email} onChange={event => setEmail(event.target.value)} required disabled={busy} /></label>
      {step === 'request' ? <>
        <p className="muted">{t("Enter your account email to request a recovery code.")}</p>
      </> : <>
        <p className="muted">{t("Paste the 8-digit code from your email. It expires after 15 minutes and is bound to this email address.")}</p>
        <label className="field-label">{t("Recovery code")}<input type="text" inputMode="numeric" autoComplete="one-time-code" spellCheck={false} autoCapitalize="none" minLength={8} pattern="[0-9]{8}|[A-Za-z0-9_-]{32,512}" maxLength={512} value={token} onChange={event => setToken(event.target.value.replace(/\s/g, ''))} required disabled={busy} /></label>
        <label className="field-label">{t("New password")}<input type="password" autoComplete="new-password" minLength={12} maxLength={256} aria-describedby="recovery-password-requirement" value={password} onChange={event => setPassword(event.target.value)} required disabled={busy} /></label>
        <label className="field-label">{t("Confirm new password")}<input type="password" autoComplete="new-password" minLength={12} maxLength={256} value={confirmation} onChange={event => setConfirmation(event.target.value)} required disabled={busy} /></label>
        <p id="recovery-password-requirement" className="microcopy">{t("12–256 characters. Updating your password ends existing sessions. MFA remains enabled if configured.")}</p>
      </>}
      <button className="btn" disabled={busy}>{busy ? t("Working…") : step === 'request' ? t("Send recovery email") : t("Update password")}</button>
    </form>
    {message && <p className="status-message" role={error ? 'alert' : 'status'} aria-live={error ? 'assertive' : 'polite'}>{t(message)}</p>}
    <div className="recovery-actions">
      <button className="text-btn" disabled={busy} onClick={() => { setStep(step === 'request' ? 'confirm' : 'request'); setToken(''); setPassword(''); setConfirmation(''); setMessage(''); setError(false); }}>{step === 'request' ? t("I already have a recovery code") : t("Request a new email")}</button>
      <button className="text-btn" disabled={busy} onClick={onCancel}>{t("Back to sign in")}</button>
    </div>
  </div>;
}
