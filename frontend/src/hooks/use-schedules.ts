/**
 * TanStack Query hooks for schedule operations.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { schedulesApi, type Schedule } from "@/lib/api";

const SCHEDULES_KEY = ["schedules"] as const;

export function useSchedules() {
  return useQuery<Schedule[]>({
    queryKey: SCHEDULES_KEY,
    queryFn: schedulesApi.list,
  });
}

export function useUpdateSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ moduleId, intervalHours }: { moduleId: number; intervalHours: number }) =>
      schedulesApi.update(moduleId, intervalHours),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: SCHEDULES_KEY });
    },
  });
}
