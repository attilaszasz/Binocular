export type DeviceStatus = "never_checked" | "up_to_date" | "update_available";

export type ApiErrorCode =
  | "DUPLICATE_NAME"
  | "NOT_FOUND"
  | "VALIDATION_ERROR"
  | "CASCADE_BLOCKED"
  | "NO_LATEST_VERSION"
  | "INTERNAL_ERROR";

export interface DeviceType {
  id: number;
  name: string;
  firmware_source_url: string;
  extension_module_id: number | null;
  check_frequency_minutes: number;
  device_count: number;
  created_at: string;
  updated_at: string;
}

export interface Device {
  id: number;
  device_type_id: number;
  device_type_name: string;
  name: string;
  current_version: string;
  latest_seen_version: string | null;
  last_checked_at: string | null;
  notes: string | null;
  status: DeviceStatus;
  created_at: string;
  updated_at: string;
}

export interface DeviceTypeCreateRequest {
  name: string;
  firmware_source_url: string;
  extension_module_id: number | null;
  check_frequency_minutes: number;
}

export interface DeviceTypeUpdateRequest {
  name?: string;
  firmware_source_url?: string;
  extension_module_id?: number | null;
  check_frequency_minutes?: number;
}

export interface DeviceCreateRequest {
  name: string;
  current_version: string;
  notes?: string;
}

export interface DeviceUpdateRequest {
  name?: string;
  current_version?: string;
  notes?: string;
}

export interface BulkConfirmDetail {
  device_id: number;
  device_name: string;
  error: string;
}

export interface BulkConfirmResponse {
  confirmed: number;
  skipped: number;
  errors: number;
  details: BulkConfirmDetail[];
}

export interface ErrorResponse {
  detail: string;
  error_code: ApiErrorCode;
  field: string | null;
}

export class ApiError extends Error {
  status: number;
  errorCode: ApiErrorCode | null;
  field: string | null;
  diagnostics: string;

  constructor(params: {
    message: string;
    status: number;
    errorCode?: ApiErrorCode | null;
    field?: string | null;
    diagnostics?: string;
  }) {
    super(params.message);
    this.name = "ApiError";
    this.status = params.status;
    this.errorCode = params.errorCode ?? null;
    this.field = params.field ?? null;
    this.diagnostics = params.diagnostics ?? "";
  }
}
