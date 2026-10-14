import { test, expect } from '@playwright/test';

const base = process.env.SENTINEL_BROWSER_TARGET === 'staging'
  ? 'https://sentinel-public-site-staging.onrender.com' : 'http://127.0.0.1:3001';

test('public navigation exposes separate truthful pages in both languages', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(base);
  await page.getByRole('button', { name: 'English', exact: true }).click();
  await expect(page.locator('main > section')).toHaveCount(2);
  for (const route of ['features', 'games', 'modules', 'pricing', 'help', 'access']) {
    const link = page.locator(`header a[href="/${route}"], header a[href="/${route}/"]`);
    await expect(link).toBeVisible();
    await link.click();
    await expect(page).toHaveURL(new RegExp(`/${route}/?$`));
    await expect(page.locator('h1')).toHaveCount(1);
    await expect(page.locator(`header a[href="/${route}"], header a[href="/${route}/"]`)).toHaveAttribute('aria-current', 'page');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.getByRole('button', { name: 'Русский', exact: true }).click();
    await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
    await expect(page.locator('h1')).toContainText(/[А-Яа-яЁё]/);
    await page.reload();
    await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
    await page.getByRole('button', { name: 'English', exact: true }).click();
  }
  await page.goto(`${base}/games/`);
  await expect(page.locator('main')).toContainText('Calibration pending');
  await expect(page.locator('main')).toContainText('Research only');
  await expect(page.locator('main')).toContainText('Shattered Pixel Dungeon');
  await page.goto(`${base}/pricing/`);
  await expect(page.locator('main')).toContainText('Prices are not published');
  await page.goto(`${base}/access/`);
  await expect(page.getByRole('link', { name: 'Open staging account', exact: true })).toHaveAttribute('href', 'https://sentinel-web-staging-fxhn.onrender.com/#account');
  await expect(page.locator('input[type="password"]')).toHaveCount(0);
  expect(errors).toEqual([]);
});
