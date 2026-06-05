import { apiClient } from './client';

export type CheckStatus = 'up_to_date' | 'update_available' | 'failed';

export type CheckResult = {
  deviceId: number;
  moduleId: string;
  status: CheckStatus;
  currentVersion: string;
  latestVersion: string | null;
  lastCheckedAt: string | null;
  lastSuccessAt: string | null;
  sourceUrl: string | null;
  detail: string | null;
  diagnostics: Record<string, unknown>;
};

export type RunCheckInput = {
  moduleId: string;
  sourceUrl?: string | null;
  extra?: Record<string, string>;
};

export type RunAllChecksInput = {
  moduleId?: string | null;
  sourceUrl?: string | null;
  extra?: Record<string, string>;
  maxConcurrency?: number | null;
};

export type BulkCheckResponse = {
  results: CheckResult[];
  total: number;
  succeeded: number;
  failed: number;
};

export function runDeviceCheck(deviceId: number, payload: RunCheckInput) {
  return apiClient.request<CheckResult>(`/checks/devices/${deviceId}`, { method: 'POST', body: payload });
}

export function runAllChecks(payload: RunAllChecksInput) {
  return apiClient.request<BulkCheckResponse>('/checks/all', { method: 'POST', body: payload });
}
