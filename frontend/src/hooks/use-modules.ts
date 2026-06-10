/**
 * TanStack Query hook for listing modules (read-only in E006).
 */
import { useQuery } from "@tanstack/react-query";
import { modulesApi, type Module } from "@/lib/api";

export function useModules() {
  return useQuery<Module[]>({
    queryKey: ["modules"],
    queryFn: modulesApi.list,
  });
}
