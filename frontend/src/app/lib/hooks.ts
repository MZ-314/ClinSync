// React hooks that wrap the API client with loading + error state
// and automatic polling for in-flight consultations.

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  getConsultation,
  getFhirRecords,
  listConsultations,
} from './api';
import type {
  ConsultationDetail,
  ConsultationListItem,
  ConsultationStatus,
  FHIRRecordItem,
} from './types';

// Statuses where the pipeline is still doing work — keep polling.
const TERMINAL_STATUSES = new Set<ConsultationStatus>([
  'pending_review',
  'approved',
  'rejected',
  'submitted',
  'failed',
]);

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

function useAsync<T>(
  loader: () => Promise<T>,
  deps: React.DependencyList,
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await loader();
      if (mountedRef.current) {
        setData(result);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : String(err));
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
  }, [run]);

  return { data, loading, error, refetch: run };
}

export function useConsultations(autoRefreshMs = 0) {
  const state = useAsync<ConsultationListItem[]>(
    () => listConsultations({ limit: 50 }),
    [],
  );

  useEffect(() => {
    if (!autoRefreshMs) return;
    const interval = setInterval(() => {
      state.refetch();
    }, autoRefreshMs);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefreshMs]);

  return state;
}

export function useConsultation(
  consultationId: string | undefined,
  pollMs = 2500,
): AsyncState<ConsultationDetail> {
  const [data, setData] = useState<ConsultationDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(!!consultationId);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const fetchOnce = useCallback(async () => {
    if (!consultationId) return;
    try {
      const result = await getConsultation(consultationId);
      if (mountedRef.current) {
        setData(result);
        setError(null);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : String(err));
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [consultationId]);

  useEffect(() => {
    if (!consultationId) {
      setData(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    fetchOnce();
  }, [consultationId, fetchOnce]);

  useEffect(() => {
    if (!consultationId || !pollMs) return;
    const id = setInterval(() => {
      // Stop polling once we reach a terminal state.
      if (data && TERMINAL_STATUSES.has(data.status)) return;
      fetchOnce();
    }, pollMs);
    return () => clearInterval(id);
  }, [consultationId, pollMs, data, fetchOnce]);

  return { data, loading, error, refetch: fetchOnce };
}

export function useFhirRecords(
  consultationId: string | undefined,
): AsyncState<FHIRRecordItem[]> {
  return useAsync<FHIRRecordItem[]>(
    () => (consultationId ? getFhirRecords(consultationId) : Promise.resolve([])),
    [consultationId],
  );
}

// ── Helpers used by the UI ──────────────────────────────────────────────────

export function statusToWorkflowStep(status: ConsultationStatus): number {
  switch (status) {
    case 'uploaded':
      return 1;
    case 'transcribing':
    case 'transcribed':
      return 2;
    case 'extracting':
    case 'extracted':
      return 3;
    case 'coding':
    case 'coded':
      return 4;
    case 'building_fhir':
      return 5;
    case 'pending_review':
      return 6;
    case 'approved':
    case 'submitted':
      return 7;
    case 'rejected':
    case 'failed':
      return 7;
    default:
      return 1;
  }
}

export function statusLabel(status: ConsultationStatus): string {
  return status
    .split('_')
    .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
    .join(' ');
}
