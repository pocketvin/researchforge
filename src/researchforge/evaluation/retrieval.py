"""Offline retrieval evaluation for V1.8 without provider calls."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from researchforge.application.general_research import EvidenceRetriever, QuestionRouter

JsonObject = dict[str, Any]
_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]", re.IGNORECASE)


def _tokens(text: str) -> list[str]:
    raw = [token.casefold() for token in _TOKEN_RE.findall(text)]
    chinese = [token for token in raw if len(token) == 1 and "\u4e00" <= token <= "\u9fff"]
    bigrams = [chinese[index] + chinese[index + 1] for index in range(len(chinese) - 1)]
    return raw + bigrams


def _cosine(query: Counter[str], document: Counter[str], idf: dict[str, float]) -> float:
    query_values = {term: count * idf.get(term, 0.0) for term, count in query.items()}
    document_values = {term: count * idf.get(term, 0.0) for term, count in document.items()}
    dot = sum(value * document_values.get(term, 0.0) for term, value in query_values.items())
    qnorm = math.sqrt(sum(value * value for value in query_values.values()))
    dnorm = math.sqrt(sum(value * value for value in document_values.values()))
    return dot / (qnorm * dnorm) if qnorm and dnorm else 0.0


def _tfidf_rank(chunks: tuple[JsonObject, ...], question: str) -> list[str]:
    documents = [
        Counter(_tokens(f"{item.get('section', '')} {item.get('text', '')}")) for item in chunks
    ]
    document_frequency: Counter[str] = Counter()
    for document in documents:
        document_frequency.update(document.keys())
    total = max(len(documents), 1)
    idf = {
        term: math.log((1 + total) / (1 + freq)) + 1.0 for term, freq in document_frequency.items()
    }
    query = Counter(_tokens(question))
    scored = [
        (_cosine(query, document, idf), str(chunk["chunk_id"]))
        for document, chunk in zip(documents, chunks, strict=True)
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [chunk_id for score, chunk_id in scored if score > 0]


def _rrf(*rankings: list[str], k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return [item for item, _ in sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))]


def _metrics(ranking: list[str], relevant: set[str]) -> dict[str, float]:
    def recall(k: int) -> float:
        return len(set(ranking[:k]) & relevant) / len(relevant) if relevant else 1.0

    def precision(k: int) -> float:
        return len(set(ranking[:k]) & relevant) / max(min(k, len(ranking)), 1)

    reciprocal_rank = 0.0
    for rank, item in enumerate(ranking, start=1):
        if item in relevant:
            reciprocal_rank = 1.0 / rank
            break
    return {
        "recall_at_5": recall(5),
        "recall_at_10": recall(10),
        "precision_at_5": precision(5),
        "mrr": reciprocal_rank,
    }


def _load_chunks(package_root: Path) -> tuple[JsonObject, ...]:
    chunks = []
    for path in sorted((package_root / "evidence-chunks").glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict):
            chunks.append(value)
    return tuple(chunks)


class RetrievalBenchmark:
    """Compare production lexical retrieval, TF-IDF vector ranking and RRF hybrid."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.router = QuestionRouter()
        self.lexical = EvidenceRetriever()

    def run(self, cases: list[JsonObject]) -> JsonObject:
        results: list[JsonObject] = []
        totals: dict[str, dict[str, float]] = {
            name: {
                metric: 0.0 for metric in ("recall_at_5", "recall_at_10", "precision_at_5", "mrr")
            }
            for name in ("lexical", "tfidf_vector", "hybrid_rrf")
        }
        for case in cases:
            package_root = self.project_root / str(case["package"])
            chunks = _load_chunks(package_root)
            question = str(case["question"])
            intent = self.router.route(question)
            lexical_chunks = self.lexical.retrieve(
                chunks, question=question, intent=intent, limit=10
            )
            lexical_rank = [str(item["chunk_id"]) for item in lexical_chunks]
            vector_rank = _tfidf_rank(chunks, question)
            hybrid_rank = _rrf(lexical_rank, vector_rank)
            relevant = {str(item) for item in case["relevant_evidence_ids"]}
            strategy_metrics = {
                "lexical": _metrics(lexical_rank, relevant),
                "tfidf_vector": _metrics(vector_rank, relevant),
                "hybrid_rrf": _metrics(hybrid_rank, relevant),
            }
            for strategy, metrics in strategy_metrics.items():
                for metric, value in metrics.items():
                    totals[strategy][metric] += value
            results.append(
                {
                    "case_id": case["case_id"],
                    "question": question,
                    "expected_skill": case["expected_skill"],
                    "observed_skill": intent.skill,
                    "router_pass": intent.skill == case["expected_skill"],
                    "relevant_evidence_ids": sorted(relevant),
                    "rankings": {
                        "lexical": lexical_rank[:10],
                        "tfidf_vector": vector_rank[:10],
                        "hybrid_rrf": hybrid_rank[:10],
                    },
                    "metrics": strategy_metrics,
                }
            )
        denominator = max(len(cases), 1)
        aggregate = {
            strategy: {metric: round(value / denominator, 4) for metric, value in metrics.items()}
            for strategy, metrics in totals.items()
        }
        return {
            "schema_version": "1.8.0",
            "case_count": len(cases),
            "router_accuracy": round(
                sum(bool(item["router_pass"]) for item in results) / denominator, 4
            ),
            "strategies": aggregate,
            "cases": results,
            "decision_rule": (
                "Adopt a more complex retrieval strategy only if Recall@10 improves materially "
                "without reducing evidence precision or violating deterministic/offline "
                "constraints."
            ),
        }
