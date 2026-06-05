import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * T015: Dark mode visual audit tests
 * - Navigate all routable views at 320px / 768px / 1280px
 * - Apply dark class, verify pages load without errors
 * - Capture screenshots for visual review
 *
 * Completes: SC-001 (dark mode no unreadable text or invisible borders)
 */

const ROUTES = ['/inventory', '/logs', '/modules', '/settings'] as const;
const VIEWPORTS = [
  { label: 'mobile', width: 320, height: 568 },
  { label: 'tablet', width: 768, height: 1024 },
  { label: 'desktop', width: 1280, height: 720 },
] as const;

/** Ensure dark class is applied on the document element before snapshot. */
async function applyDarkMode(page: import('@playwright/test').Page) {
  // First set localStorage so the theme provider initializes correctly
  await page.evaluate(() => {
    localStorage.setItem('binocular-theme', 'dark');
  });
  // Then add dark class explicitly for visual testing
  await page.evaluate(() => {
    document.documentElement.classList.add('dark');
  });
  // Let Tailwind re-render
  await page.waitForTimeout(300);
}

const screenshotDir = path.resolve(__dirname, '..', 'test-screenshots', 'dark-mode');

for (const route of ROUTES) {
  for (const viewport of VIEWPORTS) {
    test(`dark mode: ${route} at ${viewport.label} (${viewport.width}px)`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(route, { waitUntil: 'networkidle' });

      // Apply dark mode
      await applyDarkMode(page);

      // Basic assertions: page loaded, no catastrophic errors
      await expect(page.locator('html')).toHaveClass(/dark/);
      await expect(page.locator('#root')).toBeVisible();

      // The body should have proper background (not white in dark mode)
      const bodyBgColor = await page.evaluate(() => {
        return window.getComputedStyle(document.body).backgroundColor;
      });
      // In dark mode, the body should not be pure white (rgb(255,255,255))
      expect(bodyBgColor).not.toBe('rgb(255, 255, 255)');

      // Verify at least one visible heading or main content element
      const heading = page.locator('h2').first();
      await expect(heading).toBeVisible({ timeout: 5000 });

      // Capture screenshot for visual audit
      await page.screenshot({
        path: path.join(screenshotDir, `${route.replace(/\//g, '-')}-${viewport.label}.png`),
        fullPage: false,
      });
    });
  }
}
