import { apiClient } from './client';

export type DeviceTypeSchedule = {
  deviceTypeId: number;
  deviceType: string;
  enabled: boolean;
  intervalMinutes: number;
  nextRunAt: string | null;
  lastStartedAt: string | null;
  lastCompletedAt: string | null;
  lastSuccessAt: string | null;
  lastFailureAt: string | null;
  lastFailureReason: string | null;
  lastSkipReason: string | null;
};

export type ScheduleListResponse = {
  schedules: DeviceTypeSchedule[];
};

export type ScheduleUpdateRequest = {
  enabled: boolean;
  intervalMinutes: number;
};

export function listSchedules() {
  return apiClient.get<ScheduleListResponse>('/schedules');
}

export function updateSchedule(deviceTypeId: number, payload: ScheduleUpdateRequest) {
  return apiClient.request<DeviceTypeSchedule>(`/schedules/device-types/${deviceTypeId}`, {
    method: 'PUT',
    body: payload,
  });
}
