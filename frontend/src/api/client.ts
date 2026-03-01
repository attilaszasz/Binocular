import {
  ApiError,
  type BulkConfirmResponse,
  type Device,
  type DeviceCreateRequest,
  type DeviceType,
  type DeviceTypeCreateRequest,
  type DeviceTypeUpdateRequest,
  type DeviceUpdateRequest,
  type ErrorResponse,
} from "./types";

const API_BASE = "/api/v1";

function toQueryString(params: Record<string, string | number | undefined>): string {
  const entries = Object.entries(params).filter(([, value]) => value !== undefined);
  if (!entries.length) {
    return "";
  }

  const search = new URLSearchParams();
  for (const [key, value] of entries) {
    search.set(key, String(value));
  }
  return `?${search.toString()}`;
}

async function parseJsonSafely(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  const diagnostics = response.headers.get("x-ms-activity-id") ?? "";

  if (!response.ok) {
    const parsed = (await parseJsonSafely(response)) as ErrorResponse | null;
    throw new ApiError({
      message: parsed?.detail ?? `Request failed with status ${response.status}`,
      status: response.status,
      errorCode: parsed?.error_code,
      field: parsed?.field,
      diagnostics,
    });
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function listDeviceTypes(): Promise<DeviceType[]> {
  return apiFetch<DeviceType[]>("/device-types");
}

export async function createDeviceType(payload: DeviceTypeCreateRequest): Promise<DeviceType> {
  return apiFetch<DeviceType>("/device-types", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateDeviceType(
  deviceTypeId: number,
  payload: DeviceTypeUpdateRequest,
): Promise<DeviceType> {
  return apiFetch<DeviceType>(`/device-types/${deviceTypeId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteDeviceType(
  deviceTypeId: number,
  confirmCascade = false,
): Promise<void> {
  const query = toQueryString({ confirm_cascade: confirmCascade ? "true" : undefined });
  return apiFetch<void>(`/device-types/${deviceTypeId}${query}`, {
    method: "DELETE",
  });
}

export async function listDevices(params?: {
  device_type_id?: number;
  status?: string;
  sort?: "name" | "-name" | "last_checked_at" | "-last_checked_at";
}): Promise<Device[]> {
  const query = toQueryString({
    device_type_id: params?.device_type_id,
    status: params?.status,
    sort: params?.sort,
  });
  return apiFetch<Device[]>(`/devices${query}`);
}

export async function createDevice(
  deviceTypeId: number,
  payload: DeviceCreateRequest,
): Promise<Device> {
  return apiFetch<Device>(`/device-types/${deviceTypeId}/devices`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateDevice(
  deviceId: number,
  payload: DeviceUpdateRequest,
): Promise<Device> {
  return apiFetch<Device>(`/devices/${deviceId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteDevice(deviceId: number): Promise<void> {
  return apiFetch<void>(`/devices/${deviceId}`, {
    method: "DELETE",
  });
}

export async function confirmDevice(deviceId: number): Promise<Device> {
  return apiFetch<Device>(`/devices/${deviceId}/confirm`, {
    method: "POST",
  });
}

export async function confirmAllDevices(deviceTypeId?: number): Promise<BulkConfirmResponse> {
  const query = toQueryString({ device_type_id: deviceTypeId });
  return apiFetch<BulkConfirmResponse>(`/devices/confirm-all${query}`, {
    method: "POST",
  });
}
