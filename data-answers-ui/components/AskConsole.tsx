"use client";

import { useCallback, useEffect, useState } from "react";

import { askQuestion, fetchHealth, fetchMetrics, getApiBaseUrl } from "@/lib/api";
import { EXAMPLE_SCENARIOS } from "@/lib/examples";
import type { ApiResponse, MetricsSnapshot, ResponseStatus } from "@/lib/types";

const STATUS_STYLES: Record<
  ResponseStatus,
  { label: string; badge: string; panel: string }
> = {
  ok: {
    label: "Answer",
    badge: "bg-emerald-100 text-emerald-800 ring-emerald-200",
    panel: "border-emerald-200 bg-emerald-50/70",
  },
  needs_clarification: {
    label: "Needs clarification",
    badge: "bg-amber-100 text-amber-900 ring-amber-200",
    panel: "border-amber-200 bg-amber-50/70",
  },
  declined: {
    label: "Declined",
    badge: "bg-rose-100 text-rose-900 ring-rose-200",
    panel: "border-rose-200 bg-rose-50/70",
  },
  error: {
    label: "Error",
    badge: "bg-slate-200 text-slate-800 ring-slate-300",
    panel: "border-slate-300 bg-slate-50",
  },
};

function parseRegions(value: string): string[] {
  return value
    .split(",")
    .map((region) => region.trim())
    .filter(Boolean);
}

function formatPercent(value: number | undefined): string {
  if (value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export default function AskConsole() {
  const [question, setQuestion] = useState("What was total revenue last month?");
  const [userId, setUserId] = useState("u1");
  const [regions, setRegions] = useState("US, EU");
  const [email, setEmail] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ApiResponse | null>(null);

  const [health, setHealth] = useState<"checking" | "ok" | "down">("checking");
  const [metrics, setMetrics] = useState<MetricsSnapshot | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      const [healthResult, metricsResult] = await Promise.all([
        fetchHealth(),
        fetchMetrics(),
      ]);
      setHealth(healthResult.status === "ok" ? "ok" : "down");
      setMetrics(metricsResult);
    } catch {
      setHealth("down");
      setMetrics(null);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadStatus() {
      try {
        const [healthResult, metricsResult] = await Promise.all([
          fetchHealth(),
          fetchMetrics(),
        ]);
        if (cancelled) return;
        setHealth(healthResult.status === "ok" ? "ok" : "down");
        setMetrics(metricsResult);
      } catch {
        if (!cancelled) {
          setHealth("down");
          setMetrics(null);
        }
      }
    }

    void loadStatus();

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await askQuestion({
        question: question.trim(),
        user_principal: {
          user_id: userId.trim(),
          allowed_regions: parseRegions(regions),
          ...(email.trim() ? { email: email.trim() } : {}),
        },
      });
      setResponse(result);
      await refreshStatus();
    } catch (err) {
      setResponse(null);
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  function applyExample(example: (typeof EXAMPLE_SCENARIOS)[number]) {
    setQuestion(example.question);
    setUserId(example.userId);
    setRegions(example.regions);
    setError(null);
    setResponse(null);
  }

  const statusStyle = response ? STATUS_STYLES[response.status] : null;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-10 sm:px-6 lg:px-8">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-500">
            IF-RES-2026-061
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
            Data-Answers Test Console
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Ask grounded business questions against the walking-skeleton API. This UI is a
            developer harness only — no SQL or schema details are shown in responses.
          </p>
        </div>
        <div className="flex flex-col items-start gap-2 text-sm sm:items-end">
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 shadow-sm">
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                health === "ok"
                  ? "bg-emerald-500"
                  : health === "checking"
                    ? "bg-amber-400 animate-pulse"
                    : "bg-rose-500"
              }`}
            />
            <span className="font-medium text-slate-700">
              API {health === "ok" ? "healthy" : health === "checking" ? "checking…" : "unreachable"}
            </span>
          </div>
          <p className="font-mono text-xs text-slate-500">{getApiBaseUrl()}</p>
        </div>
      </header>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
        <section className="space-y-6">
          <form
            onSubmit={handleSubmit}
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            <div className="space-y-5">
              <div>
                <label htmlFor="question" className="mb-2 block text-sm font-medium text-slate-700">
                  Question
                </label>
                <textarea
                  id="question"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  rows={4}
                  required
                  className="w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:bg-white focus:ring-2 focus:ring-slate-200"
                  placeholder="What was total revenue last month?"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="userId" className="mb-2 block text-sm font-medium text-slate-700">
                    User ID
                  </label>
                  <input
                    id="userId"
                    value={userId}
                    onChange={(event) => setUserId(event.target.value)}
                    required
                    className="w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2.5 text-sm outline-none transition focus:border-slate-500 focus:bg-white focus:ring-2 focus:ring-slate-200"
                  />
                </div>
                <div>
                  <label htmlFor="regions" className="mb-2 block text-sm font-medium text-slate-700">
                    Allowed regions
                  </label>
                  <input
                    id="regions"
                    value={regions}
                    onChange={(event) => setRegions(event.target.value)}
                    className="w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2.5 text-sm outline-none transition focus:border-slate-500 focus:bg-white focus:ring-2 focus:ring-slate-200"
                    placeholder="US, EU"
                  />
                  <p className="mt-1 text-xs text-slate-500">Comma-separated. Leave empty to test policy deny.</p>
                </div>
              </div>

              <div>
                <label htmlFor="email" className="mb-2 block text-sm font-medium text-slate-700">
                  Email (optional)
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2.5 text-sm outline-none transition focus:border-slate-500 focus:bg-white focus:ring-2 focus:ring-slate-200"
                  placeholder="alice@corp.com"
                />
              </div>
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={loading || health === "down"}
                className="inline-flex items-center justify-center rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                {loading ? "Asking…" : "Ask question"}
              </button>
              <button
                type="button"
                onClick={() => void refreshStatus()}
                className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
              >
                Refresh status
              </button>
            </div>
          </form>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Example scenarios
            </h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {EXAMPLE_SCENARIOS.map((example) => (
                <button
                  key={example.label}
                  type="button"
                  onClick={() => applyExample(example)}
                  className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-left transition hover:border-slate-300 hover:bg-white"
                >
                  <p className="text-sm font-medium text-slate-900">{example.label}</p>
                  <p className="mt-1 text-xs text-slate-500">{example.description}</p>
                </button>
              ))}
            </div>
          </div>

          {(error || response) && (
            <div
              className={`rounded-2xl border p-6 shadow-sm ${
                error ? "border-rose-200 bg-rose-50/70" : statusStyle?.panel
              }`}
            >
              {error ? (
                <div>
                  <p className="text-sm font-semibold text-rose-900">Request failed</p>
                  <p className="mt-2 text-sm text-rose-800">{error}</p>
                  <p className="mt-3 text-xs text-rose-700">
                    Make sure the API is running:{" "}
                    <code className="rounded bg-white/80 px-1.5 py-0.5">
                      uvicorn app.main:app --reload --port 8000
                    </code>
                  </p>
                </div>
              ) : response && statusStyle ? (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <span
                      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ${statusStyle.badge}`}
                    >
                      {statusStyle.label}
                    </span>
                    <span className="font-mono text-xs text-slate-500">
                      request_id: {response.request_id}
                    </span>
                  </div>

                  {response.status === "ok" && response.data && (
                    <div className="space-y-4">
                      <p className="text-lg leading-8 text-slate-900">{response.data.answer}</p>
                      <dl className="grid gap-3 rounded-xl border border-white/80 bg-white/70 p-4 text-sm sm:grid-cols-2">
                        <div>
                          <dt className="font-medium text-slate-500">Source metric</dt>
                          <dd className="mt-1 font-mono text-slate-900">{response.data.source}</dd>
                        </div>
                        <div>
                          <dt className="font-medium text-slate-500">Confidence</dt>
                          <dd className="mt-1 text-slate-900">
                            {(response.data.confidence * 100).toFixed(0)}%
                          </dd>
                        </div>
                        <div className="sm:col-span-2">
                          <dt className="font-medium text-slate-500">Resolved interpretation</dt>
                          <dd className="mt-1 text-slate-900">{response.data.resolved_interpretation}</dd>
                        </div>
                      </dl>
                    </div>
                  )}

                  {response.status === "needs_clarification" && response.clarification && (
                    <p className="text-sm leading-7 text-amber-950">{response.clarification}</p>
                  )}

                  {response.status === "declined" && response.decline_reason && (
                    <p className="text-sm leading-7 text-rose-950">{response.decline_reason}</p>
                  )}

                  {response.status === "error" && response.error && (
                    <p className="text-sm leading-7 text-slate-800">{response.error}</p>
                  )}
                </div>
              ) : null}
            </div>
          )}
        </section>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              API metrics
            </h2>
            {metrics ? (
              <dl className="mt-4 space-y-3 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-slate-500">Deflection rate</dt>
                  <dd className="font-medium text-slate-900">
                    {formatPercent(metrics.deflection_rate)}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-slate-500">Clarification rate</dt>
                  <dd className="font-medium text-slate-900">
                    {formatPercent(metrics.clarification_rate)}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-slate-500">Avg latency</dt>
                  <dd className="font-medium text-slate-900">
                    {metrics.agent_latency_ms_avg != null
                      ? `${metrics.agent_latency_ms_avg} ms`
                      : "—"}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-slate-500">Avg bytes scanned</dt>
                  <dd className="font-medium text-slate-900">
                    {metrics.agent_bytes_scanned_avg != null
                      ? Math.round(metrics.agent_bytes_scanned_avg).toLocaleString()
                      : "—"}
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="mt-4 text-sm text-slate-500">Metrics unavailable until the API is reachable.</p>
            )}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-900 p-6 text-slate-100 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
              Quick start
            </h2>
            <ol className="mt-4 space-y-3 text-sm leading-6 text-slate-300">
              <li>1. Start the API on port 8000.</li>
              <li>2. Run this UI on port 3000.</li>
              <li>3. Pick an example or type your own question.</li>
              <li>4. Inspect status, provenance, and metrics.</li>
            </ol>
          </div>
        </aside>
      </div>
    </div>
  );
}
