/**
 * HTTP API client for the Binocular backend.
 */

const API_BASE = "/api/v1";

/** Typed fetch wrapper with automatic JSON parsing and error handling. */
async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/* ── Device types ─────────────────────────────────────────────── */

export interface Device {
  id: number;
  name: string;
  model: string;
  module_id: number;
  module_name: string;
  device_type: string;
  current_version: string;
  has_update: boolean;
  latest_detected_version: string | null;
  last_checked: string | null;
  last_notified_version: string | null;
  created_at: string;
  updated_at: string;
}

export interface DeviceCreate {
  name: string;
  model?: string;
  module_id: number;
  current_version?: string;
}

export interface DeviceUpdate {
  name?: string;
  model?: string;
  module_id?: number;
  current_version?: string;
}

export interface Module {
  id: number;
  name: string;
  device_type: string;
}

/* ── Device API ───────────────────────────────────────────────── */

export const devicesApi = {
  list: () => apiFetch<Device[]>("/devices"),
  get: (id: number) => apiFetch<Device>(`/devices/${id}`),
  create: (data: DeviceCreate) =>
    apiFetch<Device>("/devices", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: number, data: DeviceUpdate) =>
    apiFetch<Device>(`/devices/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: number) =>
    apiFetch<void>(`/devices/${id}`, { method: "DELETE" }),
  confirm: (id: number) =>
    apiFetch<Device>(`/devices/${id}/confirm`, { method: "PUT" }),
};

/* ── Module API ───────────────────────────────────────────────── */

export const modulesApi = {
  list: () => apiFetch<Module[]>("/modules"),
};
