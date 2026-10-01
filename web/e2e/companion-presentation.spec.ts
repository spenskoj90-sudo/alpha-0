import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const launcher = resolve(process.cwd(), '../launcher');

// Real renderer markup and accessibility script, isolated from Electron IPC.
// These checks establish presentation behavior, not Windows-host acceptance.
test('Companion rendered brand and section selection follow keyboard and history', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.name));
  await page.route('http://companion.test/**', async route => {
    const pathname = new URL(route.request().url()).pathname;
    const filename = ['/accessibility-runtime.js', '/ui-locale.js'].includes(pathname)
      ? pathname.slice(1) : 'index.html';
    const body = readFileSync(resolve(launcher, filename), 'utf8')
      .replace('<script src="renderer.js"></script>', '');
    await route.fulfill({ contentType: filename.endsWith('.js') ? 'text/javascript' : 'text/html', body });
  });
  await page.goto('http://companion.test/');
  const links = page.locator('.nav');
  await expect(links.getByRole('link', { name: 'Overview', exact: true })).toHaveAttribute('aria-current', 'location');
  await links.getByRole('link', { name: 'Voice', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(links.getByRole('link', { name: 'Voice', exact: true })).toHaveAttribute('aria-current', 'location');
  await expect(links.getByRole('link', { name: 'Overview', exact: true })).not.toHaveAttribute('aria-current', 'location');
  await page.goBack();
  await expect(links.getByRole('link', { name: 'Overview', exact: true })).toHaveAttribute('aria-current', 'location');
  await page.goto('http://companion.test/#account');
  await expect(links.getByRole('link', { name: 'Account', exact: true })).toHaveAttribute('aria-current', 'location');
  expect(await page.locator('.brand-mark path').nth(1).getAttribute('d')).toContain('M43 18.5');
  expect(await page.locator('.brand-mark').evaluate(el => el.getBoundingClientRect().width)).toBeGreaterThan(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  await page.emulateMedia({ forcedColors: 'active', reducedMotion: 'reduce' });
  await links.getByRole('link', { name: 'Games', exact: true }).focus();
  expect(await links.getByRole('link', { name: 'Games', exact: true }).evaluate(el => getComputedStyle(el).outlineStyle)).not.toBe('none');
  await page.keyboard.press('Enter');
  await expect(links.getByRole('link', { name: 'Games', exact: true })).toHaveAttribute('aria-current', 'location');
  await page.getByRole('combobox', { name: 'Interface language' }).selectOption('ru');
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
  await expect(links.getByRole('link', { name: 'Игры', exact: true })).toHaveAttribute('aria-current', 'location');
  await expect(page.locator('#voice-ptt')).toBeDisabled();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  expect(errors).toEqual([]);
});
