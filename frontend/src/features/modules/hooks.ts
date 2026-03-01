import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createDeviceType,
  deleteDeviceType,
  listDeviceTypes,
  updateDeviceType,
} from "../../api/client";
import { queryKeys } from "../../api/queryKeys";
import type { DeviceTypeCreateRequest, DeviceTypeUpdateRequest } from "../../api/types";

export function useModuleDeviceTypes() {
  return useQuery({
    queryKey: queryKeys.deviceTypes.all(),
    queryFn: listDeviceTypes,
    staleTime: 30_000,
  });
}

export function useCreateDeviceType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: DeviceTypeCreateRequest) => createDeviceType(payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.deviceTypes.all() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.devices.all() }),
      ]);
    },
  });
}

export function useUpdateDeviceType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      deviceTypeId,
      payload,
    }: {
      deviceTypeId: number;
      payload: DeviceTypeUpdateRequest;
    }) => updateDeviceType(deviceTypeId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.deviceTypes.all() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.devices.all() }),
      ]);
    },
  });
}

export function useDeleteDeviceType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      deviceTypeId,
      confirmCascade,
    }: {
      deviceTypeId: number;
      confirmCascade: boolean;
    }) => deleteDeviceType(deviceTypeId, confirmCascade),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.deviceTypes.all() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.devices.all() }),
      ]);
    },
  });
}
