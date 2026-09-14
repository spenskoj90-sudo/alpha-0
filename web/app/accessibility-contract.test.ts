import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const page = readFileSync(new URL('./page.tsx', import.meta.url), 'utf8');
const css = readFileSync(new URL('./globals.css', import.meta.url), 'utf8');
const recommendation = readFileSync(new URL('./components/recommendation-panel.tsx', import.meta.url), 'utf8');

describe('Web accessibility contract', () => {
  it('keeps skip navigation and a focusable main landmark', () => {
    expect(page).toContain('className="skip-link"');
    expect(page).toContain('href="#main-content"');
    expect(page).toContain('<main id="main-content"');
    expect(page).toContain('tabIndex={-1}');
    expect(page).toContain('<h1 className="brand">SENTINEL</h1>');
  });

  it('keeps keyboard focus visible including forced-colors mode', () => {
    expect(css).toContain(':focus-visible');
    expect(css).toContain('outline: 3px solid var(--accent-2)');
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
});
