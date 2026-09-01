import type {
  Catalog,
  EvolutionExperiment,
  FinancialFact,
  ResearchResult,
  RunManifest,
  TaskType,
  Trace,
} from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as Record<string, unknown>
    throw new Error(String(body.detail ?? body.code ?? `HTTP ${response.status}`))
  }
  return (await response.json()) as T
}

export const api = {
  catalog: () => request<Catalog>('/v1/catalog'),
  createRun: (payload: {
    task_type: TaskType
    research_question: string
    company_ids: string[]
    requested_period_labels: string[]
    research_time: string
    idempotency_key: string
  }) =>
    request<{ run_id: string }>('/v1/research-runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  manifest: (runId: string) => request<RunManifest>(`/v1/research-runs/${runId}`),
  result: (runId: string) => request<ResearchResult>(`/v1/research-runs/${runId}/result`),
  trace: (runId: string) => request<Trace>(`/v1/research-runs/${runId}/trace`),
  facts: (runId: string) => request<FinancialFact[]>(`/v1/research-runs/${runId}/facts`),
  cancel: (runId: string) =>
    request<RunManifest>(`/v1/research-runs/${runId}/cancel`, { method: 'POST' }),
  experiment: (experimentId: string) =>
    request<EvolutionExperiment>(
      `/v1/evolution-experiments/${encodeURIComponent(experimentId)}`,
    ),
  experimentArtifact: <T>(experimentId: string, kind: string) =>
    request<T>(
      `/v1/evolution-experiments/${encodeURIComponent(experimentId)}/artifacts/${encodeURIComponent(kind)}`,
    ),
}
