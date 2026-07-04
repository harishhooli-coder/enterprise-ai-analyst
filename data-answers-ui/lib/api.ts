import type {
  ApiResponse,
  AskRequest,
  HealthResponse,
  MetricsSnapshot,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }

  return response.json() as Promise<T>;
}

export function getApiBaseUrl(): string {
  return API_BASE;
}

export async function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export async function fetchMetrics(): Promise<MetricsSnapshot> {
  return request<MetricsSnapshot>("/metrics");
}

export async function askQuestion(body: AskRequest): Promise<ApiResponse> {
  return request<ApiResponse>("/ask", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
