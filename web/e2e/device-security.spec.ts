import { test, expect } from '@playwright/test';
import { randomUUID, generateKeyPairSync, createHash } from 'node:crypto';
import { coreSetupPost, redactSensitiveOperation } from '../test-support/core-setup';

test('owned device suspension confirms, survives reload and permits later revocation', async ({ page }, info) => {
  test.skip(info.project.name !== 'desktop-dark', 'One disposable account exercises server mutation; layout is covered separately.');
  const core = process.env.SENTINEL_BROWSER_TARGET === 'staging' ? 'https://sentinel-core-staging.onrender.com' : 'http://127.0.0.1:8000';
  const email = `browser-device-${randomUUID()}@example.invalid`;
  const password = `Browser-${randomUUID()}-A1!`;
  const registered = await coreSetupPost(`${core}/v1/auth/register`, { email, password });
  expect(registered.status).toBe(200);
  const { publicKey } = generateKeyPairSync('ec', { namedCurve: 'prime256v1' });
  const der = publicKey.export({ type: 'spki', format: 'der' });
  const bound = await coreSetupPost(`${core}/v1/devices/bind`, {
    platform: 'android', public_key_der_b64: der.toString('base64'), fingerprint_sha256: createHash('sha256').update(der).digest('hex'),
  }, registered.data.session_token);
  expect(bound.status).toBe(200);
  await page.goto('/');
  await redactSensitiveOperation(() => page.getByLabel('Email', { exact: true }).fill(email));
  await redactSensitiveOperation(() => page.getByLabel('Password', { exact: true }).fill(password));
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByText('AUTHENTICATED', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Suspend device', exact: true }).click({ timeout: 10_000 });
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.locator('#devices')).toContainText('Registered');
  await page.getByRole('button', { name: 'Suspend device', exact: true }).click();
  // A network failure must preserve the current readback and allow an explicit retry.
  await page.route('**/api/devices/*/suspend', route => route.abort());
  await page.getByRole('button', { name: 'Confirm suspension', exact: true }).click();
  await expect(page.locator('#devices [role="alert"]')).toContainText('Device suspension was not confirmed');
  await expect(page.locator('#devices')).toContainText('Registered');
  await page.unroute('**/api/devices/*/suspend');
  await page.getByRole('button', { name: 'Suspend device', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm suspension', exact: true }).click();
  await expect(page.locator('#devices')).toContainText('Suspended');
  await expect(page.getByRole('button', { name: 'Suspend device', exact: true })).toHaveCount(0);
  await page.reload();
  await expect(page.locator('#devices')).toContainText('Suspended');
  await page.getByRole('button', { name: 'Revoke device', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm revoke', exact: true }).click();
  await expect(page.locator('#devices')).toContainText('Revoked');
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.locator('#devices')).toContainText('Sign in to view');
  await expect(page.locator('#devices [role="alert"]')).toHaveCount(0);
});
