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
  data_namespace: 'product' | 'fixture' | 'benchmark'
  companies: Company[]
  supported_task_types: TaskType[]
  implementation_level: string
  limitations: string[]
}

export interface RunHistoryItem {
  run_id: string
  lifecycle_state: string
  created_at: string
  finished_at: string | null
  company_id: string
  company_name: string
  ticker: string | null
  market: string
  period_label: string | null
  research_question: string
  research_intent_label: string | null
  synthesis_mode: 'model' | 'evidence_summary_fallback' | null
  failure: { code: string; message: string } | null
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
  support_evidence_ids: string[]
  counter_evidence_search: {
    performed: boolean
    queries: string[]
    result: string
    evidence_ids: string[]
    summary: string
  }
  alternative_explanations: string[]
  confidence: { level: string; basis: string }
}

export interface ResearchResult {
  schema_version?: string
  result_id: string
  task_type: TaskType
  executive_summary: string
  synthesis_mode: 'model' | 'evidence_summary_fallback'
  research_intent?: {
    skill: string
    label: string
    search_terms: string[]
    preferred_sections: string[]
  }
  analysis_sections?: Array<{ title: string; text: string; evidence_ids: string[] }>
  overall_judgment?: { label: string; rationale: string }
  suggested_follow_ups?: string[]
  evidence_coverage?: {
    available_chunk_count: number
    selected_chunk_count: number
    selected_evidence_ids: string[]
    cited_evidence_ids: string[]
    sections: string[]
  }
  claims: Claim[]
  mandatory_checks: Array<{
    check_code: string
    status: string
    finding: string
    fact_ids: string[]
    evidence_ids: string[]
  }>
  monitoring_items: Array<{
    monitor_code: string
    title: string
    rationale: string
    trigger: string
    next_review: string
    fact_ids: string[]
    evidence_ids: string[]
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

export interface EvidenceChunk {
  chunk_id: string
  document_id: string
  section: string
  text: string
  text_hash: string
  source_uri: string
  locator: { page_start: number; page_end: number }
}

export interface CalculationRecord {
  calculation_id: string
  formula_code: string
  formula_version: string
  input_fact_ids: string[]
  status: string
  value: string | null
  measurement_unit: string | null
  explanation: string
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

export interface TechnicalRetries {
  policy: string
  records: Array<{
    retry_key: string
    failed_run_id: string
    retry_run_id: string
    retry_state: string
    provider_tokens_before_failure: number
    excluded_failed_run_from_formal_denominator: boolean
  }>
}

export interface ContingencyActivation {
  status: string
  authorization_basis: string
  primary_outcome: string
  activation_count: number
  protocol_deviation: {
    code: string
    data_or_threshold_changed: boolean
    explanation: string
  }
}

export interface ProjectResearchOutcome {
  status: string
  formal_experiment_count: number
  research_hypothesis_supported: boolean
  primary: { experiment_id: string; outcome: string; result_hash: string }
  contingency: { experiment_id: string; outcome: string; result_hash: string }
  final_test_consumed: boolean
  stopping_rule_applied: boolean
  claim_boundary: string
}

export interface ValidationDecision {
  status: string
  decision: SkillPatch['decision']
  seed_evaluation_ids: string[]
  candidate_evaluation_ids: string[]
}

export interface EvolutionArtifacts {
  baseEvolution: EvaluationBatch | null
  seedEvolution: EvaluationBatch | null
  failureCluster: FailureCluster | null
  experience: Experience | null
  patch: SkillPatch | null
  validationDecision: ValidationDecision | null
  seedValidation: EvaluationBatch | null
  candidateValidation: EvaluationBatch | null
  seedFinal: EvaluationBatch | null
  candidateFinal: EvaluationBatch | null
  technicalRetries: TechnicalRetries | null
  activation: ContingencyActivation | null
  projectResearchOutcome: ProjectResearchOutcome | null
}
