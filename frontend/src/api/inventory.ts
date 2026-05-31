import { apiClient } from './client';

export type DeviceStatus = 'never_checked' | 'check_failed' | 'update_available' | 'up_to_date';

export type InventoryDevice = {
  id: number;
  deviceTypeId: number;
  deviceType: string;
  name: string;
  model: string;
  currentVersion: string;
  latestVersion: string | null;
  lastCheckedAt: string | null;
  lastSuccessAt: string | null;
  status: DeviceStatus;
  createdAt: string;
  updatedAt: string;
};

export type DeviceGroup = {
  id: number;
  name: string;
  count: number;
  devices: InventoryDevice[];
};

export type InventoryResponse = {
  groups: DeviceGroup[];
};

export type DeviceInput = {
  name: string;
  model: string;
  deviceType: string;
  currentVersion: string;
};

export function listInventory() {
  return apiClient.get<InventoryResponse>('/inventory');
}

export function createDevice(payload: DeviceInput) {
  return apiClient.request<InventoryDevice>('/inventory', { method: 'POST', body: payload });
}

export function updateDevice(deviceId: number, payload: DeviceInput) {
  return apiClient.request<InventoryDevice>(`/inventory/${deviceId}`, { method: 'PATCH', body: payload });
}

export function archiveDevice(deviceId: number) {
  return apiClient.request<void>(`/inventory/${deviceId}`, { method: 'DELETE' });
}

export function confirmDeviceUpdate(deviceId: number) {
  return apiClient.request<InventoryDevice>(`/inventory/${deviceId}/confirm-update`, { method: 'POST' });
}