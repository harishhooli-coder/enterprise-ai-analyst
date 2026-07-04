"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { askQuestion, fetchHealth, fetchMetrics, getApiBaseUrl } from "@/lib/api";
import { EXAMPLE_SCENARIOS, SUGGESTED_PROMPTS } from "@/lib/examples";
import type { ApiResponse, MetricsSnapshot, ResponseStatus } from "@/lib/types";

const STATUS_STYLES: Record<
  ResponseStatus,
  { label: string; headline: string; badge: string; panel: string; icon: string }
> = {
  ok: {
    label: "Answer",
    headline: "Here's what we found",
    badge: "bg-emerald-100 text-emerald-800 ring-emerald-200",
    panel: "border-emerald-200 bg-white shadow-emerald-100/50",
    icon: "✓",
  },
  needs_clarification: {
    label: "Need more detail",
    headline: "Could you clarify?",
    badge: "bg-amber-100 text-amber-900 ring-amber-200",
    panel: "border-amber-200 bg-white shadow-amber-100/50",
    icon: "?",
  },
  declined: {
    label: "Can't answer yet",
    headline: "This question is outside scope",
    badge: "bg-rose-100 text-rose-900 ring-rose-200",
    panel: "border-rose-200 bg-white shadow-rose-100/50",
    icon: "—",
  },
  error: {
    label: "Something went wrong",
    headline: "We couldn't complete your request",
    badge: "bg-slate-200 text-slate-800 ring-slate-300",
    panel: "border-slate-300 bg-white shadow-slate-100/50",
    icon: "!",
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

function confidenceLabel(value: number): string {
  if (value >= 0.9) return "High confidence";
  if (value >= 0.7) return "Moderate confidence";
  return "Lower confidence";
}

export default function AskConsole() {
  const [question, setQuestion] = useState("");
  const [userId, setUserId] = useState("u1");
  const [regions, setRegions] = useState("US, EU");
  const [email, setEmail] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showDevPanel, setShowDevPanel] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ApiResponse | null>(null);
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);

  const [health, setHealth] = useState<"checking" | "ok" | "down">("checking");
  const [metrics, setMetrics] = useState<MetricsSnapshot | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const responseRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    if (response || error) {
      responseRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [response, error]);

  async function handleSubmit(event?: React.FormEvent) {
    event?.preventDefault();

    const trimmed = question.trim();
    if (!trimmed || loading || health === "down") return;

    setLoading(true);
    setError(null);
    setLastQuestion(trimmed);

    try {
      const result = await askQuestion({
        question: trimmed,
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
    setLastQuestion(null);
    textareaRef.current?.focus();
  }

  function applyPrompt(prompt: string) {
    setQuestion(prompt);
    setError(null);
    setResponse(null);
    setLastQuestion(null);
    textareaRef.current?.focus();
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      void handleSubmit();
    }
  }

  const statusStyle = response ? STATUS_STYLES[response.status] : null;
  const hasResult = Boolean(error || response);
  const apiUnavailable = health === "down";

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col px-4 py-8 sm:px-6 sm:py-12">
      <header className="mb-8 text-center sm:mb-10">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-600 text-lg font-semibold text-white shadow-lg shadow-indigo-200">
          DA
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
          Data Answers
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-base leading-relaxed text-slate-600">
          Ask questions about your business data in plain English. Answers come from verified
          metrics — not guesses.
        </p>

        {apiUnavailable && (
          <div
            role="alert"
            className="mx-auto mt-5 max-w-lg rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
          >
            <p className="font-medium">Service unavailable</p>
            <p className="mt-1 text-rose-700">
              The answer service isn&apos;t reachable right now. Make sure the API is running on
              port 8000, then refresh this page.
            </p>
          </div>
        )}
      </header>

      {!hasResult && !loading && (
        <section className="animate-fade-in-up mb-8 rounded-2xl border border-dashed border-slate-200 bg-white/70 px-5 py-6 text-center">
          <p className="text-sm font-medium text-slate-700">Try asking something like</p>
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            {SUGGESTED_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => applyPrompt(prompt)}
                className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-900"
              >
                {prompt}
              </button>
            ))}
          </div>
        </section>
      )}

      <form
        onSubmit={(event) => void handleSubmit(event)}
        className="sticky bottom-4 z-10 rounded-2xl border border-slate-200 bg-white p-4 shadow-lg shadow-slate-200/60 sm:p-5"
      >
        <label htmlFor="question" className="sr-only">
          Your question
        </label>
        <textarea
          ref={textareaRef}
          id="question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={handleKeyDown}
          rows={3}
          required
          disabled={loading || apiUnavailable}
          className="w-full resize-none rounded-xl border-0 bg-slate-50 px-4 py-3 text-base text-slate-900 outline-none transition placeholder:text-slate-400 focus:bg-white focus:ring-2 focus:ring-indigo-200 disabled:cursor-not-allowed disabled:opacity-60"
          placeholder="What was total revenue last month?"
        />

        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-slate-500">
            Press <kbd className="rounded border border-slate-200 bg-slate-100 px-1.5 py-0.5 font-mono text-[11px]">Ctrl</kbd>
            {" + "}
            <kbd className="rounded border border-slate-200 bg-slate-100 px-1.5 py-0.5 font-mono text-[11px]">Enter</kbd>
            {" to send"}
          </p>
          <button
            type="submit"
            disabled={loading || apiUnavailable || !question.trim()}
            className="inline-flex min-w-[120px] items-center justify-center rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {loading ? "Thinking…" : "Ask"}
          </button>
        </div>
      </form>

      {loading && (
        <div className="animate-fade-in-up mt-6 flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
          <div className="flex gap-1" aria-hidden="true">
            <span className="thinking-dot h-2 w-2 rounded-full bg-indigo-500" />
            <span className="thinking-dot h-2 w-2 rounded-full bg-indigo-500" />
            <span className="thinking-dot h-2 w-2 rounded-full bg-indigo-500" />
          </div>
          <p className="text-sm text-slate-600">Looking up your answer…</p>
        </div>
      )}

      <div ref={responseRef} className="mt-6 space-y-4">
        {error && (
          <div
            role="alert"
            className="animate-fade-in-up rounded-2xl border border-rose-200 bg-white p-6 shadow-sm"
          >
            <p className="text-sm font-semibold text-rose-900">Couldn&apos;t reach the service</p>
            <p className="mt-2 text-sm leading-relaxed text-rose-800">{error}</p>
            <p className="mt-3 text-xs text-rose-700">
              If you&apos;re running locally, start the API with{" "}
              <code className="rounded bg-rose-50 px-1.5 py-0.5 font-mono">
                uvicorn app.main:app --reload --port 8000
              </code>
            </p>
          </div>
        )}

        {response && statusStyle && (
          <article
            className={`animate-fade-in-up rounded-2xl border p-6 shadow-sm ${statusStyle.panel}`}
          >
            {lastQuestion && (
              <p className="mb-4 text-sm text-slate-500">
                <span className="font-medium text-slate-700">You asked:</span>{" "}
                &ldquo;{lastQuestion}&rdquo;
              </p>
            )}

            <div className="flex items-start gap-3">
              <span
                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold ring-1 ring-inset ${statusStyle.badge}`}
                aria-hidden="true"
              >
                {statusStyle.icon}
              </span>
              <div className="min-w-0 flex-1 space-y-4">
                <div>
                  <span
                    className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${statusStyle.badge}`}
                  >
                    {statusStyle.label}
                  </span>
                  <h2 className="mt-2 text-lg font-semibold text-slate-900">
                    {statusStyle.headline}
                  </h2>
                </div>

                {response.status === "ok" && response.data && (
                  <div className="space-y-4">
                    <p className="text-xl leading-8 text-slate-900">{response.data.answer}</p>
                    <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-4">
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                        How we interpreted this
                      </p>
                      <p className="mt-2 text-sm leading-relaxed text-slate-700">
                        {response.data.resolved_interpretation}
                      </p>
                      <div className="mt-4 flex flex-wrap gap-3 text-sm">
                        <span className="rounded-full bg-white px-3 py-1 text-slate-600 ring-1 ring-slate-200">
                          {confidenceLabel(response.data.confidence)} ·{" "}
                          {(response.data.confidence * 100).toFixed(0)}%
                        </span>
                        <span className="rounded-full bg-white px-3 py-1 font-mono text-xs text-slate-600 ring-1 ring-slate-200">
                          {response.data.source}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {response.status === "needs_clarification" && response.clarification && (
                  <div className="rounded-xl border border-amber-100 bg-amber-50/60 p-4">
                    <p className="text-sm leading-relaxed text-amber-950">
                      {response.clarification}
                    </p>
                    <p className="mt-3 text-xs text-amber-800">
                      Edit your question above and try again with more detail.
                    </p>
                  </div>
                )}

                {response.status === "declined" && response.decline_reason && (
                  <div className="rounded-xl border border-rose-100 bg-rose-50/60 p-4">
                    <p className="text-sm leading-relaxed text-rose-950">
                      {response.decline_reason}
                    </p>
                    <p className="mt-3 text-xs text-rose-800">
                      Try one of the suggested questions, or contact your data team for help.
                    </p>
                  </div>
                )}

                {response.status === "error" && response.error && (
                  <p className="text-sm leading-relaxed text-slate-700">{response.error}</p>
                )}
              </div>
            </div>
          </article>
        )}
      </div>

      <section className="mt-10 border-t border-slate-200 pt-8">
        <button
          type="button"
          onClick={() => setShowAdvanced((open) => !open)}
          aria-expanded={showAdvanced}
          className="flex w-full items-center justify-between rounded-xl px-1 py-2 text-left text-sm font-medium text-slate-600 transition hover:text-slate-900"
        >
          <span>Test scenarios &amp; settings</span>
          <span className="text-slate-400" aria-hidden="true">
            {showAdvanced ? "−" : "+"}
          </span>
        </button>

        {showAdvanced && (
          <div className="animate-fade-in-up mt-4 space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900">Example scenarios</h3>
              <p className="mt-1 text-xs text-slate-500">
                Load a preset to test different response types.
              </p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {EXAMPLE_SCENARIOS.map((example) => (
                  <button
                    key={example.label}
                    type="button"
                    onClick={() => applyExample(example)}
                    className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-left transition hover:border-indigo-200 hover:bg-indigo-50/50"
                  >
                    <p className="text-sm font-medium text-slate-900">{example.label}</p>
                    <p className="mt-1 text-xs text-slate-500">{example.description}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900">User identity (for testing)</h3>
              <p className="mt-1 text-xs text-slate-500">
                Simulates who is asking and which regions they can access.
              </p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="userId" className="mb-1.5 block text-xs font-medium text-slate-600">
                    User ID
                  </label>
                  <input
                    id="userId"
                    value={userId}
                    onChange={(event) => setUserId(event.target.value)}
                    required
                    className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                  />
                </div>
                <div>
                  <label htmlFor="regions" className="mb-1.5 block text-xs font-medium text-slate-600">
                    Allowed regions
                  </label>
                  <input
                    id="regions"
                    value={regions}
                    onChange={(event) => setRegions(event.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                    placeholder="US, EU"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label htmlFor="email" className="mb-1.5 block text-xs font-medium text-slate-600">
                    Email (optional)
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                    placeholder="alice@corp.com"
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      <footer className="mt-8 border-t border-slate-200 pt-6">
        <button
          type="button"
          onClick={() => setShowDevPanel((open) => !open)}
          aria-expanded={showDevPanel}
          className="flex w-full items-center justify-between rounded-xl px-1 py-2 text-left text-xs font-medium text-slate-400 transition hover:text-slate-600"
        >
          <span className="inline-flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${
                health === "ok"
                  ? "bg-emerald-500"
                  : health === "checking"
                    ? "bg-amber-400 animate-pulse"
                    : "bg-rose-500"
              }`}
            />
            Developer info
          </span>
          <span aria-hidden="true">{showDevPanel ? "−" : "+"}</span>
        </button>

        {showDevPanel && (
          <div className="animate-fade-in-up mt-3 space-y-4 rounded-xl border border-slate-200 bg-white p-4 text-xs text-slate-600">
            <p>
              API status:{" "}
              <span className="font-medium text-slate-800">
                {health === "ok" ? "healthy" : health === "checking" ? "checking…" : "unreachable"}
              </span>
            </p>
            <p className="font-mono break-all">{getApiBaseUrl()}</p>
            {response?.request_id && (
              <p className="font-mono">request_id: {response.request_id}</p>
            )}
            {metrics && (
              <dl className="grid gap-2 sm:grid-cols-2">
                <div className="flex justify-between gap-4">
                  <dt>Deflection rate</dt>
                  <dd className="font-medium text-slate-800">
                    {formatPercent(metrics.deflection_rate)}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt>Clarification rate</dt>
                  <dd className="font-medium text-slate-800">
                    {formatPercent(metrics.clarification_rate)}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt>Avg latency</dt>
                  <dd className="font-medium text-slate-800">
                    {metrics.agent_latency_ms_avg != null
                      ? `${metrics.agent_latency_ms_avg} ms`
                      : "—"}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt>Avg bytes scanned</dt>
                  <dd className="font-medium text-slate-800">
                    {metrics.agent_bytes_scanned_avg != null
                      ? Math.round(metrics.agent_bytes_scanned_avg).toLocaleString()
                      : "—"}
                  </dd>
                </div>
              </dl>
            )}
            <button
              type="button"
              onClick={() => void refreshStatus()}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
            >
              Refresh status
            </button>
          </div>
        )}
      </footer>
    </div>
  );
}
