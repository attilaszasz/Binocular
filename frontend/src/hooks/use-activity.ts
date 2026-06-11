/**
 * TanStack Query hooks for activity log operations.
 */
import { useQuery } from "@tanstack/react-query";
import { activityApi, type ActivityLogListResponse, type ActivityQueryParams } from "@/lib/api";

const ACTIVITY_KEY = ["activity"] as const;

export function useActivity(params: ActivityQueryParams = {}) {
  return useQuery<ActivityLogListResponse>({
    queryKey: [...ACTIVITY_KEY, params],
    queryFn: () => activityApi.list(params),
  });
}
