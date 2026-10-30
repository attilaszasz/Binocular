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

export type ComparisonStatus =
  | "unverified" | "unknown" | "comparison_unknown" | "current"
  | "update_available" | "no_firmware" | "stale" | "failed";

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
  last_check_attempt_at?: string | null;
  last_notified_version: string | null;
  created_at: string;
  updated_at: string;
  /** Additive fields are optional for compatibility with pre-catalog responses. */
  catalog_model_id?: string | null;
  catalog_link_state?: "legacy" | "unresolved" | "linked";
  installed_unknown?: boolean;
  revision?: number;
  comparison_status?: ComparisonStatus;
}

/** Absence of an update flag is not evidence of a successful comparison. */
export function deviceComparisonStatus(device: Device): ComparisonStatus {
  if (device.installed_unknown || !device.current_version.trim()) return "unknown";
  if (device.comparison_status) return device.comparison_status;
  // Older V1 responses do not carry comparison status. Only retain explicit
  // update evidence or a checked exact match; never infer current from !has_update.
  if (device.latest_detected_version?.trim()) {
    // Be conservative without backend comparison metadata; opaque versions
    // must not become current just because their display strings match.
    const numericVersion = /^\d+(?:[._-]\d+)*$/;
    if (!numericVersion.test(device.current_version) || !numericVersion.test(device.latest_detected_version))
      return "comparison_unknown";
    if (device.has_update) return "update_available";
    if (device.last_checked && device.current_version === device.latest_detected_version)
      return "current";
  }
  return "unverified";
}

export interface DeviceCreate {
  name: string;
  model?: string;
  module_id: number;
  current_version?: string;
  installed_unknown?: boolean;
}

export interface DeviceUpdate {
  name?: string;
  model?: string;
  module_id?: number;
  current_version?: string;
  installed_unknown?: boolean;
  expected_revision?: number;
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
  consecutive_failures?: number;
  last_success?: string | null;
  source_url: string;
  display_name?: string;
  coverage_notes?: string;
  model_examples?: string[];
  help_url?: string;
  guidance_provenance?: "verified_official" | "custom" | "legacy";
  linked_device_count?: number;
}

export interface ScopeResponse {
  module_id: number;
  linked_device_count: number;
  devices: { id: number; name: string; model: string }[];
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
  confirm: (id: number, expectedRevision?: number) =>
    apiFetch<Device>(`/devices/${id}/confirm${expectedRevision === undefined ? "" : `?expected_revision=${expectedRevision}`}`, { method: "PUT" }),
};

/* ── Module API ───────────────────────────────────────────────── */

export const modulesApi = {
  devices: (id: number) => apiFetch<ScopeResponse>(`/modules/${id}/devices`),
  list: () => apiFetch<Module[]>("/modules"),
  upload: async (file: File, runPhase2: boolean = false): Promise<Response> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/modules?run_phase2=${runPhase2}`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      const message = typeof body.detail === "object" ? JSON.stringify(body.detail) : (body.detail ?? res.statusText);
      throw new ApiError(res.status, message, body);
    }
    return res;
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
  searchVersion: (moduleId: number, model: string) =>
    apiFetch<{ version: string }>("/checks/search-version", {
      method: "POST",
      body: JSON.stringify({ module_id: moduleId, model }),
    }),
};


/* ── Schedules API ────────────────────────────────────────────── */

export interface Schedule {
  module_id: number;
  module_name: string;
  device_type: string;
  interval_hours: number;
  last_run: string | null;
  next_run: string | null;
}

export const schedulesApi = {
  list: () => apiFetch<Schedule[]>("/schedules"),
  update: (moduleId: number, intervalHours: number) =>
    apiFetch<Schedule>("/schedules", {
      method: "PUT",
      body: JSON.stringify({ module_id: moduleId, interval_hours: intervalHours }),
    }),
};

/* ── Notifications API ────────────────────────────────────────── */

export interface NotificationChannel {
  type: string;
  enabled: boolean;
  config: Record<string, unknown>;
}

export const notificationsApi = {
  list: () => apiFetch<NotificationChannel[]>("/notifications"),
  save: (data: NotificationChannel) =>
    apiFetch<NotificationChannel>("/notifications", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  test: (data: { type: string; config: Record<string, unknown> }) =>
    apiFetch<{ success: boolean; message: string }>("/notifications/test", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

/* ── Activity API ─────────────────────────────────────────────── */

export interface ActivityLogEntry {
  id: number;
  timestamp: string;
  level: string;
  category: string;
  message: string;
  device_id: number | null;
  device_name: string | null;
  module_name: string | null;
  traceback: string | null;
}

export interface ActivityLogListResponse {
  items: ActivityLogEntry[];
  total: number;
}

export interface ActivityQueryParams {
  level?: string;
  category?: string;
  device_id?: number;
  limit?: number;
  offset?: number;
}

export const activityApi = {
  list: (params: ActivityQueryParams = {}) => {
    const query = new URLSearchParams();
    if (params.level) query.append("level", params.level);
    if (params.category) query.append("category", params.category);
    if (params.device_id) query.append("device_id", String(params.device_id));
    if (params.limit !== undefined) query.append("limit", String(params.limit));
    if (params.offset !== undefined) query.append("offset", String(params.offset));

    const queryString = query.toString();
    return apiFetch<ActivityLogListResponse>(`/activity${queryString ? `?${queryString}` : ""}`);
  },
};
