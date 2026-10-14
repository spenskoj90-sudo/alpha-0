import { test, expect } from '@playwright/test';

/** Browser UI contract only: all Core responses are mocked, never real delivery evidence. */
test('signed-in email verification is scoped, cancellable and read back from account security', async ({ page }) => {
  let signedIn = false;
  let verified = false;
  let requests = 0;
  let confirmations = 0;

  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    const respond = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
    const path = url.pathname;
    if (path === '/api/session/login') { signedIn = true; return respond(200, {}); }
    if (path === '/api/billing/plans') return signedIn ? respond(200, { plans: [] }) : respond(401, {});
    if (path === '/api/billing/subscriptions') return respond(200, { subscriptions: [] });
    if (path === '/api/account/entitlements') return respond(200, { entitlements: [] });
    if (path === '/api/account/security') return respond(200, {
      email: 'owner@example.invalid', email_verified: verified, password_enabled: true,
      mfa_enabled: true, mfa_recovery_codes_remaining: 4, providers: [],
    });
    if (path === '/api/games') return respond(200, { games: [] });
    if (path === '/api/game-capabilities') return respond(200, { schema_version: 1, profiles: [] });
    if (path === '/api/devices') return respond(200, { devices: [], truncated: false });
    if (path === '/api/activity') return respond(200, { events: [] });
    if (path === '/api/session/email-verification/request') {
      requests++;
      expect(route.request().postDataJSON()).toEqual({ email: 'owner@example.invalid' });
      return respond(202, { status: 'ACCEPTED' });
    }
    if (path === '/api/session/email-verification/confirm') {
      confirmations++;
      expect(route.request().postDataJSON()).toEqual({ email: 'owner@example.invalid', token: '12345678' });
      verified = true;
      return respond(200, { status: 'VERIFIED' });
    }
    return respond(404, { error: 'NOT_MOCKED' });
  });

  await page.goto('/');
  await page.getByLabel('Email', { exact: true }).fill('owner@example.invalid');
  await page.getByLabel('Password', { exact: true }).fill('A-long-example-password-123');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const security = page.locator('#security');
  await expect(security.getByRole('button', { name: 'Verify account email' })).toBeVisible();
  await expect(security).toContainText('a Web login alone cannot authorize');
  await security.getByRole('button', { name: 'Verify account email' }).click();
  await expect(security.getByLabel('Email', { exact: true })).toBeDisabled();
  await security.getByRole('button', { name: 'Back to security' }).click();
  expect(requests).toBe(0);
  await security.getByRole('button', { name: 'Verify account email' }).click();
  await security.getByRole('button', { name: 'Request verification email' }).click();
  await expect(security.getByLabel('Verification code')).toBeVisible();
  await security.getByLabel('Verification code').fill('12345678');
  await security.getByRole('button', { name: 'Confirm email' }).click();
  await expect(security).toContainText('Verified');
  await expect(security.getByRole('button', { name: 'Verify account email' })).toHaveCount(0);
  expect(requests).toBe(1);
  expect(confirmations).toBe(1);
});
