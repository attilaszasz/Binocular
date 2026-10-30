import { afterEach, expect, it, vi } from "vitest";
import { activityApi, ApiError, checksApi, deviceComparisonStatus, devicesApi, modulesApi, notificationsApi, schedulesApi, type Device } from "./api";

afterEach(() => vi.restoreAllMocks());

it("uses typed routes, request bodies and multipart without a JSON header", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response("[]", { status: 200 }));
  const calls = [
    () => devicesApi.list(), () => devicesApi.get(1), () => devicesApi.create({ name: "camera", module_id: 1 }),
    () => devicesApi.update(1, { module_id: 2 }), () => devicesApi.delete(1), () => devicesApi.confirm(1),
    () => modulesApi.list(), () => modulesApi.devices(1), () => modulesApi.update(1, "inactive"), () => modulesApi.delete(1),
    () => checksApi.checkDevice(1), () => checksApi.checkBulk(), () => checksApi.searchVersion(1, "model"),
    () => schedulesApi.list(), () => schedulesApi.update(1, 6), () => notificationsApi.list(),
    () => notificationsApi.save({ type: "email", enabled: false, config: {} }), () => notificationsApi.test({ type: "email", config: {} }),
    () => activityApi.list(), () => activityApi.list({ level: "ERROR", category: "check", device_id: 1, limit: 20, offset: 20 }),
  ];
  for (const call of calls) await call();
  expect(fetch).toHaveBeenCalledWith("/api/v1/devices/1", expect.objectContaining({ method: "PUT", body: '{"module_id":2}' }));
  expect(fetch).toHaveBeenCalledWith("/api/v1/activity?level=ERROR&category=check&device_id=1&limit=20&offset=20", expect.anything());
  const file = new File(["code"], "custom.py");
  await modulesApi.upload(file, true);
  expect(fetch).toHaveBeenLastCalledWith("/api/v1/modules?run_phase2=true", expect.objectContaining({ body: expect.any(FormData) }));
});

it.each([true, false])("surfaces structured errors and invalid JSON (%s)", async structured => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(structured ? '{"detail":{"field":"invalid"}}' : "not json", { status: 422, statusText: "Invalid" }));
  await expect(devicesApi.list()).rejects.toBeInstanceOf(ApiError);
  await expect(modulesApi.upload(new File([], "custom.py"))).rejects.toMatchObject({ status: 422 });
});

it("handles bodyless delete responses", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));
  expect(await devicesApi.delete(1)).toBeUndefined();
});

it("preserves additive status and ownership fields and sends explicit unknown/revision mutations", async () => {
  const response = { catalog_model_id: null, catalog_link_state: "unresolved", installed_unknown: true, revision: 8, comparison_status: "unknown", current_version: "retained", latest_detected_version: "2.0" };
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json(response));
  expect(await devicesApi.get(1)).toEqual(response);
  await devicesApi.create({ name: "Camera", module_id: 1, current_version: "retained", installed_unknown: true });
  expect(fetch).toHaveBeenLastCalledWith("/api/v1/devices", expect.objectContaining({ body: JSON.stringify({ name: "Camera", module_id: 1, current_version: "retained", installed_unknown: true }) }));
  await devicesApi.update(1, { installed_unknown: true, expected_revision: 7 });
  expect(fetch).toHaveBeenLastCalledWith("/api/v1/devices/1", expect.objectContaining({ body: '{"installed_unknown":true,"expected_revision":7}' }));
  await devicesApi.confirm(1, 8);
  expect(fetch).toHaveBeenLastCalledWith("/api/v1/devices/1/confirm?expected_revision=8", expect.objectContaining({ method: "PUT" }));
});

it("surfaces revision conflicts instead of silently retrying or confirming", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({ detail: "Device mutation conflict: stale_revision" }, { status: 409 }));
  await expect(devicesApi.update(1, { expected_revision: 2, current_version: "2.0" })).rejects.toMatchObject({ status: 409, message: "Device mutation conflict: stale_revision" });
  await expect(devicesApi.confirm(1, 2)).rejects.toMatchObject({ status: 409 });
  expect(fetch).toHaveBeenCalledTimes(2);
});

it.each<[Partial<Device>, string]>([
  [{ current_version: "" }, "unknown"],
  [{ installed_unknown: true, comparison_status: "current" }, "unknown"],
  [{}, "unverified"],
  [{ has_update: true }, "unverified"],
  [{ latest_detected_version: "1.0", last_checked: null }, "unverified"],
  [{ latest_detected_version: "1.0", last_checked: "2026-10-29" }, "current"],
  [{ latest_detected_version: "2.0", has_update: true }, "update_available"],
  [{ current_version: "opaque", latest_detected_version: "opaque", last_checked: "2026-10-29" }, "comparison_unknown"],
  [{ latest_detected_version: "opaque", has_update: true }, "comparison_unknown"],
  [{ comparison_status: "comparison_unknown", has_update: true, latest_detected_version: "2.0" }, "comparison_unknown"],
])("adapts legacy and additive status honestly: %j", (overrides, expected) => {
  const device: Device = { id: 1, name: "Camera", model: "Model", module_id: 1, module_name: "Source", device_type: "camera", current_version: "1.0", has_update: false, latest_detected_version: null, last_checked: null, last_notified_version: null, created_at: "", updated_at: "", ...overrides };
  expect(deviceComparisonStatus(device)).toBe(expected);
});
