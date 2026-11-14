import { expect, test } from '@playwright/test';

test.use({ javaScriptEnabled: false, viewport: { width: 320, height: 844 } });

test('the static English About page exposes biography and canonical metadata', async ({
  page,
  request,
}) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'About Felix Yang' }).click();
  await expect(page.getByRole('heading', { name: 'Felix Yang.', level: 1 })).toBeVisible();
  await expect(page.getByText('Streaming video', { exact: true })).toBeVisible();
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    'href',
    'https://felixpy.com/about',
  );
  const profile = JSON.parse(await page.locator('script[type="application/ld+json"]').innerHTML());
  expect(profile.mainEntity.alternateName).toEqual(['felixpy', 'gofelixpy']);

  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.locator('link[hreflang]')).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Find me on GitHub' })).toHaveAttribute(
    'href',
    'https://github.com/felixpy',
  );
  await expect(page.getByRole('link', { name: 'Follow on X' })).toHaveAttribute(
    'href',
    'https://x.com/gofelixpy',
  );
  expect(await page.locator('html').evaluate((html) => html.scrollWidth === html.clientWidth)).toBe(
    true,
  );

  const sitemap = await request.get('/sitemap.xml');
  expect(sitemap.ok()).toBe(true);
  const urls = await sitemap.text();
  expect(urls).toContain('https://felixpy.com/about');
  expect(urls).not.toContain('/zh/about');
  const robots = await request.get('/robots.txt');
  expect(await robots.text()).toContain('Sitemap: https://felixpy.com/sitemap.xml');
  const llms = await request.get('/llms.txt');
  expect(await llms.text()).toContain('https://felixpy.com/about');
});
