/**
 * TanStack Query hooks for module CRUD operations.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { modulesApi, type Module } from "@/lib/api";

const MODULES_KEY = ["modules"] as const;
const DEVICES_KEY = ["devices"] as const;

export function useModules() {
  return useQuery<Module[]>({
    queryKey: MODULES_KEY,
    queryFn: modulesApi.list,
  });
}

export function useUploadModule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ file, runPhase2 }: { file: File; runPhase2: boolean }) =>
      modulesApi.upload(file, runPhase2),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MODULES_KEY });
      qc.invalidateQueries({ queryKey: DEVICES_KEY });
    },
  });
}

export function useUpdateModule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      modulesApi.update(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MODULES_KEY });
      qc.invalidateQueries({ queryKey: DEVICES_KEY });
    },
  });
}

export function useDeleteModule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => modulesApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MODULES_KEY });
      qc.invalidateQueries({ queryKey: DEVICES_KEY });
    },
  });
}
