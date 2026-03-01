import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  confirmDevice,
  createDevice,
  deleteDevice,
  listDevices,
  listDeviceTypes,
  updateDevice,
} from "../../api/client";
import { queryKeys } from "../../api/queryKeys";
import type { Device, DeviceCreateRequest, DeviceUpdateRequest } from "../../api/types";

export function useDeviceTypes() {
  return useQuery({
    queryKey: queryKeys.deviceTypes.all(),
    queryFn: listDeviceTypes,
    staleTime: 30_000,
  });
}

export function useDevices() {
  return useQuery({
    queryKey: queryKeys.devices.all(),
    queryFn: () => listDevices({ sort: "name" }),
    staleTime: 30_000,
  });
}

export function useCreateDevice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      deviceTypeId,
      payload,
    }: {
      deviceTypeId: number;
      payload: DeviceCreateRequest;
    }) => createDevice(deviceTypeId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.devices.all() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.deviceTypes.all() }),
      ]);
    },
  });
}

export function useUpdateDevice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ deviceId, payload }: { deviceId: number; payload: DeviceUpdateRequest }) =>
      updateDevice(deviceId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.devices.all() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.deviceTypes.all() }),
      ]);
    },
  });
}

export function useDeleteDevice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (deviceId: number) => deleteDevice(deviceId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.devices.all() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.deviceTypes.all() }),
      ]);
    },
  });
}

export function useConfirmDevice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (deviceId: number) => confirmDevice(deviceId),
    onMutate: async (deviceId) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.devices.all() });
      const previous = queryClient.getQueryData<Device[]>(queryKeys.devices.all()) ?? [];

      queryClient.setQueryData<Device[]>(queryKeys.devices.all(), (current = []) =>
        current.map((device) => {
          if (device.id !== deviceId) {
            return device;
          }
          if (!device.latest_seen_version) {
            return device;
          }

          return {
            ...device,
            current_version: device.latest_seen_version,
            status: "up_to_date",
          };
        }),
      );

      return { previous };
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.devices.all(), context.previous);
      }
    },
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.devices.all() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.deviceTypes.all() }),
      ]);
    },
  });
}
