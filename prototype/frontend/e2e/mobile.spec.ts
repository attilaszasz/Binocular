import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * T017: Mobile operability tests
 * - Set viewport to 320px
 * - Verify hamburger menu opens/closes
 * - Verify content is visible (basic checks)
 * - Verify table is scrollable
 *
 * Completes: SC-002 (all views at 320px, all interactive elements reachable)
 *            SC-003 (hamburger menu opens/closes correctly with focus management)
 */

const MOBILE_VIEWPORT = { width: 320, height: 568 };

const ROUTES_WITH_CHECK = [
  { path: '/inventory', heading: 'Device Inventory' },
  { path: '/logs', heading: 'Activity Logs' },
  { path: '/modules', heading: 'Extension Modules' },
  { path: '/settings', heading: 'Settings Configuration' },
] as const;

const screenshotDir = path.resolve(__dirname, '..', 'test-screenshots', 'mobile');

test.describe('Mobile (320px)', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
  });

  for (const { path: route, heading } of ROUTES_WITH_CHECK) {
    test(`hamburger menu opens and closes on ${route}`, async ({ page }) => {
      await page.goto(route, { waitUntil: 'networkidle' });

      // Hamburger menu button should be visible
      const hamburgerBtn = page.locator('button[aria-label="Open navigation"]');
      await expect(hamburgerBtn).toBeVisible();
      await expect(hamburgerBtn).toBeEnabled();

      // Verify sidebar is hidden initially
      const sidebar = page.locator('aside');
      await expect(sidebar).toHaveClass(/-translate-x-full/);

      // Open the menu
      await hamburgerBtn.click();
      await page.waitForTimeout(300);

      // Sidebar should now be visible (no -translate-x-full)
      await expect(sidebar).not.toHaveClass(/-translate-x-full/);

      // Verify nav items are visible inside sidebar
      const navLinks = sidebar.locator('a');
      const count = await navLinks.count();
      expect(count).toBeGreaterThanOrEqual(1);

      // Close button should be visible in sidebar
      const closeBtn = sidebar.locator('button[aria-label="Close navigation"]');
      await expect(closeBtn).toBeVisible();

      // Close the menu
      await closeBtn.click();
      await page.waitForTimeout(300);

      // Sidebar should be hidden again
      await expect(sidebar).toHaveClass(/-translate-x-full/);

      // Focus should return to hamburger button
      await expect(hamburgerBtn).toBeFocused();
    });

    test(`content is visible on ${route}`, async ({ page }) => {
      await page.goto(route, { waitUntil: 'networkidle' });

      // Page heading should be visible
      const headingEl = page.getByRole('heading', { name: heading, exact: false }).first();
      await expect(headingEl).toBeVisible();

      // Main content area should be visible
      await expect(page.locator('main')).toBeVisible();

      // Take screenshot for visual audit
      await page.screenshot({
        path: path.join(screenshotDir, `${route.replace(/\//g, '')}-content.png`),
        fullPage: true,
      });
    });
  }

  test('table is scrollable on /logs page at 320px', async ({ page }) => {
    await page.goto('/logs', { waitUntil: 'networkidle' });

    // The table should exist
    const table = page.locator('table');
    await expect(table).toBeVisible({ timeout: 5000 });

    // The table wrapper should allow horizontal scroll
    const scrollContainer = page.locator('.overflow-x-auto').first();
    await expect(scrollContainer).toBeVisible();

    // Verify the table is wider than the viewport (scrollable)
    const tableWidth = await table.boundingBox();
    const viewportWidth = page.viewportSize()?.width ?? 320;

    if (tableWidth) {
      // Table should be wider than the viewport, indicating horizontal scroll
      expect(tableWidth.width).toBeGreaterThan(viewportWidth);
    }

    // Scroll hint gradient should be visible at right edge
    const scrollHint = page.locator('.pointer-events-none.absolute.inset-y-0.right-0');
    await expect(scrollHint.first()).toBeVisible();

    // Verify at least one interactive element (button) is reachable
    // The refresh button should be visible
    const refreshBtn = page.getByRole('button', { name: /Refresh/, exact: false });
    await expect(refreshBtn.first()).toBeVisible();

    // Table header cells should have content
    const tableHeaders = table.locator('th');
    await expect(tableHeaders.first()).toBeVisible();

    await page.screenshot({
      path: path.join(screenshotDir, 'logs-table-scroll.png'),
      fullPage: true,
    });
  });

  test('hamburger menu overlay dismisses on tap outside', async ({ page }) => {
    await page.goto('/inventory', { waitUntil: 'networkidle' });

    // Open the menu
    const hamburgerBtn = page.locator('button[aria-label="Open navigation"]');
    await hamburgerBtn.click();
    await page.waitForTimeout(300);

    // The overlay should be present
    const overlay = page.locator('button[aria-label="Close navigation overlay"]');
    await expect(overlay).toBeVisible();

    // Click the overlay to dismiss
    await overlay.click({ position: { x: 160, y: 300 } });
    await page.waitForTimeout(300);

    // Sidebar should be hidden again
    const sidebar = page.locator('aside');
    await expect(sidebar).toHaveClass(/-translate-x-full/);
  });

  test('touch targets are at least 44x44px on interactive elements', async ({ page }) => {
    await page.goto('/inventory', { waitUntil: 'networkidle' });

    // Check hamburger button size
    const hamburgerBtn = page.locator('button[aria-label="Open navigation"]');
    const hamburgerBox = await hamburgerBtn.boundingBox();
    expect(hamburgerBox).not.toBeNull();
    expect(hamburgerBox!.width).toBeGreaterThanOrEqual(44);
    expect(hamburgerBox!.height).toBeGreaterThanOrEqual(44);

    // Check the theme toggle button size
    const toggleBtn = page.locator('button[aria-label^="Switch to"]');
    const toggleBox = await toggleBtn.boundingBox();
    expect(toggleBox).not.toBeNull();
    expect(toggleBox!.width).toBeGreaterThanOrEqual(44);
    expect(toggleBox!.height).toBeGreaterThanOrEqual(44);
  });

  test('sidebar nav list is scrollable when items exceed viewport', async ({ page }) => {
    await page.goto('/inventory', { waitUntil: 'networkidle' });

    // Open the menu
    await page.locator('button[aria-label="Open navigation"]').click();
    await page.waitForTimeout(300);

    // The nav element should have overflow-y: auto
    const nav = page.locator('nav[aria-label="Primary navigation"]');
    await expect(nav).toBeVisible();

    const overflowY = await nav.evaluate((el) => window.getComputedStyle(el).overflowY);
    expect(overflowY).toBe('auto');
  });
});
