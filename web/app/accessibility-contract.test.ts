import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const page = readFileSync(new URL('./page.tsx', import.meta.url), 'utf8');
const css = readFileSync(new URL('./globals.css', import.meta.url), 'utf8');
const recommendation = readFileSync(new URL('./components/recommendation-panel.tsx', import.meta.url), 'utf8');
const accountControl = readFileSync(new URL('./components/account-control.tsx', import.meta.url), 'utf8');

describe('Web accessibility contract', () => {
  it('keeps skip navigation and a focusable main landmark', () => {
    expect(page).toContain('className="skip-link"');
    expect(page).toContain('href="#main-content"');
    expect(page).toContain('<main id="main-content"');
    expect(page).toContain('tabIndex={-1}');
    expect(page).toContain('className="side-nav"');
    expect(page).toContain('<BrandMark');
  });

  it('keeps keyboard focus visible including forced-colors mode', () => {
    expect(css).toContain(':focus-visible');
    expect(css).toContain('outline: 3px solid var(--accent-2)');
    expect(css).toContain('@media (prefers-reduced-motion: reduce)');
    expect(css).toContain('@media (forced-colors: active)');
    expect(css).toContain('.skip-link:focus-visible');
  });

  it('announces asynchronous recommendation state without changing authority boundaries', () => {
    expect(recommendation).toContain("aria-busy={view === 'LOADING'}");
    expect(recommendation).toContain('role={view === \'ERROR\' ? \'alert\' : \'status\'}');
    expect(recommendation).toContain("aria-live={view === 'ERROR' ? 'assertive' : 'polite'}");
    expect(recommendation).toContain('<div role="status" aria-live="polite" aria-atomic="true">');
    expect(recommendation).toContain('Observational only · no action execution');
  });

  it('exposes account busy, failure and password requirement semantics', () => {
    expect(accountControl).toContain('aria-busy={busy}');
    expect(accountControl).toContain('aria-busy="true"');
    expect(accountControl).toContain('aria-describedby="password-requirement"');
    expect(accountControl).toContain('id="password-requirement"');
    expect(accountControl).toContain("role={messageTone === 'error' ? 'alert' : 'status'}");
    expect(accountControl).toContain("aria-live={messageTone === 'error' ? 'assertive' : 'polite'}");
    expect(accountControl).toContain('role="alert" aria-live="assertive"');
  });

  it('keeps repeated plan actions uniquely named', () => {
    expect(accountControl).toContain('`Start checkout for ${plan.name}`');
    expect(accountControl).toContain('`Activate free plan ${plan.name}`');
    expect(accountControl).toContain('aria-label={actionLabel}');
  });
});
