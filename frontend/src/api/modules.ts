import { apiClient } from './client';

export type ValidationFinding = {
  code: string;
  message: string;
};

export type ValidationPhase = {
  phase: 'static' | 'runtime';
  status: 'passed' | 'failed' | 'skipped';
  findings: ValidationFinding[];
  message?: string | null;
};

export type ModuleValidationSummary = {
  overall_status: 'valid' | 'invalid';
  static_phase: ValidationPhase;
  runtime_phase: ValidationPhase;
};

export type InstalledModule = {
  moduleId: string;
  displayName: string;
  author: string | null;
  version: string | null;
  status: 'installed' | 'disabled';
  validationStatus: 'unvalidated' | 'valid' | 'invalid';
  validationSummary: ModuleValidationSummary;
  sourceHash: string;
  lastValidatedAt: string | null;
  createdAt: string;
  updatedAt: string;
};

export type ModuleListResponse = {
  modules: InstalledModule[];
};

export class ModuleUploadError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly validationSummary: ModuleValidationSummary | null,
  ) {
    super(message);
    this.name = 'ModuleUploadError';
  }
}

export function listModules() {
  return apiClient.get<ModuleListResponse>('/modules');
}

export async function uploadModule(file: File) {
  const body = new FormData();
  body.append('file', file);
  const response = await fetch('/api/v1/modules', {
    method: 'POST',
    headers: { Accept: 'application/json' },
    body,
  });
  if (!response.ok) {
    throw await moduleUploadError(response);
  }
  return (await response.json()) as InstalledModule;
}

export function deleteModule(moduleId: string) {
  return apiClient.request<void>(`/modules/${encodeURIComponent(moduleId)}`, { method: 'DELETE' });
}

async function moduleUploadError(response: Response) {
  const payload = (await response.json().catch(() => null)) as {
    detail?: {
      code?: string;
      detail?: string;
      validationSummary?: ModuleValidationSummary | null;
    };
  } | null;
  const detail = payload?.detail;
  return new ModuleUploadError(
    response.status,
    detail?.code ?? 'upload_failed',
    detail?.detail ?? `Request failed with status ${response.status}`,
    detail?.validationSummary ?? null,
  );
}