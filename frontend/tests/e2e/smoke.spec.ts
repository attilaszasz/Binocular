import { expect, test } from "@playwright/test";

test("smoke: load dashboard and navigate", async ({ page }) => {
  const loadStart = Date.now();
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Inventory" })).toBeVisible();
  const loadElapsedMs = Date.now() - loadStart;
  expect(loadElapsedMs).toBeLessThan(3_000);

  await page.getByRole("link", { name: "Modules" }).click();
  await expect(page.getByText("Extension Modules")).toBeVisible();

  await page.getByRole("link", { name: "Inventory" }).click();
  await expect(page.getByRole("heading", { name: "Inventory" })).toBeVisible();

  const syncButtons = page.getByRole("button", { name: /sync local/i });
  if ((await syncButtons.count()) > 0) {
    const confirmStart = Date.now();
    await syncButtons.first().click();
    await expect(syncButtons.first()).toHaveCount(0, { timeout: 2_000 });
    const confirmElapsedMs = Date.now() - confirmStart;
    expect(confirmElapsedMs).toBeLessThan(2_000);
  }

  const transitionStart = Date.now();
  await page.getByRole("link", { name: "Modules" }).click();
  await expect(page.getByText("Extension Modules")).toBeVisible();
  const transitionElapsedMs = Date.now() - transitionStart;
  expect(transitionElapsedMs).toBeLessThan(300);

  await page.getByRole("link", { name: "Settings" }).click();
  await expect(
    page.getByText("Notification and scheduling configuration will appear here."),
  ).toBeVisible();
});
