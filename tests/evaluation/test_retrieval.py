import json
from pathlib import Path

from researchforge.evaluation.retrieval import RetrievalBenchmark

ROOT = Path(__file__).resolve().parents[2]


def test_frozen_retrieval_benchmark_is_repeatable_and_router_is_exact() -> None:
    suite = json.loads((ROOT / "data/evaluation/v1.8/eval-suite.json").read_text())
    result = RetrievalBenchmark(ROOT).run(suite["retrieval_cases"])

    assert result["case_count"] == 8
    assert result["router_accuracy"] == 1.0
    assert result["strategies"]["lexical"]["recall_at_10"] == 0.8125
    assert result["strategies"]["tfidf_vector"]["recall_at_10"] == 0.8542
    assert result["strategies"]["tfidf_vector"]["precision_at_5"] == 0.5417
    assert result["strategies"]["hybrid_rrf"]["precision_at_5"] == 0.375
