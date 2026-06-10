/**
 * TanStack Query hooks for device CRUD operations.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  devicesApi,
  type Device,
  type DeviceCreate,
  type DeviceUpdate,
} from "@/lib/api";

const DEVICES_KEY = ["devices"] as const;

export function useDevices() {
  return useQuery<Device[]>({
    queryKey: DEVICES_KEY,
    queryFn: devicesApi.list,
  });
}

export function useDevice(id: number) {
  return useQuery<Device>({
    queryKey: [...DEVICES_KEY, id],
    queryFn: () => devicesApi.get(id),
    enabled: id > 0,
  });
}

export function useCreateDevice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DeviceCreate) => devicesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: DEVICES_KEY }),
  });
}

export function useUpdateDevice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: DeviceUpdate }) =>
      devicesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: DEVICES_KEY }),
  });
}

export function useDeleteDevice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => devicesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: DEVICES_KEY }),
  });
}

export function useConfirmUpdate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => devicesApi.confirm(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: DEVICES_KEY }),
  });
}
