import { createRequire } from "node:module";
import { writeFile } from "node:fs/promises";
import { test, expect, type Page, type TestInfo } from "@playwright/test";
import type { AxeResults } from "axe-core";

const axePath = createRequire(import.meta.url).resolve("axe-core/axe.min.js");

async function audit(page: Page, info: TestInfo, state: string) {
  await page.addScriptTag({ path: axePath });
  const results = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: typeof import("axe-core") }).axe;
    return axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] } });
  });
  const path = info.outputPath(`${state}-axe.json`);
  await writeFile(path, JSON.stringify(results, null, 2));
  await info.attach(`${state}-axe`, { path, contentType: "application/json" });
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  // Do not accept an audit that silently skipped either original QC rule.
  for (const id of ["link-name", "color-contrast"]) {
    expect(results.passes.some((rule: AxeResults["passes"][number]) => rule.id === id)).toBe(true);
    expect(results.incomplete.filter(rule => rule.id === id)).toEqual([]);
  }
}

for (const theme of ["light", "dark"]) {
  test(`FR-018 rendered WCAG regression: ${theme} navigation and source states`, async ({ page }, info) => {
    await page.addInitScript(value => localStorage.setItem("binocular-theme", value), theme);
    // Test-only response projection exercises amber health without changing backend state or semantics.
    await page.route("**/api/v1/modules", async route => {
      const response = await route.fetch();
      const modules = await response.json();
      for (const module of modules) {
        if (module.is_official) {
          module.status = "active";
          module.consecutive_failures = module.name === "sony_alpha" ? 2 : 0;
        }
      }
      await route.fulfill({ response, json: modules });
    });
    await page.goto("/modules");
    await expect(page.locator("html")).toHaveClass(theme);
    await expect(page.getByText("Sony Alpha cameras & lenses", { exact: true })).toBeVisible();
    await expect(page.getByText("2 consecutive failures", { exact: true })).toBeVisible();
    await expect(page.getByText("Healthy", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Official", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("active", { exact: true }).first()).toBeVisible();
    for (const name of ["Inventory", "Modules", "Logs", "Settings"]) {
      const link = page.getByRole("link", { name, exact: true });
      await expect(link).toBeVisible();
      await expect(link).toHaveAttribute("aria-label", name);
    }
    await expect(page.getByRole("link", { name: "Modules", exact: true })).toHaveAttribute("aria-current", "page");
    await audit(page, info, "sources");

    const card = page.locator('[data-slot="card"]').filter({ has: page.getByText("Sony Alpha cameras & lenses", { exact: true }) });
    await card.getByRole("button", { name: "Inspect linked devices" }).click();
    await expect(card.getByRole("button", { name: "Refresh linked devices" })).toBeVisible();
    await card.locator("summary").click();
    await page.getByRole("button", { name: "Create a Module", exact: true }).click();
    await expect(page.getByText("STARTER_TEMPLATE.py", { exact: true })).toBeVisible();
    await audit(page, info, "scope-details-authoring");
    await page.getByRole("button", { name: "Upload Module", exact: true }).click();
    await expect(page.getByText(/unsandboxed, user-vetted code/)).toBeVisible();
    await audit(page, info, "upload-warning");

    await page.goto("/inventory");
    await page.getByRole("button", { name: /Add.*Device/i }).first().click();
    await page.getByLabel("Source", { exact: true }).click();
    await page.getByRole("option", { name: /Sony Alpha cameras/ }).click();
    await expect(page.getByLabel("Model", { exact: true })).toHaveAttribute("aria-describedby", "device-model-help");
    await audit(page, info, "add-source-help");
  });
}
