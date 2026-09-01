export type TaskType =
  | 'company_research'
  | 'filing_analysis'
  | 'peer_comparison'
  | 'thesis_investigation'
  | 'risk_detection'

export interface Company {
  company_id: string
  legal_name: string
  ticker: string
  exchange: string
  country_code: string
  period_labels: string[]
}

export interface Catalog {
  schema_version: string
  companies: Company[]
  supported_task_types: TaskType[]
  implementation_level: string
  limitations: string[]
}

export interface RunManifest {
  run_id: string
  lifecycle_state: string
  input: {
    task_type: TaskType
    research_question: string
    company_ids: string[]
    requested_period_labels: string[]
    research_time: string
  }
  artifacts: {
    result_id: string | null
    workflow_trace_id: string | null
    evaluation_id: string | null
  }
  failure: { code: string; message: string } | null
}

export interface Claim {
  claim_id: string
  claim_type: string
  epistemic_status: string
  materiality: string
  direction: string
  text: string
  fact_ids: string[]
  counter_evidence_search: {
    performed: boolean
    result: string
    summary: string
  }
  alternative_explanations: string[]
  confidence: { level: string; basis: string }
}

export interface ResearchResult {
  result_id: string
  task_type: TaskType
  executive_summary: string
  claims: Claim[]
  mandatory_checks: Array<{
    check_code: string
    status: string
    finding: string
    fact_ids: string[]
  }>
  limitations: string[]
  source_document_ids: string[]
}

export interface FinancialFact {
  fact_id: string
  metric_code: string
  value: string | null
  currency: string | null
  measurement_unit: string
  company: Company
  period: { fiscal_year: number; fiscal_period: string }
  source: { document_id: string; published_at: string; uri: string }
  source_locator: { page: number | null; section: string | null; table: string | null }
}

export interface Trace {
  run_id: string
  terminal_state: string
  stages: Array<{
    sequence: number
    stage: string
    status: string
    sanitized_summary: string
  }>
}

export interface EvolutionExperiment {
  schema_version: string
  experiment_id: string
  scope_version: string
  suite_id: string
  suite_hash: string
  status: string
  outcome: string
  seed_skill_version_id: string
  candidate_skill_version_id: string | null
  split_case_ids: {
    evolution: string[]
    validation: string[]
    final_test: string[]
  }
  budget: { currency: string; cap: number; spent: number }
  final_test_consumed: boolean
  preregistered_at: string
  finished_at: string | null
}

export interface FailureCluster {
  cluster_id: string
  failure_label: string
  signature: string
  eligible_run_count: number
  support_count: number
  distinct_case_ids: string[]
}

export interface Experience {
  experience_id: string
  failure_label: string
  observed_behavior: string
  applicable_condition: string
  required_procedure: string
  exceptions: string[]
}

export interface SkillPatch {
  patch_id: string
  candidate_version: string
  status: string
  operations: Array<{
    operation: string
    target_section: string
    new_rule: string
    reason: string
  }>
  decision: null | {
    target_failure_reduced: boolean
    deterministic_quality_preserved: boolean
    overall_non_inferior: boolean
    regression_within_threshold: boolean
    decision_reason: string
  }
}

export interface EvaluationBatch {
  condition: string
  split: string
  repeat_count: number
  evaluations: Array<{
    evaluation_id: string
    case_id: string
    metrics: { task_score: number }
    failure_events: Array<{ failure_label: string; signature: string }>
  }>
}

export interface ValidationDecision {
  status: string
  decision: SkillPatch['decision']
  seed_evaluation_ids: string[]
  candidate_evaluation_ids: string[]
}

export interface EvolutionArtifacts {
  failureCluster: FailureCluster | null
  experience: Experience | null
  patch: SkillPatch | null
  validationDecision: ValidationDecision | null
  seedValidation: EvaluationBatch | null
  candidateValidation: EvaluationBatch | null
  seedFinal: EvaluationBatch | null
  candidateFinal: EvaluationBatch | null
}
