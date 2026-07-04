export type ResponseStatus = "ok" | "needs_clarification" | "declined" | "error";

export interface UserPrincipal {
  user_id: string;
  allowed_regions: string[];
  email?: string;
}

export interface AskRequest {
  question: string;
  user_principal: UserPrincipal;
}

export interface AnswerPayload {
  answer: string;
  resolved_interpretation: string;
  source: string;
  confidence: number;
}

export interface ApiResponse {
  status: ResponseStatus;
  data: AnswerPayload | null;
  clarification: string | null;
  decline_reason: string | null;
  request_id: string;
  error: string | null;
}

export interface HealthResponse {
  status: string;
}

export interface MetricsSnapshot {
  agent_requests_total?: Record<string, number>;
  agent_clarifications_total?: number;
  agent_declines_total?: Record<string, number>;
  agent_latency_ms_avg?: number;
  agent_bytes_scanned_avg?: number;
  deflection_rate?: number;
  clarification_rate?: number;
}

export interface ExampleScenario {
  label: string;
  description: string;
  question: string;
  userId: string;
  regions: string;
}
