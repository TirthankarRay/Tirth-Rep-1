import type {
  OverviewMetrics,
  TimeToTreatmentResponse,
  TreatmentPatternsResponse,
  GeographicResponse,
  PatientListResponse,
  SankeyResponse,
} from "../types/index";
import {
  mockOverviewMetrics,
  mockTimeToTreatment,
  mockTreatmentPatterns,
  mockGeographicData,
  mockPatients,
  mockSankeyData,
} from "./mockData";

const API_BASE = import.meta.env.VITE_API_URL || "";
const USE_MOCK = true; // Toggle to false when backend is running

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchOverviewMetrics(
  stage?: string | null,
  state?: string | null
): Promise<OverviewMetrics> {
  if (USE_MOCK) return mockOverviewMetrics;
  const params = new URLSearchParams();
  if (stage) params.set("stage", stage);
  if (state) params.set("state", state);
  return fetchJson(`/api/v1/metrics/overview?${params}`);
}

export async function fetchTimeToTreatment(
  stage?: string | null,
  state?: string | null
): Promise<TimeToTreatmentResponse> {
  if (USE_MOCK) return mockTimeToTreatment;
  const params = new URLSearchParams();
  if (stage) params.set("stage", stage);
  if (state) params.set("state", state);
  return fetchJson(`/api/v1/metrics/time-to-treatment?${params}`);
}

export async function fetchTreatmentPatterns(
  stage?: string | null
): Promise<TreatmentPatternsResponse> {
  if (USE_MOCK) return mockTreatmentPatterns;
  const params = new URLSearchParams();
  if (stage) params.set("stage", stage);
  return fetchJson(`/api/v1/metrics/treatment-patterns?${params}`);
}

export async function fetchGeographicData(): Promise<GeographicResponse> {
  if (USE_MOCK) return mockGeographicData;
  return fetchJson("/api/v1/geographic/states");
}

export async function fetchPatients(
  page: number = 1,
  pageSize: number = 25,
  stage?: string | null,
  state?: string | null
): Promise<PatientListResponse> {
  if (USE_MOCK) {
    const start = (page - 1) * pageSize;
    const items = mockPatients.slice(start, start + pageSize);
    return {
      items,
      total: mockPatients.length,
      page,
      page_size: pageSize,
    };
  }
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (stage) params.set("stage", stage);
  if (state) params.set("state", state);
  return fetchJson(`/api/v1/patients?${params}`);
}

export async function fetchSankeyData(
  stage?: string | null
): Promise<SankeyResponse> {
  if (USE_MOCK) return mockSankeyData;
  const params = new URLSearchParams();
  if (stage) params.set("stage", stage);
  return fetchJson(`/api/v1/patients/journey/sankey?${params}`);
}
