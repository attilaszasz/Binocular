import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { deleteModule, listModules, reloadModules, uploadModule } from "../../api/client";
import { queryKeys } from "../../api/queryKeys";

export function useModules() {
  return useQuery({
    queryKey: queryKeys.modules.all(),
    queryFn: listModules,
    staleTime: 30_000,
  });
}

export function useUploadModule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      file,
      options,
    }: {
      file: File;
      options?: { testUrl?: string; testModel?: string };
    }) => uploadModule(file, options),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.modules.all() });
    },
  });
}

export function useDeleteModule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (filename: string) => deleteModule(filename),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.modules.all() });
    },
  });
}

export function useReloadModules() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => reloadModules(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.modules.all() });
    },
  });
}
