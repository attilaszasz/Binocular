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
  test(`TR-007 keyboard, honest firmware states and local-only forms: ${theme}`, async ({ page, request }, info) => {
    await page.addInitScript(value => localStorage.setItem("binocular-theme", value), theme);
    const modules = await (await request.get("/api/v1/modules")).json();
    const sony = modules.find((module: { name: string }) => module.name === "sony_alpha");
    const prefix = `TR-007 ${theme} ${info.project.name}`;
    const external: string[] = [];
    const firmwareActions: string[] = [];
    const pageErrors: string[] = [];
    page.on("pageerror", error => pageErrors.push(error.message));
    await page.route("**/*", route => {
      const url = new URL(route.request().url());
      if (url.hostname !== "127.0.0.1") {
        external.push(url.href);
        return route.abort();
      }
      return route.continue();
    });
    page.on("request", req => {
      if (new URL(req.url()).pathname.startsWith("/api/v1/checks/")) firmwareActions.push(req.url());
    });
    const vendorCount = async () => {
      const response = await request.get("/api/v1/modules");
      expect(response.ok()).toBe(true);
      const count = response.headers()["x-e2e-vendor-requests"];
      expect(count).toMatch(/^\d+$/);
      return Number(count);
    };
    const baseline = await vendorCount();
    const card = (name: string) => page.locator('[data-slot="card"]').filter({ has: page.getByText(`${prefix} ${name}`, { exact: true }) });
    try {
      await page.goto("/inventory");
      await page.getByRole("button", { name: /Add.*Device/i }).first().press("Enter");
      const name = page.getByRole("textbox", { name: "Name", exact: true });
      const source = page.getByRole("combobox", { name: "Source", exact: true });
      const model = page.getByRole("textbox", { name: "Model", exact: true });
      const installed = page.getByRole("textbox", { name: "Current Version", exact: true });
      const unknown = page.getByRole("checkbox", { name: "Installed version unknown", exact: true });
      await expect(source).toBeEnabled();
      await name.fill(`${prefix} Unknown`);
      await expect(name).toHaveValue(`${prefix} Unknown`);
      await expect(page.getByRole("button", { name: "Add Device", exact: true })).toBeEnabled();
      await page.getByRole("button", { name: "Add Device", exact: true }).press("Enter");
      await expect(page.getByRole("alert")).toHaveText("Please select a module.");
      await audit(page, info, "keyboard-form-error");
      await source.press("Enter");
      await expect(page.locator("#device-module")).toHaveAttribute("aria-expanded", "true");
      await expect(page.getByRole("listbox")).toBeVisible();
      await page.keyboard.type("Sony");
      await expect(page.getByRole("option", { name: /Sony Alpha cameras/ })).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(source).toContainText("Sony Alpha cameras");
      await expect(source).toBeFocused();
      await expect(source).toHaveAttribute("aria-expanded", "false");
      await expect(model).toHaveAttribute("aria-describedby", "device-model-help");
      await expect(model).toHaveAccessibleDescription(/ILCE-/);
      await model.fill("ILCE-7CM2");
      await installed.fill("1.00");
      await expect(unknown).not.toBeChecked();
      await expect(installed).toHaveAccessibleDescription(/blank version is always unknown/);
      await installed.press("Tab");
      await expect(unknown).toBeFocused();
      await page.keyboard.press("Space");
      await expect(unknown).toBeChecked();
      await expect(installed).toHaveValue("1.00");
      await audit(page, info, "keyboard-unknown-form");
      await page.getByRole("button", { name: "Add Device", exact: true }).press("Enter");
      await expect(card("Unknown").getByRole("status", { name: "Firmware status" })).toContainText("Installed version unknown");
      await card("Unknown").getByRole("button", { name: "Edit device" }).press("Enter");
      await expect(unknown).toBeChecked();
      await expect(installed).toHaveValue("1.00");
      await model.fill("local edit without search");
      await model.fill("ILCE-7CM2");
      await page.getByRole("button", { name: "Save Changes" }).press("Enter");
      await expect(name).toHaveCount(0);
      expect(firmwareActions).toEqual([]);
      expect(external).toEqual([]);
      const after = await vendorCount();
      expect(after).toBe(baseline);
      const networkPath = info.outputPath("ordinary-form-network.json");
      await writeFile(networkPath, JSON.stringify({ before: baseline, after, external, firmwareActions }, null, 2));
      await info.attach("ordinary-form-network", {
        path: networkPath,
        contentType: "application/json",
      });

      // Explicit V1 search is intentionally separate from ordinary local interaction.
      await card("Unknown").getByRole("button", { name: "Edit device" }).press("Enter");
      await page.getByRole("button", { name: "Search Version" }).press("Enter");
      await expect(page.getByRole("status", { name: "Version search reference" })).toContainText("reference only): 2.01");
      await expect(installed).toHaveValue("1.00");
      await expect(unknown).toBeChecked();
      expect(await vendorCount()).toBeGreaterThan(baseline);
      await audit(page, info, "explicit-search-reference");
      await model.fill("near-match unknown");
      await page.getByRole("button", { name: "Search Version" }).press("Enter");
      await expect(page.getByRole("alert")).toContainText("product_not_found");
      await expect(page.getByRole("status", { name: "Version search reference" })).toHaveCount(0);
      await expect(installed).toHaveValue("1.00");
      await expect(unknown).toBeChecked();
      await audit(page, info, "explicit-search-error");
      await model.fill("ILCE-7CM2");
      await expect(page.getByRole("alert")).toHaveCount(0);
      await page.getByRole("button", { name: "Cancel", exact: true }).press("Enter");

      for (const [label, current_version] of [["Update", "1.00"], ["Current", "2.01"], ["Incomparable", "operator text"]]) {
        const response = await request.post("/api/v1/devices", { data: {
          name: `${prefix} ${label}`, model: "ILCE-7CM2", module_id: sony.id,
          current_version, installed_unknown: false,
        } });
        expect(response.ok()).toBe(true);
      }
      await page.reload();
      for (const label of ["Unknown", "Update", "Current", "Incomparable"]) {
        await card(label).getByRole("button", { name: "Check for update" }).press("Enter");
        await expect(card(label).getByText(/Last successfully checked:/)).toBeVisible();
      }
      for (const [label, text] of [["Unknown", "Installed version unknown"], ["Incomparable", "Versions cannot be compared"], ["Current", "Latest"]]) {
        await expect(card(label).getByRole("status", { name: "Firmware status" })).toContainText(text);
        await expect(card(label).getByRole("button", { name: "Confirm Update" })).toHaveCount(0);
      }
      for (const label of ["Unknown", "Incomparable"]) {
        await expect(card(label).getByText("Latest", { exact: true })).toHaveCount(0);
        await expect(card(label).getByText("Last detected version (reference only): 2.01")).toBeVisible();
      }
      await expect(card("Update").getByRole("status", { name: "Firmware status" })).toContainText("1.00");
      await expect(card("Update").getByRole("status", { name: "Firmware status" })).toContainText("Update available");
      await expect(card("Update").getByRole("status", { name: "Firmware status" })).toContainText("2.01");
      await expect(card("Update").getByRole("button", { name: "Confirm Update" })).toBeVisible();
      await audit(page, info, "honest-inventory-statuses");

      // An out-of-band check must remain failed after a full reload, without
      // relying on the card mutation's transient checkError state.
      const beforeFailure = (await (await request.get("/api/v1/devices")).json())
        .find((device: { name: string }) => device.name === `${prefix} Current`);
      expect((await request.put("/api/v1/e2e/vendor-failure/true")).ok()).toBe(true);
      try {
        const failure = await (await request.post(`/api/v1/checks/device/${beforeFailure.id}`)).json();
        expect(failure.success).toBe(false);
        const retained = await (await request.get(`/api/v1/devices/${beforeFailure.id}`)).json();
        expect(retained.comparison_status).toBe("failed");
        expect(retained.has_update).toBe(false);
        expect(retained.last_checked).toBe(beforeFailure.last_checked);
        expect(retained.last_check_attempt_at).toBe(failure.checked_at);
        expect(retained.latest_detected_version).toBe(beforeFailure.latest_detected_version);
        expect(retained.revision).toBe(beforeFailure.revision);
        await page.reload();
        await expect(card("Current").getByRole("status", { name: "Firmware status" })).toContainText("Verification failed");
        await expect(card("Current").getByText("Latest", { exact: true })).toHaveCount(0);
        await expect(card("Current").getByRole("alert")).toContainText("Last verification failed");
        await expect(card("Current").getByText(/Last check attempt:/)).toBeVisible();
        await expect(card("Current").getByText("Last detected version (reference only): 2.01")).toBeVisible();
        await audit(page, info, "persisted-failure-after-reload");
      } finally {
        expect((await request.put("/api/v1/e2e/vendor-failure/false")).ok()).toBe(true);
      }
      expect(external).toEqual([]);
      expect(pageErrors).toEqual([]);
    } finally {
      const devices = await (await request.get("/api/v1/devices")).json();
      for (const device of devices.filter((device: { name: string }) => device.name.startsWith(prefix))) {
        expect((await request.delete(`/api/v1/devices/${device.id}`)).ok()).toBe(true);
      }
    }
  });

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
