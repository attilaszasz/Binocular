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
    refetchOnWindowFocus: "always",
  });
}

export function useModuleScope(id: number, enabled: boolean) {
  return useQuery({
    queryKey: ["module-scope", id],
    queryFn: () => modulesApi.devices(id),
    enabled,
    refetchOnWindowFocus: "always",
    staleTime: 0,
  });
}

export function useUploadModule() {
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ file, runPhase2 }: { file: File; runPhase2: boolean }) =>
      modulesApi.upload(file, runPhase2),
  });
  return { ...mutation, acknowledgeSave: () => {
      qc.invalidateQueries({ queryKey: MODULES_KEY });
      qc.invalidateQueries({ queryKey: DEVICES_KEY });
      qc.invalidateQueries({ queryKey: ["module-scope"] });
      qc.invalidateQueries({ queryKey: ["schedules"] });
    } };
}

export function useUpdateModule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      modulesApi.update(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MODULES_KEY });
      qc.invalidateQueries({ queryKey: DEVICES_KEY });
      qc.invalidateQueries({ queryKey: ["module-scope"] });
      qc.invalidateQueries({ queryKey: ["schedules"] });
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
      qc.invalidateQueries({ queryKey: ["module-scope"] });
      qc.invalidateQueries({ queryKey: ["schedules"] });
    },
  });
}
