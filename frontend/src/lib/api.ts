/**
 * HTTP API client for the Binocular backend.
 */

const API_BASE = "/api/v1";

/** Typed fetch wrapper with automatic JSON parsing and error handling. */
async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {};
  if (!(init?.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (init?.headers) {
    Object.assign(headers, init.headers);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    headers,
    ...init,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const message = typeof body.detail === "object" ? JSON.stringify(body.detail) : (body.detail ?? res.statusText);
    throw new ApiError(res.status, message, body);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
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
  version: string;
  author: string;
  file_path: string;
  is_official: boolean;
  status: string;
  created_at: string;
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
  upload: (file: File, runPhase2: boolean = false) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiFetch<Module>(`/modules?run_phase2=${runPhase2}`, {
      method: "POST",
      body: formData,
    });
  },
  update: (id: number, status: string) =>
    apiFetch<Module>(`/modules/${id}`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    }),
  delete: (id: number) =>
    apiFetch<void>(`/modules/${id}`, { method: "DELETE" }),
};

/* ── Checks API ───────────────────────────────────────────────── */

export interface DeviceCheckResult {
  device_id: number;
  module_id: number;
  latest_version: string | null;
  current_version: string;
  has_update: boolean;
  checked_at: string;
  success: boolean;
  error_message: string | null;
}

export const checksApi = {
  checkDevice: (id: number) =>
    apiFetch<DeviceCheckResult>(`/checks/device/${id}`, { method: "POST" }),
  checkBulk: () =>
    apiFetch<DeviceCheckResult[]>("/checks/bulk", { method: "POST" }),
};

