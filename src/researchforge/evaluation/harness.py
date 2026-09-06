"""V1.8 product Agent Eval Harness: final answer, trajectory and failure semantics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from researchforge.application.general_research import QuestionRouter
from researchforge.evaluation.failures import failure_record
from researchforge.evaluation.retrieval import JsonObject, RetrievalBenchmark


class AgentEvalHarness:
    """Evaluate persisted product runs and frozen offline retrieval/router cases."""

    def evaluate_bundle(
        self,
        *,
        manifest: JsonObject,
        result: JsonObject | None,
        trace: JsonObject | None,
        facts: list[JsonObject],
        evidence: list[JsonObject],
        calculations: list[JsonObject],
    ) -> JsonObject:
        lifecycle = str(manifest.get("lifecycle_state", "unknown"))
        if lifecycle != "succeeded" or result is None:
            return {
                "schema_version": "1.8.0",
                "run_id": manifest.get("run_id"),
                "task_success": False,
                "terminal_state": lifecycle,
                "failure": failure_record(manifest),
                "metrics": {},
            }

        fact_ids = {str(item.get("fact_id")) for item in facts}
        evidence_ids = {str(item.get("chunk_id")) for item in evidence}
        raw_claims = result.get("claims")
        raw_sections = result.get("analysis_sections")
        claims: list[Any] = raw_claims if isinstance(raw_claims, list) else []
        sections: list[Any] = raw_sections if isinstance(raw_sections, list) else []
        material_claims: list[dict[str, Any]] = [item for item in claims if isinstance(item, dict)]
        grounded = 0
        citation_valid = True
        for claim in material_claims:
            cited_facts = {str(item) for item in claim.get("fact_ids", [])}
            cited_evidence = {str(item) for item in claim.get("support_evidence_ids", [])}
            if cited_facts or cited_evidence:
                grounded += 1
            citation_valid = (
                citation_valid and cited_facts <= fact_ids and cited_evidence <= evidence_ids
            )
        for section in sections:
            if not isinstance(section, dict):
                continue
            citation_valid = (
                citation_valid
                and {str(item) for item in section.get("evidence_ids", [])} <= evidence_ids
            )
        trace_stages = trace.get("stages", []) if isinstance(trace, dict) else []
        completed_stages = [
            stage
            for stage in trace_stages
            if isinstance(stage, dict) and stage.get("status") == "succeeded"
        ]
        grounding_rate = grounded / len(material_claims) if material_claims else 0.0
        research_question = str(manifest.get("input", {}).get("research_question", ""))
        expected_skill = (
            QuestionRouter().route(research_question).skill if research_question else None
        )
        observed_intent = result.get("research_intent")
        observed_skill = (
            str(observed_intent.get("skill")) if isinstance(observed_intent, dict) else None
        )
        intent_routing_valid = expected_skill is None or expected_skill == observed_skill
        raw_plan = result.get("research_plan")
        plan = raw_plan if isinstance(raw_plan, list) else []
        plan_completion = (
            sum(1 for step in plan if isinstance(step, dict) and step.get("status") == "completed")
            / len(plan)
            if plan
            else 0.0
        )
        synthesis_mode = result.get("synthesis_mode")
        structured_output_valid = bool(
            result.get("run_id") == manifest.get("run_id")
            and synthesis_mode in {"model", "evidence_summary_fallback"}
            and isinstance(result.get("executive_summary"), str)
        )
        task_success = bool(
            citation_valid
            and structured_output_valid
            and grounding_rate == 1.0
            and intent_routing_valid
            and trace is not None
            and str(trace.get("terminal_state")) == "succeeded"
            and bool(trace_stages)
            and len(completed_stages) == len(trace_stages)
        )
        return {
            "schema_version": "1.8.0",
            "run_id": manifest.get("run_id"),
            "task_success": task_success,
            "terminal_state": lifecycle,
            "synthesis_mode": synthesis_mode,
            "context": {
                "company_ids": [
                    str(item) for item in manifest.get("input", {}).get("company_ids", [])
                ],
                "research_question": research_question,
            },
            "metrics": {
                "grounded_claim_rate": round(grounding_rate, 4),
                "citation_validity": 1.0 if citation_valid else 0.0,
                "structured_output_validity": 1.0 if structured_output_valid else 0.0,
                "intent_routing_accuracy": 1.0 if intent_routing_valid else 0.0,
                "plan_completion": round(plan_completion, 4),
                "trajectory_completion": round(len(completed_stages) / len(trace_stages), 4)
                if trace_stages
                else 0.0,
                "tool_call_count": sum(
                    len(stage.get("tool_record_ids", []))
                    for stage in trace_stages
                    if isinstance(stage, dict)
                ),
                "fact_count": len(facts),
                "evidence_count": len(evidence),
                "calculation_count": len(calculations),
            },
            "failure": None,
        }

    def evaluate_thread(self, run_evaluations: list[JsonObject]) -> JsonObject:
        """Evaluate a sequence of persisted turns without pretending to judge prose semantics."""
        run_ids = [str(item.get("run_id")) for item in run_evaluations]
        contexts = {
            tuple(str(company_id) for company_id in item.get("context", {}).get("company_ids", []))
            for item in run_evaluations
        }
        same_company_context = len(contexts) == 1 and bool(next(iter(contexts), ()))
        all_successful = bool(run_evaluations) and all(
            bool(item.get("task_success")) for item in run_evaluations
        )
        return {
            "schema_version": "1.8.0",
            "turn_count": len(run_evaluations),
            "run_ids": run_ids,
            "eligible_thread": same_company_context,
            "same_company_context": same_company_context,
            "all_turns_successful": same_company_context and all_successful,
            "no_duplicate_run_ids": len(run_ids) == len(set(run_ids)),
            "grounding_preserved": same_company_context
            and all(
                float(item.get("metrics", {}).get("grounded_claim_rate", 0.0)) == 1.0
                for item in run_evaluations
            ),
            "semantic_consistency_scored": False,
            "semantic_consistency_note": (
                "V1.8.5 does not use a model judge for contradiction scoring; it verifies "
                "context identity, run success and grounding only."
            ),
        }

    def evaluate_offline_suite(self, project_root: Path, suite: JsonObject) -> JsonObject:
        cases = suite.get("retrieval_cases", [])
        if not isinstance(cases, list):
            raise ValueError("retrieval_cases must be a list")
        benchmark = RetrievalBenchmark(project_root).run(cases)
        return {
            "schema_version": "1.8.0",
            "suite_id": suite.get("suite_id"),
            "component_eval": {
                "router_accuracy": benchmark["router_accuracy"],
                "retrieval": benchmark["strategies"],
            },
            "retrieval_benchmark": benchmark,
            "passed": bool(
                float(benchmark["router_accuracy"]) == 1.0
                and float(benchmark["strategies"]["lexical"]["recall_at_10"]) >= 0.8
            ),
        }
