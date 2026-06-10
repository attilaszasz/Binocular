import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * T018: Desktop consistency test
 * - Set viewport to 1280px
 * - Navigate all views
 * - Verify basic layout elements are present
 * - Measure content padding, header height, card spacing
 *
 * Completes: SC-004 (layout measurements within ±4px across 1280px views)
 */

const DESKTOP_VIEWPORT = { width: 1280, height: 720 };

const ROUTES = [
  {
    path: '/inventory',
    heading: 'Device Inventory',
    expectedElements: [
      'h2',                    // Page heading
      'table select',          // Module selector dropdown
      'button:has-text("Check All")', // Bulk check button
      'button:has-text("Add Device")', // Add device link
      'form#inventory-form',   // Add device form
    ],
  },
  {
    path: '/logs',
    heading: 'Activity Logs',
    expectedElements: [
      'h2',
      'table',                 // Activity table
      'button:has-text("Refresh")',
      'select#log-type-filter',
      'select#log-status-filter',
    ],
  },
  {
    path: '/modules',
    heading: 'Extension Modules',
    expectedElements: [
      'h2',
      'input#moduleFile',      // File upload
      'button:has-text("Upload")',
    ],
  },
  {
    path: '/settings',
    heading: 'Settings Configuration',
    expectedElements: [
      'h2',
      'button:has-text("Save Settings")', // At least one Save button
      'button:has-text("Send Test")',     // At least one Test button
    ],
  },
] as const;

const screenshotDir = path.resolve(__dirname, '..', 'test-screenshots', 'desktop');

test.describe('Desktop (1280px)', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(DESKTOP_VIEWPORT);
  });

  for (const { path: route, heading, expectedElements } of ROUTES) {
    test(`layout elements present on ${route}`, async ({ page }) => {
      await page.goto(route, { waitUntil: 'networkidle' });

      // Page heading should be visible
      const headingEl = page.getByRole('heading', { name: heading, exact: false }).first();
      await expect(headingEl).toBeVisible();

      // Expected elements should be present
      for (const selector of expectedElements) {
        await expect(page.locator(selector).first()).toBeVisible({ timeout: 5000 });
      }

      // Main content area should have proper max-width container
      const mainContent = page.locator('main .max-w-7xl');
      await expect(mainContent).toBeVisible();

      // Take screenshot
      await page.screenshot({
        path: path.join(screenshotDir, `${route.replace(/\//g, '')}-layout.png`),
        fullPage: false,
      });
    });
  }

  test('layout measurements consistent across views at 1280px', async ({ page }) => {
    // Collect header heights across all views
    const headerHeights: number[] = [];
    const contentPaddings: number[] = [];

    for (const { path: route } of ROUTES) {
      await page.goto(route, { waitUntil: 'networkidle' });

      // Measure header height
      const headerBox = await page.locator('header').boundingBox();
      if (headerBox) {
        headerHeights.push(headerBox.height);
      }

      // Measure content padding-left
      const contentContainer = page.locator('main .max-w-7xl');
      const contentPadding = await contentContainer.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return parseFloat(styles.paddingLeft);
      });
      contentPaddings.push(contentPadding);
    }

    // All header heights should be within ±4px of each other
    const maxHeader = Math.max(...headerHeights);
    const minHeader = Math.min(...headerHeights);
    expect(maxHeader - minHeader).toBeLessThanOrEqual(4);

    // All content paddings should be consistent
    const maxPadding = Math.max(...contentPaddings);
    const minPadding = Math.min(...contentPaddings);
    expect(maxPadding - minPadding).toBeLessThanOrEqual(4);
  });

  test('sidebar is always visible on desktop', async ({ page }) => {
    await page.goto('/inventory', { waitUntil: 'networkidle' });

    // On desktop, sidebar should be visible (no -translate-x-full)
    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();
    await expect(sidebar).not.toHaveClass(/-translate-x-full/);

    // Hamburger menu button should not be visible on desktop
    const hamburgerBtn = page.locator('button[aria-label="Open navigation"]');
    await expect(hamburgerBtn).not.toBeVisible();
  });

  test('all navigation links are functional on desktop', async ({ page }) => {
    await page.goto('/inventory', { waitUntil: 'networkidle' });

    const navLinks = [
      { label: 'Inventory', href: '/inventory' },
      { label: 'Activity Logs', href: '/logs' },
      { label: 'Modules', href: '/modules' },
      { label: 'Settings', href: '/settings' },
    ];

    for (const { label, href } of navLinks) {
      // Click nav link by its text
      const navLink = page.locator('aside a').filter({ hasText: label });
      await navLink.click();
      await page.waitForTimeout(300);

      // URL should contain the expected path
      expect(page.url()).toContain(href);

      // Content should be loaded
      await expect(page.locator('main')).toBeVisible();
      await expect(page.locator('h2').first()).toBeVisible();
    }
  });

  test('theme toggle is accessible on desktop', async ({ page }) => {
    await page.goto('/inventory', { waitUntil: 'networkidle' });

    const toggleButton = page.locator('button[aria-label^="Switch to"]');
    await expect(toggleButton).toBeVisible();
    await expect(toggleButton).toBeEnabled();

    // Toggle to dark mode
    await toggleButton.click();
    await page.waitForTimeout(200);

    // Verify dark theme applied
    await expect(page.locator('html')).toHaveClass(/dark/);

    // Content should still be visible
    await expect(page.locator('h2').first()).toBeVisible();

    await page.screenshot({
      path: path.join(screenshotDir, 'desktop-dark.png'),
      fullPage: false,
    });
  });

  test('content padding and spacing are consistent at 1280px', async ({ page }) => {
    await page.goto('/inventory', { waitUntil: 'networkidle' });

    const contentContainer = page.locator('main .max-w-7xl');

    // Measure padding
    const paddingLeft = await contentContainer.evaluate(
      (el) => parseFloat(window.getComputedStyle(el).paddingLeft),
    );
    const paddingRight = await contentContainer.evaluate(
      (el) => parseFloat(window.getComputedStyle(el).paddingRight),
    );

    // Padding should be at least 16px (standard Tailwind px-4)
    expect(paddingLeft).toBeGreaterThanOrEqual(16);
    expect(paddingRight).toBeGreaterThanOrEqual(16);

    // Cards should have reasonable spacing
    const statCards = page.locator('.grid.grid-cols-1.gap-4.sm\\:grid-cols-3').first();
    const cardGap = await statCards.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      const gap = parseFloat(styles.gap) || parseFloat(styles.rowGap);
      return gap;
    });
    expect(cardGap).toBeGreaterThanOrEqual(12);
  });
});
