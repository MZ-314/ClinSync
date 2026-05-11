// Centralised API client for the ClinSync backend.
// Base URL is read from the VITE_API_URL env var (set in .env.local for
// development and in Vercel Project Settings for production).

import type {
  ApprovalLogsResponse,
  ApprovalRequest,
  ApprovalResponse,
  ConsultationDetail,
  ConsultationListItem,
  ConsultationUploadResponse,
  FHIRRecordItem,
} from './types';

const RAW_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.trim();

// Fall back to localhost dev backend if env var is missing.
export const API_BASE_URL = (RAW_BASE && RAW_BASE.length > 0
  ? RAW_BASE
  : 'http://127.0.0.1:8000'
).replace(/\/$/, '');

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

async function request<T>(
  path: string,
  init?: RequestInit & { json?: unknown },
): Promise<T> {
  const headers = new Headers(init?.headers);
  let body: BodyInit | undefined = init?.body as BodyInit | undefined;

  if (init?.json !== undefined) {
    headers.set('Content-Type', 'application/json');
    body = JSON.stringify(init.json);
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    body,
  });

  if (!res.ok) {
    let parsed: unknown = undefined;
    let message = `Request failed: ${res.status} ${res.statusText}`;
    try {
      parsed = await res.json();
      if (
        parsed &&
        typeof parsed === 'object' &&
        'detail' in parsed &&
        typeof (parsed as { detail: unknown }).detail === 'string'
      ) {
        message = (parsed as { detail: string }).detail;
      }
    } catch {
      // body not JSON — ignore
    }
    throw new ApiError(res.status, message, parsed);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

// ── Consultations ───────────────────────────────────────────────────────────

export function listConsultations(params?: {
  limit?: number;
  offset?: number;
}): Promise<ConsultationListItem[]> {
  const search = new URLSearchParams();
  if (params?.limit !== undefined) search.set('limit', String(params.limit));
  if (params?.offset !== undefined) search.set('offset', String(params.offset));
  const qs = search.toString();
  return request<ConsultationListItem[]>(
    `/api/v1/consultations/${qs ? `?${qs}` : ''}`,
  );
}

export function getConsultation(
  consultationId: string,
): Promise<ConsultationDetail> {
  return request<ConsultationDetail>(
    `/api/v1/consultations/${consultationId}`,
  );
}

export function uploadConsultation(
  audio: Blob,
  options?: { doctorName?: string; filename?: string },
): Promise<ConsultationUploadResponse> {
  const form = new FormData();
  const filename = options?.filename ?? 'recording.webm';
  form.append('audio', audio, filename);
  if (options?.doctorName) {
    form.append('doctor_name', options.doctorName);
  }
  return request<ConsultationUploadResponse>('/api/v1/consultations/', {
    method: 'POST',
    body: form,
  });
}

export function getFhirRecords(
  consultationId: string,
): Promise<FHIRRecordItem[]> {
  return request<FHIRRecordItem[]>(
    `/api/v1/consultations/${consultationId}/fhir-records`,
  );
}

// ── Approvals ───────────────────────────────────────────────────────────────

export function submitApproval(
  consultationId: string,
  payload: ApprovalRequest,
): Promise<ApprovalResponse> {
  return request<ApprovalResponse>(`/api/v1/approvals/${consultationId}`, {
    method: 'POST',
    json: payload,
  });
}

export function getApprovalLogs(
  consultationId: string,
): Promise<ApprovalLogsResponse> {
  return request<ApprovalLogsResponse>(
    `/api/v1/approvals/${consultationId}/logs`,
  );
}
