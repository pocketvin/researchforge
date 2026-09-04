import type {
  Catalog,
  CalculationRecord,
  EvidenceChunk,
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
    const detail = body.detail
    if (detail && typeof detail === 'object') {
      const item = detail as Record<string, unknown>
      const parts = [item.code, item.stage, item.message].filter(Boolean).map(String)
      throw new Error(parts.join(' · ') || `HTTP ${response.status}`)
    }
    throw new Error(String(detail ?? body.code ?? `HTTP ${response.status}`))
  }
  return (await response.json()) as T
}

export const api = {
  catalog: () => request<Catalog>('/v1/catalog'),
  createAutonomousRun: (payload: {
    company_query: string
    market_hint: 'CN' | 'US' | 'HK' | null
    requested_period_label: string | null
    research_mode?: 'general' | 'financial_snapshot'
    research_question: string
    research_time: string
    idempotency_key: string
  }) =>
    request<{ run_id: string }>('/v1/autonomous-research-runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
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
  evidence: (runId: string) =>
    request<EvidenceChunk[]>(`/v1/research-runs/${runId}/evidence`),
  calculations: (runId: string) =>
    request<CalculationRecord[]>(`/v1/research-runs/${runId}/calculations`),
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
