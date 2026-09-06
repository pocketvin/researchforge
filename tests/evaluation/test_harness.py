from researchforge.evaluation.harness import AgentEvalHarness


def _bundle() -> dict[str, object]:
    return {
        "manifest": {
            "run_id": "run_1",
            "lifecycle_state": "succeeded",
            "failure": None,
            "input": {"research_question": "请做完整分析"},
        },
        "result": {
            "run_id": "run_1",
            "synthesis_mode": "model",
            "executive_summary": "Supported conclusion.",
            "research_intent": {"skill": "company_overview"},
            "research_plan": [{"status": "completed"}],
            "claims": [
                {
                    "fact_ids": ["fact_1"],
                    "support_evidence_ids": ["chunk_1"],
                }
            ],
            "analysis_sections": [{"evidence_ids": ["chunk_1"]}],
        },
        "trace": {
            "terminal_state": "succeeded",
            "stages": [
                {"status": "succeeded", "tool_record_ids": ["tool_1"]},
                {"status": "succeeded", "tool_record_ids": []},
            ],
        },
        "facts": [{"fact_id": "fact_1"}],
        "evidence": [{"chunk_id": "chunk_1"}],
        "calculations": [{"calculation_id": "calc_1"}],
    }


def test_agent_eval_scores_grounding_citations_and_trajectory() -> None:
    bundle = _bundle()
    evaluation = AgentEvalHarness().evaluate_bundle(**bundle)  # type: ignore[arg-type]
    assert evaluation["task_success"] is True
    assert evaluation["metrics"]["grounded_claim_rate"] == 1.0
    assert evaluation["metrics"]["citation_validity"] == 1.0
    assert evaluation["metrics"]["intent_routing_accuracy"] == 1.0
    assert evaluation["metrics"]["plan_completion"] == 1.0
    assert evaluation["metrics"]["trajectory_completion"] == 1.0
    assert evaluation["metrics"]["tool_call_count"] == 1


def test_agent_eval_rejects_out_of_run_citation() -> None:
    bundle = _bundle()
    result = bundle["result"]
    assert isinstance(result, dict)
    claims = result["claims"]
    assert isinstance(claims, list)
    assert isinstance(claims[0], dict)
    claims[0]["support_evidence_ids"] = ["missing"]
    evaluation = AgentEvalHarness().evaluate_bundle(**bundle)  # type: ignore[arg-type]
    assert evaluation["task_success"] is False
    assert evaluation["metrics"]["citation_validity"] == 0.0


def test_thread_eval_keeps_grounding_and_unique_run_identity() -> None:
    harness = AgentEvalHarness()
    result = harness.evaluate_thread(
        [
            {
                "run_id": "run_1",
                "task_success": True,
                "context": {"company_ids": ["cn_1"]},
                "metrics": {"grounded_claim_rate": 1.0},
            },
            {
                "run_id": "run_2",
                "task_success": True,
                "context": {"company_ids": ["cn_1"]},
                "metrics": {"grounded_claim_rate": 1.0},
            },
        ]
    )
    assert result["eligible_thread"] is True
    assert result["same_company_context"] is True
    assert result["all_turns_successful"] is True
    assert result["semantic_consistency_scored"] is False
    assert result["no_duplicate_run_ids"] is True
    assert result["grounding_preserved"] is True
