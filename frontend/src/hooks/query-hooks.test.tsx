import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { useCreateDevice, useUpdateDevice, useDeleteDevice, useConfirmUpdate, useCheckDevice, useCheckBulk, useDevices, useDevice } from "./use-devices";
import { useModules, useModuleScope, useUpdateModule, useDeleteModule, useUploadModule } from "./use-modules";
import { useSchedules, useUpdateSchedule } from "./use-schedules";
import { useActivity } from "./use-activity";

afterEach(() => vi.restoreAllMocks());
function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response("[]", { status: 200 }));
  return { client, wrapper };
}

it("reads devices, sources, exact members, schedules and activity through real query hooks", async () => {
  const { wrapper } = setup();
  const { result } = renderHook(() => [useDevices(), useDevice(1), useModules(), useModuleScope(1, true), useSchedules(), useActivity({ level: "ERROR" })], { wrapper });
  await waitFor(() => expect(result.current.every(query => query.isSuccess)).toBe(true));
  expect(fetch).toHaveBeenCalledWith("/api/v1/modules/1/devices", expect.anything());
});

it("membership mutations invalidate both old/new scopes by invalidating the whole scope family", async () => {
  const { client, wrapper } = setup();
  const invalidate = vi.spyOn(client, "invalidateQueries");
  const { result } = renderHook(() => ({ create: useCreateDevice(), update: useUpdateDevice(), remove: useDeleteDevice(), confirm: useConfirmUpdate(), check: useCheckDevice(), bulk: useCheckBulk() }), { wrapper });
  await act(async () => {
    await result.current.create.mutateAsync({ name: "camera", module_id: 1 });
    await result.current.update.mutateAsync({ id: 1, data: { module_id: 2 } });
    await result.current.remove.mutateAsync(1);
    await result.current.confirm.mutateAsync(1);
    await result.current.check.mutateAsync(1);
    await result.current.bulk.mutateAsync();
  });
  expect(invalidate.mock.calls.filter(([args]) => args?.queryKey?.[0] === "module-scope")).toHaveLength(3);
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ["modules"] });
});

it("invalidates status/schedule saves but waits for the NDJSON terminal upload acknowledgement", async () => {
  const { client, wrapper } = setup();
  const invalidate = vi.spyOn(client, "invalidateQueries");
  const { result } = renderHook(() => ({ update: useUpdateModule(), remove: useDeleteModule(), schedule: useUpdateSchedule(), upload: useUploadModule() }), { wrapper });
  await act(async () => {
    await result.current.update.mutateAsync({ id: 1, status: "inactive" });
    await result.current.remove.mutateAsync(1);
    await result.current.schedule.mutateAsync({ moduleId: 1, intervalHours: 6 });
  });
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ["schedules"] });
  invalidate.mockClear();
  await act(async () => { await result.current.upload.mutateAsync({ file: new File([], "custom.py"), runPhase2: false }); });
  expect(invalidate).not.toHaveBeenCalled();
  result.current.upload.acknowledgeSave();
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ["module-scope"] });
});
