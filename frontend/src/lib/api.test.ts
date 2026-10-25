import { afterEach, expect, it, vi } from "vitest";
import { activityApi, ApiError, checksApi, devicesApi, modulesApi, notificationsApi, schedulesApi } from "./api";

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
