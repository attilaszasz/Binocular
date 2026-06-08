import { apiClient } from './client';

export type ActivityLog = {
  id: number;
  eventType: 'check' | 'notification';
  status: 'success' | 'failed';
  deviceName: string | null;
  moduleName: string | null;
  message: string;
  traceback: string | null;
  createdAt: string;
};

export type GetActivityParams = {
  limit?: number;
  offset?: number;
  type?: 'check' | 'notification';
  status?: 'success' | 'failed';
};

export function listActivity(params?: GetActivityParams) {
  const queryParams = new URLSearchParams();
  if (params) {
    if (params.limit !== undefined) {
      queryParams.append('limit', params.limit.toString());
    }
    if (params.offset !== undefined) {
      queryParams.append('offset', params.offset.toString());
    }
    if (params.type !== undefined) {
      queryParams.append('type', params.type);
    }
    if (params.status !== undefined) {
      queryParams.append('status', params.status);
    }
  }
  const queryString = queryParams.toString();
  const path = queryString ? `/audit-log?${queryString}` : '/audit-log';
  return apiClient.get<ActivityLog[]>(path);
}
