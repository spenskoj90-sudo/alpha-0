import { test, expect, type Page } from '@playwright/test';
import { coreSetupPost, redactSensitiveOperation } from '../test-support/core-setup';
import { randomUUID, generateKeyPairSync, createHash } from 'node:crypto';

const staging = process.env.SENTINEL_BROWSER_TARGET === 'staging';
const publicSite = staging ? 'https://sentinel-public-site-staging.onrender.com' : 'http://127.0.0.1:3001';

async function geometry(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  expect(await page.locator('img').evaluateAll(images => images.every(image => (image as HTMLImageElement).complete && (image as HTMLImageElement).naturalWidth > 0))).toBe(true);
}

async function contrast(page: Page, selector: string) {
  const ratio = await page.locator(selector).first().evaluate(el => {
    const style = getComputedStyle(el);
    const luminance = (color: string) => {
      const channels = color.match(/[\d.]+/g)!.slice(0, 3).map(Number).map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
      return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2];
    };
    const a = luminance(style.color), b = luminance(style.backgroundColor);
    return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
  });
  expect(ratio).toBeGreaterThanOrEqual(4.5);
}

test('Web layout, focus, navigation, assets and action contrast', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.name));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await geometry(page);
  await contrast(page, '.btn');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to main content' })).toBeFocused();
  expect(await page.getByRole('link', { name: 'Skip to main content' }).evaluate(el => getComputedStyle(el).outlineStyle)).not.toBe('none');
  await page.keyboard.press('Enter');
  await expect(page.locator('#main-content')).toBeFocused();
  await page.getByRole('link', { name: 'Games', exact: true }).click();
  await expect(page.locator('#games')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Games', exact: true })).toHaveAttribute('aria-current', 'location');
  await expect(page.getByRole('link', { name: 'Overview', exact: true })).not.toHaveAttribute('aria-current', 'location');
  await page.goBack();
  await expect(page.getByRole('link', { name: 'Overview', exact: true })).toHaveAttribute('aria-current', 'location');
  expect(errors).toEqual([]);
});

test('Russian Web navigation, recovery, errors and language preference remain usable', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('combobox', { name: 'Interface language' }).selectOption('ru');
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
  await expect(page.getByRole('heading', { name: 'Войти', exact: true })).toBeVisible();
  await geometry(page);
  await page.getByRole('link', { name: 'Игры', exact: true }).click();
  await expect(page.getByRole('link', { name: 'Игры', exact: true })).toHaveAttribute('aria-current', 'location');
  await page.getByRole('button', { name: 'Забыли пароль?' }).click();
  await expect(page.getByRole('heading', { name: 'Восстановить доступ' })).toBeVisible();
  await expect(page.getByLabel('Email для восстановления')).toBeVisible();
  await page.getByRole('button', { name: 'У меня уже есть код восстановления' }).click();
  await expect(page.getByLabel('Код восстановления')).toBeVisible();
  await geometry(page);
  await page.reload();
  await expect(page.getByRole('combobox', { name: 'Язык интерфейса' })).toHaveValue('ru');
  await page.goto('/admin');
  await expect(page.getByRole('tab', { name: 'Каталог', exact: true })).toBeVisible();
  await page.getByRole('tab', { name: 'Качество', exact: true }).click();
  await expect(page.getByRole('tab', { name: 'Качество', exact: true })).toHaveAttribute('aria-selected', 'true');
  await geometry(page);
});

test('Russian public routes preserve truthful release states and language across navigation', async ({ page }) => {
  await page.goto(publicSite);
  await page.getByRole('button', { name: 'Русский', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
  await geometry(page);
  for (const route of ['/security', '/privacy', '/status']) {
    await page.goto(publicSite + route);
    await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
    await expect(page.getByRole('button', { name: 'Русский', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('main')).toContainText(/[А-Яа-яЁё]/);
    await geometry(page);
  }
  await page.getByRole('button', { name: 'English', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
});

test('Web language selection works when browser storage is unavailable', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'localStorage', { get() { throw new DOMException('Storage blocked', 'SecurityError'); } });
  });
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.name));
  await page.goto('/');
  await page.getByRole('combobox', { name: 'Interface language' }).selectOption('ru');
  await expect(page.getByRole('heading', { name: 'Войти', exact: true })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
  const appearance = page.locator('#settings').getByRole('button', { name: /Переключить тему/ });
  await appearance.click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  expect(errors).toEqual([]);
});

test('Settings persist appearance and Support exposes safe diagnostics', async ({ page }) => {
  await page.goto('/');
  const control = page.locator('#settings').getByRole('button', { name: /Switch appearance/ });
  await control.click();
  await expect(control).toHaveAccessibleName('Switch appearance. Current mode: Dark');
  await control.click();
  await expect(control).toHaveAccessibleName('Switch appearance. Current mode: Light');
  await page.reload();
  await expect(page.locator('#settings').getByRole('button', { name: /Switch appearance/ })).toHaveAccessibleName('Switch appearance. Current mode: Light');
  const download = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download Web build diagnostics' }).click();
  expect((await download).suggestedFilename()).toBe('sentinel-web-diagnostics.json');
});

test('password recovery has truthful request, invalid code, retry and completion states', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Forgot password?' }).click();
  await expect(page.getByRole('heading', { name: 'Recover account' })).toBeVisible();
  await geometry(page);
  await page.getByLabel('Recovery email', { exact: true }).fill(`unknown-${randomUUID()}@example.invalid`);
  await page.route('**/api/session/password-reset/request', route => route.abort('failed'));
  await page.getByRole('button', { name: 'Send recovery email' }).click();
  await expect(page.locator('#account [role="alert"]')).toContainText('Connection interrupted');
  await page.unroute('**/api/session/password-reset/request');
  await page.getByRole('button', { name: 'Send recovery email' }).click();
  await expect(page.locator('#account [role="status"]')).toContainText('If an eligible account exists');
  await page.getByLabel('Recovery code', { exact: true }).fill('invalid-' + 'x'.repeat(40));
  await redactSensitiveOperation(() => page.getByLabel('New password', { exact: true }).fill('Disposable-test-password-123'));
  await redactSensitiveOperation(() => page.getByLabel('Confirm new password', { exact: true }).fill('Different-test-password-123'));
  await page.getByRole('button', { name: 'Update password' }).click();
  await expect(page.locator('#account [role="alert"]')).toContainText('Passwords do not match');
  await redactSensitiveOperation(() => page.getByLabel('Confirm new password', { exact: true }).fill('Disposable-test-password-123'));
  await page.getByRole('button', { name: 'Update password' }).click();
  await expect(page.locator('#account [role="alert"]')).toContainText('invalid or expired');
  expect(await page.getByLabel('New password', { exact: true }).inputValue()).toBe('');
  // Whole numeric-code paste and completion UI fixture; no real delivery claim.
  await page.getByLabel('Recovery code', { exact: true }).fill('0000 1234');
  await expect(page.getByLabel('Recovery code', { exact: true })).toHaveValue('00001234');
  await expect(page.getByLabel('Recovery code', { exact: true })).toHaveAttribute('inputmode', 'numeric');
  await expect(page.getByLabel('Recovery code', { exact: true })).toHaveAttribute('autocomplete', 'one-time-code');
  await page.route('**/api/session/password-reset/confirm', route => route.fulfill({ status: 200, json: { status: 'PASSWORD_UPDATED' } }));
  await redactSensitiveOperation(() => page.getByLabel('New password', { exact: true }).fill('Disposable-test-password-123'));
  await redactSensitiveOperation(() => page.getByLabel('Confirm new password', { exact: true }).fill('Disposable-test-password-123'));
  await page.getByRole('button', { name: 'Update password' }).click();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await expect(page.locator('#account [role="status"]')).toContainText('Password updated');
  expect(await page.getByLabel('Password', { exact: true }).inputValue()).toBe('');
  expect(new URL(page.url()).search).toBe('');
  expect(await page.evaluate(() => [...Object.keys(localStorage), ...Object.keys(sessionStorage)].some(key => /token|password|recovery/i.test(key)))).toBe(false);
});

test('Public Site routes, responsive layout, assets and action contrast', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.name));
  await page.goto(publicSite);
  await geometry(page);
  await contrast(page, '.button-primary');
  for (const route of ['security', 'status', 'privacy']) {
    const response = await page.goto(`${publicSite}/${route}`);
    expect(response?.status()).toBe(200);
    await expect(page.locator('main')).toBeVisible();
    await geometry(page);
  }
  expect(errors).toEqual([]);
});

test('simulated offline account recovery and malformed successful data', async ({ page }) => {
  await page.route('**/api/billing/plans', route => route.abort('failed'));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Control data unavailable' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Retry', exact: true })).toBeEnabled();
  await page.unroute('**/api/billing/plans');
  await page.getByRole('button', { name: 'Retry', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await page.route('**/api/billing/**', route => route.fulfill({ status: 200, json: {} }));
  await page.route('**/api/account/entitlements', route => route.fulfill({ status: 200, json: {} }));
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Control data unavailable' })).toBeVisible();
  await expect(page.locator('#account [role="alert"]')).toContainText('Account data could not be verified');
});

test('real registration, invalid login, persistent HttpOnly session, product data and logout', async ({ page, context }, info) => {
  test.skip(info.project.name !== 'desktop-dark', 'One disposable account per run; layout covers all themes/viewports.');
  const email = `browser-${randomUUID()}@example.invalid`;
  const password = `Browser-${randomUUID()}-A1!`;
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await redactSensitiveOperation(() => page.getByLabel('Email', { exact: true }).fill(email));
  await redactSensitiveOperation(() => page.getByLabel('Password', { exact: true }).fill(password));
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.locator('#account [role="alert"]')).toContainText('INVALID_CREDENTIALS');
  await page.getByRole('button', { name: 'Need an account? Register' }).click();
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByText('AUTHENTICATED', { exact: true })).toBeVisible();
  await expect(page.locator('#games')).toContainText('Diablo IV');
  await expect(page.locator('#security')).toContainText('Verification pending');
  await expect(page.locator('#activity')).toContainText('auth:register');
  await expect(page.locator('#devices')).toContainText('No devices are registered');
  const cookies = (await context.cookies()).filter(cookie => cookie.name.startsWith('sentinel_'));
  // Assert only metadata; never attach cookie values to evidence.
  expect(cookies.length).toBeGreaterThanOrEqual(2);
  expect(cookies.every(cookie => cookie.httpOnly && cookie.sameSite === 'Strict' && (!staging || cookie.secure))).toBe(true);
  expect(await page.evaluate(() => document.cookie.includes('sentinel_'))).toBe(false);
  await page.reload();
  await expect(page.getByText('AUTHENTICATED', { exact: true })).toBeVisible();
  await expect(page.locator('#games')).toContainText('Diablo IV');
  // A still-valid HttpOnly session must not become a signed-out claim on outage.
  await page.route('**/api/billing/plans', route => route.fulfill({ status: 503, json: {} }));
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Control data unavailable' })).toBeVisible();
  await expect(page.locator('#security')).toContainText('Account data is unavailable');
  await expect(page.getByRole('article', { name: 'SENTINEL recommendation' })).toContainText('Account data is unavailable');
  await expect(page.locator('#security')).not.toContainText('Sign in to view');
  expect((await context.cookies()).filter(cookie => cookie.name.startsWith('sentinel_')).length).toBeGreaterThanOrEqual(2);
  await page.unroute('**/api/billing/plans');
  await page.getByRole('button', { name: 'Retry', exact: true }).click();
  await expect(page.getByText('AUTHENTICATED', { exact: true })).toBeVisible();
  await expect(page.locator('#games')).toContainText('Diablo IV');
  await page.route('**/api/intelligence/recommendations', route => route.fulfill({ status: 200, json: {
    recommendations: [{ kind: 'fact', text: 'Disposable account observation', confidence: 1, provenance: ['browser-test-fixture'], provider_id: null, model_id: null }],
  } }));
  await page.getByRole('button', { name: 'Load live', exact: true }).click();
  await expect(page.getByText('Disposable account observation', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await expect(page.locator('#security')).toContainText('Sign in to view');
  await expect(page.getByText('Disposable account observation', { exact: true })).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
});

test('MFA challenge, invalid code and recovery completion through Web', async ({ page }, info) => {
  test.skip(info.project.name !== 'desktop-dark', 'One disposable MFA account per run.');
  const core = staging ? 'https://sentinel-core-staging.onrender.com' : 'http://127.0.0.1:8000';
  const email = `browser-mfa-${randomUUID()}@example.invalid`;
  const password = `Browser-${randomUUID()}-A1!`;
  const registered = await coreSetupPost(`${core}/v1/auth/register`, { email, password });
  expect(registered.status).toBe(200);
  const token = registered.data.session_token;
  expect(typeof token).toBe('string');
  const { publicKey } = generateKeyPairSync('ec', { namedCurve: 'prime256v1' });
  const der = publicKey.export({ type: 'spki', format: 'der' });
  const bound = await coreSetupPost(`${core}/v1/devices/bind`, {
    platform: 'android', public_key_der_b64: der.toString('base64'), fingerprint_sha256: createHash('sha256').update(der).digest('hex'),
  }, token);
  expect(bound.status).toBe(200);
  const enrolled = await coreSetupPost(`${core}/v1/account/mfa/totp/enroll`, {}, token);
  expect(enrolled.status).toBe(200);
  expect(typeof enrolled.data.secret).toBe('string');
  const secret = enrolled.data.secret!;
  const { createHmac } = await import('node:crypto');
  let bits = '', key = '';
  for (const char of secret) bits += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'.indexOf(char).toString(2).padStart(5, '0');
  for (let i = 0; i + 8 <= bits.length; i += 8) key += String.fromCharCode(parseInt(bits.slice(i, i + 8), 2));
  const counter = Buffer.alloc(8); counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30_000)));
  const hash = createHmac('sha1', Buffer.from(key, 'latin1')).update(counter).digest();
  const offset = hash[19] & 15;
  const code = ((hash.readUInt32BE(offset) & 0x7fffffff) % 1_000_000).toString().padStart(6, '0');
  const confirmed = await coreSetupPost(`${core}/v1/account/mfa/totp/confirm`, { code }, token);
  expect(confirmed.status).toBe(200);
  expect(Array.isArray(confirmed.data.recovery_codes)).toBe(true);
  const recoveryCode = confirmed.data.recovery_codes![0];
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await redactSensitiveOperation(() => page.getByLabel('Email', { exact: true }).fill(email));
  await redactSensitiveOperation(() => page.getByLabel('Password', { exact: true }).fill(password));
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByLabel('Authenticator or recovery code')).toBeVisible();
  await redactSensitiveOperation(() => page.getByLabel('Authenticator or recovery code').fill('invalid-recovery-code'));
  await page.getByRole('button', { name: 'Verify MFA' }).click();
  await expect(page.locator('#account [role="alert"]')).toContainText('MFA_INVALID');
  await redactSensitiveOperation(() => page.getByLabel('Authenticator or recovery code').fill(recoveryCode));
  await page.getByRole('button', { name: 'Verify MFA' }).click();
  await expect(page.getByText('AUTHENTICATED', { exact: true })).toBeVisible();
  await expect(page.locator('#security')).toContainText('Enabled');
  await expect(page.locator('#devices')).toContainText('Registered');
  await expect(page.locator('#devices')).toContainText('android');
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
});
