#!/usr/bin/env python3
"""Validate the ResearchForge contract package without third-party dependencies."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CURRENT_SCHEMA_VERSION = "v1.4"
CURRENT_ARTIFACT_VERSION = "1.4.0"
ACTIVE_PRODUCT_SCHEMA_VERSION = "v1.5"
ACTIVE_PRODUCT_ARTIFACT_VERSION = "1.5.0"
V17_SCHEMA_VERSION = "v1.7"
V17_ARTIFACT_VERSION = "1.7.0"
HISTORICAL_SCHEMA_VERSIONS = ("v1.3", "v1.2")
SCHEMA_DIR = ROOT / "schemas" / CURRENT_SCHEMA_VERSION
ACTIVE_PRODUCT_SCHEMA_DIR = ROOT / "schemas" / ACTIVE_PRODUCT_SCHEMA_VERSION
V17_SCHEMA_DIR = ROOT / "schemas" / V17_SCHEMA_VERSION
HISTORICAL_SCHEMA_DIRS = {
    version: ROOT / "schemas" / version for version in HISTORICAL_SCHEMA_VERSIONS
}
EXAMPLE_DIR = ROOT / "examples" / "contracts" / CURRENT_SCHEMA_VERSION
ACTIVE_PRODUCT_EXAMPLE_DIR = ROOT / "examples" / "contracts" / ACTIVE_PRODUCT_SCHEMA_VERSION
G0_FIXTURE_DIR = ROOT / "data" / "fixtures" / "g0"
G0_SOURCE_DIR = G0_FIXTURE_DIR / "source-documents"
G0_FACT_DIR = G0_FIXTURE_DIR / "financial-facts"
G0_GOLDEN_CASES_PATH = G0_FIXTURE_DIR / "golden-cases.json"
G0_MANIFEST_PATH = G0_FIXTURE_DIR / "manifest.json"
PRIMARY_FIXTURE_DIR = ROOT / "data" / "fixtures" / "v1.4-primary"
PRIMARY_SOURCE_DIR = PRIMARY_FIXTURE_DIR / "source-documents"
PRIMARY_FACT_DIR = PRIMARY_FIXTURE_DIR / "financial-facts"
PRIMARY_CHUNK_DIR = PRIMARY_FIXTURE_DIR / "evidence-chunks"
PRIMARY_CASE_DIR = PRIMARY_FIXTURE_DIR / "cases"
PRIMARY_MANIFEST_PATH = PRIMARY_FIXTURE_DIR / "manifest.json"
PRIMARY_SUITE_PATH = ROOT / "benchmark" / "suites" / "v1.4-primary-preregistered.json"
CONTINGENCY_FIXTURE_DIR = ROOT / "data" / "fixtures" / "v1.5-contingency"
CONTINGENCY_SOURCE_DIR = CONTINGENCY_FIXTURE_DIR / "source-documents"
CONTINGENCY_FACT_DIR = CONTINGENCY_FIXTURE_DIR / "financial-facts"
CONTINGENCY_CHUNK_DIR = CONTINGENCY_FIXTURE_DIR / "evidence-chunks"
CONTINGENCY_CASE_DIR = CONTINGENCY_FIXTURE_DIR / "cases"
CONTINGENCY_MANIFEST_PATH = CONTINGENCY_FIXTURE_DIR / "manifest.json"
CONTINGENCY_SUITE_PATH = ROOT / "benchmark" / "suites" / "v1.5-contingency-preregistered.json"
PRODUCT_REGISTRY_PATH = ROOT / "data" / "product" / "filing-catalog.json"
PRODUCT_PACKAGE_DIR = ROOT / "data" / "product" / "packages" / "catl-2024h1"
PRODUCT_PACKAGE_MANIFEST_PATH = PRODUCT_PACKAGE_DIR / "manifest.json"
PRODUCT_INGESTION_MANIFEST_PATH = PRODUCT_PACKAGE_DIR / "ingestion-manifest.json"
PRODUCT_INDEX_PATH = PRODUCT_PACKAGE_DIR.parent / "manifest.json"
HISTORICAL_EXAMPLE_DIRS = {
    "v1.3": ROOT / "examples" / "contracts" / "v1.3",
    "v1.2": ROOT / "examples" / "contracts",
}
CONTRACT_PACKAGE_VERSION = "1.5.0"
G0_REQUIRED_METRICS = {
    "accounts_receivable",
    "inventory",
    "revenue",
    "operating_cost",
    "net_income",
    "operating_cash_flow",
}
HISTORICAL_SCOPE_SHA256 = {
    "v1.3": "b7c1a17e705550122a97296ef255660879f060911a2c01d27d1793bb9ece68a7",
    "v1.2": "513f4a9ae8eabab7a77cb34dedabf6b064a0f9a5710386856f93a7219250816e",
}

REQUIRED_SCHEMAS = {
    "common.schema.json",
    "financial-fact.schema.json",
    "evidence-chunk.schema.json",
    "claim.schema.json",
    "research-result.schema.json",
    "run-manifest.schema.json",
    "skill-patch.schema.json",
    "benchmark-case.schema.json",
    "evaluation-result.schema.json",
    "project-checkpoint.schema.json",
    "workflow-trace.schema.json",
    "source-document.schema.json",
    "calculation-record.schema.json",
    "tool-record.schema.json",
    "skill-version.schema.json",
    "experience.schema.json",
    "evolution-experiment.schema.json",
    "retrieval-evaluation.schema.json",
    "simulated-usability-evaluation.schema.json",
}

V17_REQUIRED_SCHEMAS = {"research-result.schema.json", "n8n-research-output.schema.json"}

ACTIVE_PRODUCT_REQUIRED_SCHEMAS = {
    "common.schema.json",
    "final-human-evaluation-session.schema.json",
    "financial-fact-extraction.schema.json",
    "human-usability-session.schema.json",
    "ingestion-manifest.schema.json",
    "product-research-request.schema.json",
    "project-checkpoint.schema.json",
    "product-package-index.schema.json",
    "n8n-research-output.schema.json",
}

HISTORICAL_REQUIRED_SCHEMAS = {
    "v1.3": REQUIRED_SCHEMAS
    - {
        "source-document.schema.json",
        "calculation-record.schema.json",
        "tool-record.schema.json",
        "skill-version.schema.json",
        "experience.schema.json",
        "evolution-experiment.schema.json",
        "retrieval-evaluation.schema.json",
        "simulated-usability-evaluation.schema.json",
    },
    "v1.2": {
        "common.schema.json",
        "financial-fact.schema.json",
        "evidence-chunk.schema.json",
        "claim.schema.json",
        "research-result.schema.json",
        "run-manifest.schema.json",
        "skill-patch.schema.json",
        "benchmark-case.schema.json",
        "evaluation-result.schema.json",
        "project-checkpoint.schema.json",
    },
}

CURRENT_EXAMPLES = {
    "benchmark-case.example.json": "benchmark-case.schema.json",
    "calculation-record.example.json": "calculation-record.schema.json",
    "evolution-experiment.example.json": "evolution-experiment.schema.json",
    "experience.example.json": "experience.schema.json",
    "retrieval-evaluation.example.json": "retrieval-evaluation.schema.json",
    "run-manifest.patch-generation.example.json": "run-manifest.schema.json",
    "run-manifest.research.example.json": "run-manifest.schema.json",
    "simulated-usability-evaluation.example.json": ("simulated-usability-evaluation.schema.json"),
    "skill-version.example.json": "skill-version.schema.json",
    "source-document.example.json": "source-document.schema.json",
    "tool-record.example.json": "tool-record.schema.json",
    "workflow-trace.example.json": "workflow-trace.schema.json",
}

ACTIVE_PRODUCT_EXAMPLES = {
    "final-human-evaluation-session.template.json": ("final-human-evaluation-session.schema.json"),
    "n8n-research-output.error.example.json": "n8n-research-output.schema.json",
    "human-usability-session.example.json": "human-usability-session.schema.json",
    "ingestion-manifest.example.json": "ingestion-manifest.schema.json",
    "product-research-request.example.json": "product-research-request.schema.json",
}

HISTORICAL_EXAMPLES = {
    "v1.3": {
        "benchmark-case.example.json": "benchmark-case.schema.json",
        "run-manifest.patch-generation.example.json": "run-manifest.schema.json",
        "run-manifest.research.example.json": "run-manifest.schema.json",
        "workflow-trace.example.json": "workflow-trace.schema.json",
    },
    "v1.2": {"benchmark-case.example.json": "benchmark-case.schema.json"},
}

REQUIRED_CONTRACTS = {
    ROOT / "README.md",
    ROOT / ".env.example",
    ROOT / ".python-version",
    ROOT / "AGENTS.md",
    ROOT / "CHANGELOG.md",
    ROOT / "DECISIONS.md",
    ROOT / "DATA_NOTICE.md",
    ROOT / "LICENSE",
    ROOT / "PORTFOLIO.md",
    ROOT / "PROJECT_STATUS.md",
    ROOT / "project-status.json",
    ROOT / "pyproject.toml",
    ROOT / "uv.lock",
    ROOT / ".github" / "workflows" / "ci.yml",
    ROOT / "Dockerfile",
    ROOT / "docker-compose.yml",
    ROOT / "scripts" / "start_demo.py",
    ROOT / "scripts" / "summarize_human_evaluation.py",
    ROOT / "frontend" / "scripts" / "capture-demo-screenshots.mjs",
    ROOT / "scripts" / "build_g0_fixtures.py",
    ROOT / "scripts" / "build_primary_benchmark.py",
    ROOT / "scripts" / "build_contingency_benchmark.py",
    ROOT / "scripts" / "build_demo_video.swift",
    ROOT / "scripts" / "docker_smoke.py",
    ROOT / "scripts" / "extract_primary_pdf_text.py",
    ROOT / "scripts" / "inspect_financial_rows.py",
    ROOT / "src" / "researchforge" / "application" / "calibration.py",
    ROOT / "tests" / "application" / "test_calibration.py",
    G0_MANIFEST_PATH,
    G0_GOLDEN_CASES_PATH,
    PRIMARY_MANIFEST_PATH,
    PRIMARY_SUITE_PATH,
    CONTINGENCY_MANIFEST_PATH,
    CONTINGENCY_SUITE_PATH,
    PRODUCT_REGISTRY_PATH,
    PRODUCT_PACKAGE_MANIFEST_PATH,
    PRODUCT_INGESTION_MANIFEST_PATH,
    PRODUCT_INDEX_PATH,
    ROOT / "docs/evidence/v1.5-generalization/README.md",
    ROOT / "integrations/n8n/researchforge.workflow.json",
    ROOT / "integrations/n8n/README.md",
    ROOT / "docs/contracts/v1.5/n8n-integration.md",
    ROOT / "skills" / "fundamental-research" / "README.md",
    ROOT / "skills" / "fundamental-research" / "versions" / "1.0.0" / "SKILL.md",
    ROOT / "skills" / "fundamental-research" / "versions" / "1.0.0" / "skill-version.json",
    ROOT / "docs" / "architecture" / "implementation-blueprint.md",
    ROOT / "docs" / "product" / "researchforge-v1.4-scope.md",
    ROOT / "docs" / "product" / "researchforge-v1.5-product-thesis.md",
    ROOT / "docs" / "product" / "v1.4-to-v1.5-productization-change-note.md",
    ROOT / "docs" / "product" / "v1.3-to-v1.4-change-note.md",
    ROOT / "docs" / "product" / "researchforge-v1.3-scope.md",
    ROOT / "docs" / "product" / "v1.2-to-v1.3-change-note.md",
    ROOT / "docs" / "product" / "researchforge-v1.2-scope-freeze.md",
    ROOT / "docs" / "contracts" / "README.md",
    ROOT / "docs" / "contracts" / "data-source-acceptance.md",
    ROOT / "docs" / "contracts" / "financial-methodology.md",
    ROOT / "docs" / "contracts" / "product-success-metrics.md",
    ROOT / "docs" / "contracts" / "research-workflow.md",
    ROOT / "docs" / "contracts" / "task-capability-matrix.md",
    ROOT / "docs" / "contracts" / "benchmark-protocol.md",
    ROOT / "docs" / "contracts" / "evolution-adoption-policy.md",
    ROOT / "docs" / "contracts" / "run-lifecycle.md",
    ROOT / "docs" / "contracts" / "development-gates.md",
    ROOT / "docs" / "contracts" / "v1.5" / "README.md",
    ROOT / "docs" / "contracts" / "v1.5" / "real-data-ingestion.md",
    ROOT / "docs" / "contracts" / "v1.5" / "product-research-run.md",
    ROOT / "docs" / "contracts" / "v1.5" / "human-usability-pilot.md",
    ROOT / "docs" / "contracts" / "v1.5" / "final-human-evaluation.md",
    ROOT / "docs" / "evidence" / "g0-source-spike.md",
    ROOT / "docs" / "evidence" / "g0-filing-read-plan.md",
    ROOT / "docs" / "evidence" / "g0-reconciliation.md",
    ROOT / "docs" / "evidence" / "g0-golden-cases.md",
    ROOT / "docs" / "evidence" / "g0-owner-signoff.md",
    ROOT / "docs" / "evidence" / "g3-primary-data-signoff.md",
    ROOT / "docs" / "evidence" / "g3-experiment-engine.md",
    ROOT / "docs" / "evidence" / "g3-contingency-freeze.md",
    ROOT / "docs" / "evidence" / "g4-engineering-progress.md",
    ROOT / "docs" / "evidence" / "v1.5-phase2-financial-fact-extraction.md",
    ROOT / "docs" / "demo" / "demo-script.md",
    ROOT / "docs" / "demo" / "walkthrough.md",
    ROOT / "docs" / "demo" / "v1.5-demo-evidence.md",
    ROOT / "docs" / "usability" / "README.md",
    ROOT / "docs" / "usability" / "privacy-notice.md",
    ROOT / "docs" / "usability" / "participant-task-sheet.md",
    ROOT / "docs" / "usability" / "facilitator-guide.md",
    ROOT / "docs" / "usability" / "observation-rubric.md",
    ROOT / "docs" / "usability" / "pilot-status.md",
    ROOT / "docs" / "usability" / "final-dual-surface-protocol.md",
    ROOT / "docs" / "usability" / "final-participant-task-sheet.md",
    ROOT / "docs" / "usability" / "final-facilitator-guide.md",
    ROOT / "docs" / "assets" / "research-page.png",
    ROOT / "docs" / "assets" / "skill-lab-page.png",
    ROOT / "docs" / "assets" / "research-page-v1.5-start.png",
    ROOT / "docs" / "assets" / "research-page-v1.5-result.png",
    ROOT / "docs" / "assets" / "research-page-v1.5-evidence.png",
    ROOT / "docs" / "assets" / "quality-lab-page-v1.5.png",
    ROOT / "docs" / "assets" / "research-page-v1.5-final-start.png",
    ROOT / "docs" / "assets" / "research-page-v1.5-final-result.png",
    ROOT / "docs" / "assets" / "n8n-form-v1.5.png",
    ROOT / "docs" / "assets" / "n8n-result-v1.5.png",
    ROOT / "docs" / "assets" / "n8n-abstention-v1.5.png",
    ROOT / "docs" / "assets" / "researchforge-v1.4-demo.mp4",
    ROOT / "docs" / "operations" / "resume-playbook.md",
    ROOT / "docs" / "strategy" / "project-scorecard.md",
    ROOT / "docs" / "strategy" / "risk-register.md",
    ROOT / "docs" / "strategy" / "solo-success-plan.md",
    *{EXAMPLE_DIR / name for name in CURRENT_EXAMPLES},
    *{ACTIVE_PRODUCT_EXAMPLE_DIR / name for name in ACTIVE_PRODUCT_EXAMPLES},
    *{
        HISTORICAL_EXAMPLE_DIRS[version] / name
        for version, example_map in HISTORICAL_EXAMPLES.items()
        for name in example_map
    },
}

ALLOWED_SCHEMA_KEYWORDS = {
    "$schema",
    "$id",
    "$ref",
    "$defs",
    "title",
    "description",
    "type",
    "const",
    "enum",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minLength",
    "maxLength",
    "pattern",
    "format",
    "minimum",
    "maximum",
    "minProperties",
    "maxProperties",
    "allOf",
    "anyOf",
    "oneOf",
    "not",
    "if",
    "then",
    "else",
    "default",
}


class ContractError(Exception):
    """Raised when a contract artifact is invalid."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"{path.relative_to(ROOT)}: {exc}") from exc


def json_pointer(document: Any, fragment: str, label: str) -> Any:
    if not fragment:
        return document
    if not fragment.startswith("/"):
        raise ContractError(f"{label}: unsupported JSON pointer #{fragment}")
    current = document
    for raw_part in fragment.lstrip("/").split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        try:
            current = current[int(part)] if isinstance(current, list) else current[part]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise ContractError(f"{label}: unresolved JSON pointer #{fragment}") from exc
    return current


def iter_schema_nodes(
    node: dict[str, Any], location: str = "$"
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield schema objects without mistaking property-name maps for schemas."""
    yield location, node

    for map_keyword in ("properties", "$defs"):
        mapping = node.get(map_keyword, {})
        if isinstance(mapping, dict):
            for name, child in mapping.items():
                if isinstance(child, dict):
                    yield from iter_schema_nodes(child, f"{location}/{map_keyword}/{name}")

    for schema_keyword in ("additionalProperties", "items", "not", "if", "then", "else"):
        child = node.get(schema_keyword)
        if isinstance(child, dict):
            yield from iter_schema_nodes(child, f"{location}/{schema_keyword}")

    for array_keyword in ("allOf", "anyOf", "oneOf"):
        children = node.get(array_keyword, [])
        if isinstance(children, list):
            for index, child in enumerate(children):
                if isinstance(child, dict):
                    yield from iter_schema_nodes(child, f"{location}/{array_keyword}/{index}")


def validate_schema_shape(path: Path, schema: dict[str, Any]) -> None:
    relative = path.relative_to(ROOT)
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ContractError(f"{relative}: must use JSON Schema Draft 2020-12")
    version_directory = path.parent.name
    recognized_versions = {
        ACTIVE_PRODUCT_SCHEMA_VERSION,
        V17_SCHEMA_VERSION,
        CURRENT_SCHEMA_VERSION,
        *HISTORICAL_SCHEMA_VERSIONS,
    }
    if version_directory not in recognized_versions:
        raise ContractError(f"{relative}: schema must live in a recognized version directory")
    expected_id = f"https://researchforge.local/schemas/{version_directory}/{path.name}"
    if schema.get("$id") != expected_id:
        raise ContractError(f"{relative}: unexpected $id")
    if not isinstance(schema.get("title"), str) or not schema["title"].strip():
        raise ContractError(f"{relative}: missing title")

    for location, node in iter_schema_nodes(schema):
        unknown = set(node) - ALLOWED_SCHEMA_KEYWORDS
        if unknown:
            raise ContractError(
                f"{relative}:{location}: unsupported schema keywords {sorted(unknown)}"
            )
        if "required" in node and (
            not isinstance(node["required"], list)
            or not all(isinstance(item, str) for item in node["required"])
        ):
            raise ContractError(f"{relative}:{location}: required must be string array")
        if "properties" in node and not isinstance(node["properties"], dict):
            raise ContractError(f"{relative}:{location}: properties must be object")
        for combinator in ("allOf", "anyOf", "oneOf"):
            if combinator in node and (
                not isinstance(node[combinator], list)
                or not all(isinstance(item, dict) for item in node[combinator])
            ):
                raise ContractError(f"{relative}:{location}: {combinator} must be schema array")
        if "$ref" in node and not isinstance(node["$ref"], str):
            raise ContractError(f"{relative}:{location}: $ref must be string")


def resolve_ref(
    ref: str, current_path: Path, schemas: dict[Path, dict[str, Any]]
) -> tuple[Any, Path]:
    file_part, separator, fragment = ref.partition("#")
    if file_part.startswith(("http://", "https://")):
        matching = [path for path, schema in schemas.items() if schema.get("$id") == file_part]
        if len(matching) != 1:
            raise ContractError(f"{current_path.name}: unresolved schema ID {file_part}")
        target_path = matching[0]
    elif file_part:
        target_path = (current_path.parent / file_part).resolve()
    else:
        target_path = current_path.resolve()

    if target_path not in schemas:
        raise ContractError(f"{current_path.name}: unresolved local $ref {ref}")
    target = json_pointer(
        schemas[target_path], fragment if separator else "", f"{current_path.name}:{ref}"
    )
    return target, target_path


def validate_all_refs(schemas: dict[Path, dict[str, Any]]) -> int:
    count = 0
    for path, schema in schemas.items():
        for _, node in iter_schema_nodes(schema):
            if "$ref" in node:
                resolve_ref(node["$ref"], path, schemas)
                count += 1
    return count


def is_type(instance: Any, expected: str) -> bool:
    return {
        "null": instance is None,
        "boolean": isinstance(instance, bool),
        "object": isinstance(instance, dict),
        "array": isinstance(instance, list),
        "string": isinstance(instance, str),
        "integer": isinstance(instance, int) and not isinstance(instance, bool),
        "number": isinstance(instance, (int, float)) and not isinstance(instance, bool),
    }.get(expected, False)


def validate_format(value: str, format_name: str, location: str) -> None:
    try:
        if format_name == "date":
            date.fromisoformat(value)
        elif format_name == "date-time":
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        elif format_name == "uri" and not urlparse(value).scheme:
            raise ValueError("URI has no scheme")
    except ValueError as exc:
        raise ContractError(f"{location}: invalid {format_name}: {value}") from exc


def validate_instance(
    instance: Any,
    schema: dict[str, Any],
    schema_path: Path,
    schemas: dict[Path, dict[str, Any]],
    location: str = "$",
) -> None:
    if "$ref" in schema:
        referenced, referenced_path = resolve_ref(schema["$ref"], schema_path, schemas)
        validate_instance(instance, referenced, referenced_path, schemas, location)

    if "const" in schema and instance != schema["const"]:
        raise ContractError(f"{location}: expected const {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise ContractError(f"{location}: value {instance!r} not in enum")

    if "type" in schema:
        expected_types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(is_type(instance, expected) for expected in expected_types):
            raise ContractError(
                f"{location}: expected type {expected_types}, got {type(instance).__name__}"
            )

    if isinstance(instance, dict):
        required = schema.get("required", [])
        missing = [key for key in required if key not in instance]
        if missing:
            raise ContractError(f"{location}: missing required keys {missing}")
        properties = schema.get("properties", {})
        for key, value in instance.items():
            if key in properties:
                validate_instance(value, properties[key], schema_path, schemas, f"{location}/{key}")
            elif schema.get("additionalProperties") is False:
                raise ContractError(f"{location}: unexpected property {key}")
            elif isinstance(schema.get("additionalProperties"), dict):
                validate_instance(
                    value,
                    schema["additionalProperties"],
                    schema_path,
                    schemas,
                    f"{location}/{key}",
                )
        if len(instance) < schema.get("minProperties", 0):
            raise ContractError(f"{location}: too few properties")
        if "maxProperties" in schema and len(instance) > schema["maxProperties"]:
            raise ContractError(f"{location}: too many properties")

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            raise ContractError(f"{location}: too few items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise ContractError(f"{location}: too many items")
        if schema.get("uniqueItems"):
            serialized = [json.dumps(item, sort_keys=True) for item in instance]
            if len(serialized) != len(set(serialized)):
                raise ContractError(f"{location}: items must be unique")
        if isinstance(schema.get("items"), dict):
            for index, item in enumerate(instance):
                validate_instance(
                    item, schema["items"], schema_path, schemas, f"{location}/{index}"
                )

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            raise ContractError(f"{location}: string is too short")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            raise ContractError(f"{location}: string is too long")
        if "pattern" in schema and re.fullmatch(schema["pattern"], instance) is None:
            raise ContractError(f"{location}: string does not match {schema['pattern']}")
        if "format" in schema:
            validate_format(instance, schema["format"], location)

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise ContractError(f"{location}: value below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            raise ContractError(f"{location}: value above maximum")

    for item in schema.get("allOf", []):
        validate_instance(instance, item, schema_path, schemas, location)

    for keyword, expected_matches in (("anyOf", "at least one"), ("oneOf", "exactly one")):
        if keyword in schema:
            matches = 0
            for option in schema[keyword]:
                try:
                    validate_instance(instance, option, schema_path, schemas, location)
                    matches += 1
                except ContractError:
                    pass
            valid = matches >= 1 if keyword == "anyOf" else matches == 1
            if not valid:
                raise ContractError(
                    f"{location}: {keyword} requires {expected_matches} match, got {matches}"
                )

    if "not" in schema:
        try:
            validate_instance(instance, schema["not"], schema_path, schemas, location)
        except ContractError:
            pass
        else:
            raise ContractError(f"{location}: instance matches forbidden schema")

    if "if" in schema:
        try:
            validate_instance(instance, schema["if"], schema_path, schemas, location)
            branch = schema.get("then")
        except ContractError:
            branch = schema.get("else")
        if branch is not None:
            validate_instance(instance, branch, schema_path, schemas, location)


def validate_markdown_links() -> int:
    count = 0
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in ROOT.rglob("*.md"):
        if any(part in {"node_modules", "dist", "playwright-report"} for part in path.parts):
            continue
        for target in link_pattern.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:")) or target.startswith("#"):
                continue
            clean_target = target.split("#", 1)[0]
            resolved = (path.parent / clean_target).resolve()
            if not resolved.exists():
                raise ContractError(f"{path.relative_to(ROOT)}: broken link {target}")
            count += 1
    return count


def validate_project_checkpoint(checkpoint: dict[str, Any]) -> int:
    """Check repository-level checkpoint semantics not expressible in the JSON Schema."""
    if checkpoint["contract_package_version"] != CONTRACT_PACKAGE_VERSION:
        raise ContractError(
            "project-status.json: contract_package_version must match validator package version"
        )

    current_gate = checkpoint["current_gate"]
    completed_gates = checkpoint["completed_gates"]
    gate_status = checkpoint["gate_status"]
    if gate_status == "completed" and current_gate not in completed_gates:
        raise ContractError(
            "project-status.json: completed current gate missing from completed_gates"
        )
    if gate_status != "completed" and current_gate in completed_gates:
        raise ContractError("project-status.json: active current gate cannot also be completed")
    if checkpoint["current_milestone"]["status"] != gate_status:
        raise ContractError("project-status.json: milestone status must match gate_status")

    path_count = 0
    referenced_paths = (
        checkpoint["resumption"]["read_first"] + checkpoint["last_session"]["files_changed"]
    )
    for relative_path in referenced_paths:
        resolved = (ROOT / relative_path).resolve()
        if ROOT not in resolved.parents and resolved != ROOT:
            raise ContractError(f"project-status.json: path escapes project: {relative_path}")
        if not resolved.exists():
            raise ContractError(f"project-status.json: referenced path missing: {relative_path}")
        path_count += 1

    status_text = (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    required_mirror_text = (
        f"Contract package: {CONTRACT_PACKAGE_VERSION}",
        f"Current gate: {current_gate}",
        "Scope: V1.6 autonomous productization",
    )
    for expected in required_mirror_text:
        if expected not in status_text:
            raise ContractError(f"PROJECT_STATUS.md: missing checkpoint mirror text {expected!r}")

    return path_count


def validate_workflow_trace(trace: dict[str, Any]) -> None:
    stages = trace["stages"]
    sequences = [stage["sequence"] for stage in stages]
    if sequences != list(range(1, len(stages) + 1)):
        raise ContractError("workflow-trace example: stage sequences must be contiguous from 1")
    if stages[0]["stage"] != "understanding_question":
        raise ContractError("workflow-trace example: first stage must understand the question")
    if trace["terminal_state"] == "succeeded" and stages[-1]["stage"] != "completed":
        raise ContractError("workflow-trace example: succeeded trace must end at completed")
    if trace["terminal_state"] is not None and trace["finished_at"] is None:
        raise ContractError("workflow-trace example: terminal trace must have finished_at")


def validate_historical_scope_hashes() -> None:
    paths = {
        "v1.3": ROOT / "docs" / "product" / "researchforge-v1.3-scope.md",
        "v1.2": ROOT / "docs" / "product" / "researchforge-v1.2-scope-freeze.md",
    }
    for version, path in paths.items():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != HISTORICAL_SCOPE_SHA256[version]:
            raise ContractError(f"historical {version.upper()} scope hash changed")


def require_text(path: Path, expected_fragments: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    for fragment in expected_fragments:
        if fragment not in text:
            raise ContractError(
                f"{path.relative_to(ROOT)}: missing required contract text {fragment!r}"
            )


def validate_schema_catalog(directory: Path, expected: set[str], label: str) -> None:
    actual = {path.name for path in directory.glob("*.schema.json")}
    missing = expected - actual
    unexpected = actual - expected
    if missing or unexpected:
        raise ContractError(
            f"{label} schema catalog mismatch; missing={sorted(missing)}, "
            f"unexpected={sorted(unexpected)}"
        )


def validate_example_catalog(
    directory: Path,
    expected: dict[str, str],
    schema_directory: Path,
    schemas: dict[Path, dict[str, Any]],
    label: str,
) -> dict[str, dict[str, Any]]:
    actual_names = {path.name for path in directory.glob("*.json")}
    expected_names = set(expected)
    if actual_names != expected_names:
        raise ContractError(
            f"{label} example catalog mismatch; missing={sorted(expected_names - actual_names)}, "
            f"unexpected={sorted(actual_names - expected_names)}"
        )

    examples: dict[str, dict[str, Any]] = {}
    for example_name, schema_name in expected.items():
        example = load_json(directory / example_name)
        if not isinstance(example, dict):
            raise ContractError(f"{label}/{example_name}: example root must be object")
        schema_path = (schema_directory / schema_name).resolve()
        validate_instance(example, schemas[schema_path], schema_path, schemas)
        examples[example_name] = example
    return examples


def validate_v14_semantics(
    schemas: dict[Path, dict[str, Any]],
    examples: dict[str, dict[str, Any]],
) -> None:
    common = schemas[(SCHEMA_DIR / "common.schema.json").resolve()]
    model_config = common["$defs"]["modelConfig"]
    required_model_fields = {
        "provider",
        "model_id",
        "model_snapshot",
        "temperature",
        "reasoning_effort",
        "max_output_tokens",
        "tool_choice_policy",
        "store",
        "built_in_tools",
    }
    if not required_model_fields.issubset(set(model_config["required"])):
        raise ContractError("V1.4 model configuration is missing reproducibility fields")
    if model_config["properties"]["store"].get("const") is not False:
        raise ContractError("V1.4 model configuration must require store=false")
    if model_config["properties"]["built_in_tools"].get("maxItems") != 0:
        raise ContractError("V1.4 model configuration must prohibit built-in tools")

    model_examples = (
        examples["run-manifest.research.example.json"]["configuration"]["model"],
        examples["run-manifest.patch-generation.example.json"]["configuration"]["model"],
        examples["evolution-experiment.example.json"]["model"],
        examples["simulated-usability-evaluation.example.json"]["model"],
    )
    for model in model_examples:
        expected_values = {
            "provider": "openai",
            "model_id": "gpt-5.6-luna",
            "reasoning_effort": "medium",
            "store": False,
            "built_in_tools": [],
        }
        for key, value in expected_values.items():
            if model.get(key) != value:
                raise ContractError(f"V1.4 example model must set {key}={value!r}")

    simulation_schema = schemas[
        (SCHEMA_DIR / "simulated-usability-evaluation.schema.json").resolve()
    ]
    simulation_properties = simulation_schema["properties"]
    if simulation_properties["evidence_label"].get("const") != "SIMULATED":
        raise ContractError("simulated usability evidence must be labeled SIMULATED")
    if simulation_properties["human_user_value_validated"].get("const") is not False:
        raise ContractError("simulated usability evidence cannot validate human value")
    if simulation_properties["session_number"].get("maximum") != 3:
        raise ContractError("simulated usability contract must be bounded to three sessions")

    evolution_schema = schemas[(SCHEMA_DIR / "evolution-experiment.schema.json").resolve()]
    threshold_properties = evolution_schema["properties"]["thresholds"]["properties"]
    expected_evolution_thresholds = {
        "repair_rate_min": 0.5,
        "regression_rate_max": 0.05,
        "task_score_drop_max": 0.02,
        "cluster_support_min": 3,
        "cluster_share_min": 0.2,
    }
    for key, value in expected_evolution_thresholds.items():
        if threshold_properties[key].get("const") != value:
            raise ContractError(f"evolution threshold {key} must remain {value}")
    budget_properties = evolution_schema["properties"]["budget"]["properties"]
    if budget_properties["cap"].get("maximum") != 20:
        raise ContractError("evolution experiment budget must have a USD 20 ceiling")

    retrieval_schema = schemas[(SCHEMA_DIR / "retrieval-evaluation.schema.json").resolve()]
    retrieval_thresholds = retrieval_schema["properties"]["thresholds"]["properties"]
    expected_retrieval_thresholds = {
        "recall_at_5_gain_min": 0.1,
        "new_citation_mismatches_max": 0,
        "p95_latency_multiplier_max": 2,
    }
    for key, value in expected_retrieval_thresholds.items():
        if retrieval_thresholds[key].get("const") != value:
            raise ContractError(f"retrieval threshold {key} must remain {value}")

    experiment = examples["evolution-experiment.example.json"]
    splits = experiment["split_case_ids"]
    expected_split_sizes = {"evolution": 12, "validation": 6, "final_test": 6}
    all_case_ids: list[str] = []
    for split_name, expected_size in expected_split_sizes.items():
        case_ids = splits[split_name]
        if len(case_ids) != expected_size:
            raise ContractError(f"primary {split_name} split must contain {expected_size} cases")
        all_case_ids.extend(case_ids)
    if len(all_case_ids) != 24 or len(set(all_case_ids)) != 24:
        raise ContractError("primary experiment must freeze 24 non-overlapping case IDs")
    allowed_prefixes = {
        "evolution": ("case_catl_", "case_eve_"),
        "validation": ("case_gotion_",),
        "final_test": ("case_sunwoda_",),
    }
    for split_name, prefixes in allowed_prefixes.items():
        if not all(case_id.startswith(prefixes) for case_id in splits[split_name]):
            raise ContractError(f"primary {split_name} company isolation changed")

    active_requirements = {
        ROOT / "docs" / "product" / "researchforge-v1.4-scope.md": (
            "`SIMULATED`",
            "`SUPPORTED`",
            "USD 20",
            "CATL (`300750.SZ`)",
            "Sunwoda (`300207.SZ`)",
            "Zhuhai CosMX (`688772.SH`)",
        ),
        ROOT / "docs" / "architecture" / "implementation-blueprint.md": (
            "POST /v1/research-runs",
            "GET /v1/research-runs/{run_id}/result",
            "GET /v1/research-runs/{run_id}/trace",
            "POST /v1/research-runs/{run_id}/cancel",
            "GET /v1/catalog",
            "gpt-5.6-luna",
        ),
        ROOT / "docs" / "contracts" / "product-success-metrics.md": (
            "SIMULATED",
            "human_user_value_validated: false",
        ),
        ROOT / "DATA_NOTICE.md": (
            "complete third-party announcement or annual-report PDFs",
            "synthetic evidence",
        ),
    }
    for path, fragments in active_requirements.items():
        require_text(path, fragments)


def validate_v15_product_semantics(
    schemas: dict[Path, dict[str, Any]],
    examples: dict[str, dict[str, Any]],
) -> None:
    request_schema = schemas[
        (ACTIVE_PRODUCT_SCHEMA_DIR / "product-research-request.schema.json").resolve()
    ]
    if request_schema["properties"]["data_namespace"].get("const") != "product":
        raise ContractError("V1.5 product requests must require the product namespace")

    ingestion_schema = schemas[
        (ACTIVE_PRODUCT_SCHEMA_DIR / "ingestion-manifest.schema.json").resolve()
    ]
    if ingestion_schema["properties"]["data_namespace"].get("const") != "product":
        raise ContractError("V1.5 ingestion must require the product namespace")
    raw_payload = ingestion_schema["properties"]["acquisition"]["anyOf"][0]["properties"][
        "raw_payload_committed"
    ]
    if raw_payload.get("const") is not False:
        raise ContractError("V1.5 ingestion must prohibit committing raw filings")

    human_schema = schemas[
        (ACTIVE_PRODUCT_SCHEMA_DIR / "human-usability-session.schema.json").resolve()
    ]
    if human_schema["properties"]["evidence_label"].get("const") != "REAL_HUMAN":
        raise ContractError("V1.5 human pilot records must be labeled REAL_HUMAN")
    if human_schema["properties"]["simulated"].get("const") is not False:
        raise ContractError("V1.5 human pilot records cannot be simulated")

    final_human_schema = schemas[
        (ACTIVE_PRODUCT_SCHEMA_DIR / "final-human-evaluation-session.schema.json").resolve()
    ]
    if final_human_schema["properties"]["simulated"].get("const") is not False:
        raise ContractError("final human evaluation records cannot be simulated")
    protocol_version = final_human_schema["properties"]["protocol_version"].get("const")
    if protocol_version != "final-dual-surface-v1.0-frozen":
        raise ContractError("final human evaluation protocol must remain frozen")
    final_template = examples["final-human-evaluation-session.template.json"]
    if (
        final_template["status"] != "scheduled"
        or final_template["evidence_label"] != "TEMPLATE_ONLY"
        or final_template["study_started"] is not False
        or final_template["consent"]["obtained"] is not False
    ):
        raise ContractError("final human evaluation example must remain non-evidence preparation")
    surfaces = [attempt["surface"] for attempt in final_template["surface_attempts"]]
    if sorted(surfaces) != ["n8n", "web"]:
        raise ContractError("final human evaluation template must cover Web and n8n exactly once")
    for attempt in final_template["surface_attempts"]:
        if attempt["attempt_status"] != "not_started" or any(
            outcome != "not_attempted" for outcome in attempt["common_outcomes"].values()
        ):
            raise ContractError("final human template cannot contain fabricated task outcomes")

    ingestion = examples["ingestion-manifest.example.json"]
    if ingestion["status"] != "ready" or ingestion["abstentions"]:
        raise ContractError("V1.5 ingestion example must be a ready, non-abstained package")
    if ingestion["acquisition"]["content_hash"] != (
        "2a690cb2471c1f0d4539d909a9f068c03710a838ddd35313175790169e85eab1"
    ):
        raise ContractError("V1.5 CATL example must retain the reviewed official PDF hash")
    extraction = ingestion["extraction"]
    expected_metrics = {
        "revenue",
        "operating_cost",
        "net_income",
        "operating_cash_flow",
        "accounts_receivable",
        "inventory",
    }
    if extraction["llm_used"] is not False or extraction["numerical_truth_source"] != (
        "verified_pdf"
    ):
        raise ContractError("V1.5 numerical truth must be deterministic verified-PDF recovery")
    if set(extraction["target_metrics"]) != expected_metrics:
        raise ContractError("V1.5 extraction must target exactly the six frozen metrics")
    for recovery in extraction["recoveries"]:
        _validate_extraction_recovery(recovery, f"example:{recovery['metric_code']}")

    active_requirements = {
        ROOT / "README.md": (
            "Auditable autonomous financial research for public companies",
            "Company name / ticker + optional market + optional period + research question",
            "V1.6 Autonomous Research",
            "Quality Lab",
        ),
        ROOT / "docs" / "product" / "researchforge-v1.5-product-thesis.md": (
            "## 1. Problem",
            "## 2. Target User",
            "## 3. Job To Be Done",
            "## 4. Product Promise",
            "## 6. Core Workflow",
            "## 7. User Story",
            "## 8. V1.4 Starting Audit and V1.5 Closure Status",
            "## 9. V1.5 Scope",
            "## 11. Non-goals",
            "## 12. Acceptance Criteria",
            "## 14. Migration Plan from V1.4",
            "RESEARCH_HYPOTHESIS_UNSUPPORTED_AFTER_TWO_EXPERIMENTS",
        ),
        ROOT / "docs" / "contracts" / "v1.5" / "real-data-ingestion.md": (
            "MUST NOT search or",
            "abstention",
            "300750.SZ",
        ),
        ROOT / "docs" / "usability" / "pilot-status.md": (
            "PREPARATION_ONLY",
            "FORMAL EVALUATION DEFERRED TO PHASE 6",
            "UNVALIDATED",
            "Completed real-human sessions | 0",
        ),
        ROOT / "docs" / "demo" / "v1.5-demo-evidence.md": (
            "fdd6cc077607144b46b741aae3fe713eae09ca7c54c00bfbc43960847be45765",
            "run_b69d4aaf34e045c19619d4b9f88ebaca",
            "run_158b579d17b84c5db602847ab864f340",
        ),
    }
    for path, fragments in active_requirements.items():
        require_text(path, fragments)


def validate_seed_skill(schemas: dict[Path, dict[str, Any]]) -> None:
    version_directory = ROOT / "skills" / "fundamental-research" / "versions" / "1.0.0"
    manifest_path = version_directory / "skill-version.json"
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ContractError("seed skill version manifest must be an object")
    schema_path = (SCHEMA_DIR / "skill-version.schema.json").resolve()
    validate_instance(manifest, schemas[schema_path], schema_path, schemas)

    content_path = (ROOT / manifest["content_path"]).resolve()
    if ROOT not in content_path.parents:
        raise ContractError("seed skill content path escapes the project")
    if content_path.parent != version_directory:
        raise ContractError("seed skill manifest must reference its immutable version directory")
    digest = hashlib.sha256(content_path.read_bytes()).hexdigest()
    if digest != manifest["content_hash"]:
        raise ContractError("seed skill content hash does not match its manifest")
    if manifest["status"] != "seed" or manifest["parent_version_id"] is not None:
        raise ContractError("initial fundamental-research skill must be a parentless seed")


def _decimal(value: Any, label: str) -> Decimal:
    if not isinstance(value, str):
        raise ContractError(f"{label}: Decimal value must be a string")
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ContractError(f"{label}: invalid Decimal value {value!r}") from exc


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _validate_extraction_recovery(recovery: dict[str, Any], label: str) -> None:
    if recovery["line_end"] < recovery["line_start"]:
        raise ContractError(f"{label}: extraction source line range is reversed")
    evidence_hash = hashlib.sha256(recovery["evidence_text"].encode("utf-8")).hexdigest()
    if evidence_hash != recovery["evidence_text_hash"]:
        raise ContractError(f"{label}: extraction evidence hash is invalid")

    raw = re.sub(r"\s+", "", recovery["raw_value"])
    parenthesized = raw.startswith("(") and raw.endswith(")")
    raw = raw.strip("()\uff08\uff09").replace(",", "").replace("\u2212", "-").replace("\uff0d", "-")
    raw_decimal = _decimal(raw, f"{label}:raw_value")
    if parenthesized:
        raw_decimal = -raw_decimal
    reported = _decimal(recovery["reported_value"], f"{label}:reported_value")
    normalized = _decimal(recovery["normalized_value"], f"{label}:normalized_value")
    if raw_decimal != reported or reported * recovery["scale"] != normalized:
        raise ContractError(f"{label}: extraction numerical normalization is invalid")

    recovery_material = {
        key: recovery[key]
        for key in (
            "metric_code",
            "statement",
            "page",
            "line_start",
            "line_end",
            "row_label",
            "column_label",
            "raw_value",
            "reported_value",
            "unit_label",
            "scale",
            "normalized_value",
            "evidence_text_hash",
            "page_text_hash",
        )
    }
    if _canonical_hash(recovery_material) != recovery["recovery_hash"]:
        raise ContractError(f"{label}: extraction recovery hash is invalid")


def _fixture_package_hash(artifact_hashes: dict[str, str]) -> str:
    return _canonical_hash(artifact_hashes)


def _validate_golden_case_calculations(
    case: dict[str, Any], facts: dict[str, dict[str, Any]]
) -> None:
    grouped: dict[str, dict[str, Decimal]] = {}
    for fact_id in case["fact_ids"]:
        fact = facts[fact_id]
        grouped.setdefault(fact["company"]["company_id"], {})[fact["metric_code"]] = _decimal(
            fact["value"], f"{case['case_id']}:{fact_id}"
        )

    expected_metrics = {"revenue", "operating_cost", "net_income", "operating_cash_flow"}
    expected: dict[str, dict[str, Decimal]] = {}
    for company_id, metrics in grouped.items():
        if set(metrics) != expected_metrics:
            raise ContractError(
                f"{case['case_id']}: company {company_id} has wrong calculation inputs"
            )
        gross_profit = metrics["revenue"] - metrics["operating_cost"]
        if metrics["revenue"] <= 0 or metrics["net_income"] <= 0:
            raise ContractError(f"{case['case_id']}: frozen ratio denominator is not positive")
        expected[company_id] = {
            "gross_profit": gross_profit,
            "gross_margin": gross_profit / metrics["revenue"],
            "cash_conversion": metrics["operating_cash_flow"] / metrics["net_income"],
            "profit_cash_divergence": Decimal(
                int(metrics["net_income"] > 0 and metrics["operating_cash_flow"] < 0)
            ),
        }

    calculations = case["calculations"]
    if case["task_type"] == "company_research":
        company_id = case["companies"][0]
        actual_by_company = {company_id: calculations}
    else:
        company_labels = {"cn_300750": "catl", "cn_300014": "eve"}
        actual_by_company = {
            company_id: calculations[company_labels[company_id]] for company_id in case["companies"]
        }
    for company_id, expected_values in expected.items():
        actual_values = actual_by_company[company_id]
        if set(actual_values) != set(expected_values):
            raise ContractError(f"{case['case_id']}: calculation catalog changed")
        for formula_code, expected_value in expected_values.items():
            actual_value = _decimal(
                actual_values[formula_code],
                f"{case['case_id']}:{company_id}:{formula_code}",
            )
            if actual_value != expected_value:
                raise ContractError(
                    f"{case['case_id']}:{company_id}:{formula_code}: calculation mismatch"
                )


def validate_g0_fixtures(schemas: dict[Path, dict[str, Any]]) -> tuple[int, int, int]:
    """Validate the frozen G0 source package and deterministic golden cases."""
    source_paths = sorted(G0_SOURCE_DIR.glob("*.json"))
    fact_paths = sorted(G0_FACT_DIR.glob("*.json"))
    if len(source_paths) != 8 or len(fact_paths) != 48:
        raise ContractError(
            f"G0 fixture catalog must contain 8 source documents and 48 facts; "
            f"found {len(source_paths)} and {len(fact_paths)}"
        )
    if any(G0_FIXTURE_DIR.rglob("*.pdf")):
        raise ContractError("G0 public fixture package must not contain raw PDFs")

    source_schema_path = (SCHEMA_DIR / "source-document.schema.json").resolve()
    fact_schema_path = (SCHEMA_DIR / "financial-fact.schema.json").resolve()
    sources: dict[str, dict[str, Any]] = {}
    for path in source_paths:
        source = load_json(path)
        if not isinstance(source, dict):
            raise ContractError(f"{path.relative_to(ROOT)}: source document must be an object")
        validate_instance(source, schemas[source_schema_path], source_schema_path, schemas)
        document_id = source["document_id"]
        if document_id in sources:
            raise ContractError(f"G0 source document ID is duplicated: {document_id}")
        if source["license"]["raw_payload_committed"] is not False:
            raise ContractError(f"{document_id}: raw filing commitment must remain false")
        if datetime.fromisoformat(source["published_at"]) > datetime.fromisoformat(
            source["retrieved_at"]
        ):
            raise ContractError(f"{document_id}: retrieval precedes publication")
        sources[document_id] = source

    facts: dict[str, dict[str, Any]] = {}
    metrics_by_document: dict[str, set[str]] = {document_id: set() for document_id in sources}
    for path in fact_paths:
        fact = load_json(path)
        if not isinstance(fact, dict):
            raise ContractError(f"{path.relative_to(ROOT)}: financial fact must be an object")
        validate_instance(fact, schemas[fact_schema_path], fact_schema_path, schemas)
        fact_id = fact["fact_id"]
        if fact_id in facts:
            raise ContractError(f"G0 fact ID is duplicated: {fact_id}")
        document_id = fact["source"]["document_id"]
        source = sources.get(document_id)
        if source is None:
            raise ContractError(f"{fact_id}: source document does not exist")
        if fact["company"] != source["company"]:
            raise ContractError(f"{fact_id}: company differs from source document")
        if fact["source"]["content_hash"] != source["content_hash"]:
            raise ContractError(f"{fact_id}: source content hash differs from document")
        if fact["source"]["published_at"] != source["published_at"]:
            raise ContractError(f"{fact_id}: publication time differs from document")
        locator = fact["source_locator"]
        if not all(
            locator.get(key) for key in ("page", "section", "table", "row_label", "column_label")
        ):
            raise ContractError(f"{fact_id}: incomplete source locator")
        if fact["value"] is None:
            raise ContractError(f"{fact_id}: G0 reviewed sample cannot contain a missing value")
        _decimal(fact["value"], fact_id)
        metrics_by_document[document_id].add(fact["metric_code"])
        facts[fact_id] = fact

    for document_id, metrics in metrics_by_document.items():
        if metrics != G0_REQUIRED_METRICS:
            raise ContractError(f"{document_id}: required metric set changed")
    corrected = sources.get("doc_g0_eve_2024h1_corrected")
    if corrected is None or corrected["reporting_period"]["restatement_status"] != "restated":
        raise ContractError("corrected EVE H1 source must retain restated lineage")

    manifest = load_json(G0_MANIFEST_PATH)
    if not isinstance(manifest, dict):
        raise ContractError("G0 manifest must be an object")
    if manifest["schema_version"] != CURRENT_ARTIFACT_VERSION:
        raise ContractError("G0 manifest schema version changed")
    if manifest["status"] != "owner_signed":
        raise ContractError("G0 manifest must retain the completed owner signoff")
    if manifest["source_document_count"] != 8 or manifest["financial_fact_count"] != 48:
        raise ContractError("G0 manifest counts changed")
    if set(manifest["source_document_ids"]) != set(sources):
        raise ContractError("G0 manifest source IDs do not match the package")
    if set(manifest["financial_fact_ids"]) != set(facts):
        raise ContractError("G0 manifest fact IDs do not match the package")

    reconciliation = manifest["reconciliation"]
    expected_reconciliation = {
        "sample_size": 48,
        "semantic_complete_count": 48,
        "visual_match_count": 48,
        "unresolved_mismatch_count": 0,
        "semantic_completeness_rate": "1.0",
        "numeric_agreement_rate": "1.0",
    }
    for key, expected_value in expected_reconciliation.items():
        if reconciliation.get(key) != expected_value:
            raise ContractError(f"G0 reconciliation {key} must equal {expected_value!r}")
    cells = reconciliation["cells"]
    if len(cells) != 48 or {cell["fact_id"] for cell in cells} != set(facts):
        raise ContractError("G0 reconciliation cells do not cover the 48 facts exactly")
    for cell in cells:
        fact_id = cell["fact_id"]
        reported_value = _decimal(cell["reported_value"], f"{fact_id}:reported")
        scale = cell["reported_scale"]
        if not isinstance(scale, int) or isinstance(scale, bool) or scale <= 0:
            raise ContractError(f"{fact_id}: reported scale must be a positive integer")
        canonical = _decimal(cell["canonical_value"], f"{fact_id}:canonical")
        if canonical != reported_value * Decimal(scale):
            raise ContractError(f"{fact_id}: unit normalization mismatch")
        if canonical != _decimal(facts[fact_id]["value"], fact_id):
            raise ContractError(f"{fact_id}: manifest and fact values differ")
        if cell["visual_match"] is not True:
            raise ContractError(f"{fact_id}: visual reconciliation must pass")

    golden = load_json(G0_GOLDEN_CASES_PATH)
    if not isinstance(golden, dict) or golden.get("fixture_version") != "1.0.0":
        raise ContractError("G0 golden-case fixture version changed")
    if golden.get("review_status") != "owner_signed":
        raise ContractError("G0 golden cases must retain the completed owner signoff")
    cases = golden.get("cases")
    if not isinstance(cases, list) or len(cases) != 3:
        raise ContractError("G0 requires exactly three golden cases")
    case_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ContractError("G0 golden case must be an object")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or case_id in case_ids:
            raise ContractError("G0 golden case IDs must be unique strings")
        case_ids.add(case_id)
        fact_ids = case.get("fact_ids")
        if not isinstance(fact_ids, list) or not fact_ids or not set(fact_ids) <= set(facts):
            raise ContractError(f"{case_id}: golden-case fact IDs are invalid")
        research_time = datetime.fromisoformat(case["research_time"])
        if any(
            datetime.fromisoformat(facts[fact_id]["source"]["published_at"]) > research_time
            for fact_id in fact_ids
        ):
            raise ContractError(f"{case_id}: contains evidence published after research time")
        _validate_golden_case_calculations(case, facts)

    artifact_paths = sorted((*source_paths, *fact_paths, G0_GOLDEN_CASES_PATH))
    expected_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in artifact_paths
    }
    if manifest["artifact_hashes"] != expected_hashes:
        raise ContractError("G0 artifact hashes do not match public fixture files")
    if manifest["package_hash"] != _fixture_package_hash(expected_hashes):
        raise ContractError("G0 package hash does not match artifact hashes")

    signoff = manifest["owner_signoff"]
    signoff_ids = signoff["fact_ids"]
    if signoff["sample_size"] != 20 or len(signoff_ids) != 20:
        raise ContractError("G0 owner signoff sample must contain exactly 20 facts")
    if len(set(signoff_ids)) != 20 or not set(signoff_ids) <= set(facts):
        raise ContractError("G0 owner signoff fact sample is duplicated or unknown")
    if signoff["status"] != "signed" or signoff["signed_at"] is None:
        raise ContractError("G0 owner signoff must remain signed")
    signoff_path = (ROOT / signoff["evidence_file"]).resolve()
    if ROOT not in signoff_path.parents or not signoff_path.is_file():
        raise ContractError("G0 owner signoff evidence path is invalid")
    signoff_text = signoff_path.read_text(encoding="utf-8")
    for expected_text in (signoff["signed_at"], manifest["package_hash"], "Status: `SIGNED`"):
        if expected_text not in signoff_text:
            raise ContractError("G0 owner signoff evidence does not match the manifest")

    return len(source_paths), len(fact_paths), len(cases)


def validate_primary_benchmark(
    schemas: dict[Path, dict[str, Any]],
) -> tuple[int, int, int, int]:
    """Validate the frozen public package without opening verifier-only truth."""
    source_paths = sorted(PRIMARY_SOURCE_DIR.glob("*.json"))
    fact_paths = sorted(PRIMARY_FACT_DIR.glob("*.json"))
    chunk_paths = sorted(PRIMARY_CHUNK_DIR.glob("*.json"))
    case_paths = sorted(PRIMARY_CASE_DIR.glob("*.json"))
    expected_counts = (24, 144, 24, 24)
    actual_counts = (len(source_paths), len(fact_paths), len(chunk_paths), len(case_paths))
    if actual_counts != expected_counts:
        raise ContractError(
            "primary benchmark must contain 24 sources, 144 facts, 24 chunks, and "
            f"24 cases; found {actual_counts}"
        )
    if any(PRIMARY_FIXTURE_DIR.rglob("*.pdf")):
        raise ContractError("primary public package must not contain raw PDFs")

    schema_names = {
        "source": "source-document.schema.json",
        "fact": "financial-fact.schema.json",
        "chunk": "evidence-chunk.schema.json",
        "case": "benchmark-case.schema.json",
    }
    schema_paths = {key: (SCHEMA_DIR / name).resolve() for key, name in schema_names.items()}

    sources: dict[str, dict[str, Any]] = {}
    for path in source_paths:
        source = load_json(path)
        if not isinstance(source, dict):
            raise ContractError(f"{path.relative_to(ROOT)}: source must be an object")
        validate_instance(source, schemas[schema_paths["source"]], schema_paths["source"], schemas)
        document_id = source["document_id"]
        if document_id in sources:
            raise ContractError(f"primary source ID is duplicated: {document_id}")
        if urlparse(source["source_uri"]).netloc not in {
            "static.cninfo.com.cn",
            "disc.static.szse.cn",
        }:
            raise ContractError(
                f"{document_id}: source must be an official CNInfo or SZSE artifact"
            )
        if source["license"]["raw_payload_committed"] is not False:
            raise ContractError(f"{document_id}: raw filing must remain excluded")
        sources[document_id] = source

    facts: dict[str, dict[str, Any]] = {}
    metrics_by_document: dict[str, set[str]] = {document_id: set() for document_id in sources}
    for path in fact_paths:
        fact = load_json(path)
        if not isinstance(fact, dict):
            raise ContractError(f"{path.relative_to(ROOT)}: fact must be an object")
        validate_instance(fact, schemas[schema_paths["fact"]], schema_paths["fact"], schemas)
        fact_id = fact["fact_id"]
        if fact_id in facts:
            raise ContractError(f"primary fact ID is duplicated: {fact_id}")
        document_id = fact["source"]["document_id"]
        source = sources.get(document_id)
        if source is None:
            raise ContractError(f"{fact_id}: source document does not exist")
        if fact["company"] != source["company"]:
            raise ContractError(f"{fact_id}: company differs from source")
        if fact["source"]["content_hash"] != source["content_hash"]:
            raise ContractError(f"{fact_id}: source hash differs from document")
        if fact["source"]["published_at"] != source["published_at"]:
            raise ContractError(f"{fact_id}: publication time differs from document")
        if fact["value"] is None:
            raise ContractError(f"{fact_id}: frozen benchmark fact cannot be missing")
        _decimal(fact["value"], fact_id)
        locator = fact["source_locator"]
        if not all(
            locator.get(key) for key in ("page", "section", "table", "row_label", "column_label")
        ):
            raise ContractError(f"{fact_id}: incomplete physical-page locator")
        metrics_by_document[document_id].add(fact["metric_code"])
        facts[fact_id] = fact
    for document_id, metrics in metrics_by_document.items():
        if metrics != G0_REQUIRED_METRICS:
            raise ContractError(f"{document_id}: required metric set changed")

    chunks: dict[str, dict[str, Any]] = {}
    for path in chunk_paths:
        chunk = load_json(path)
        if not isinstance(chunk, dict):
            raise ContractError(f"{path.relative_to(ROOT)}: chunk must be an object")
        validate_instance(chunk, schemas[schema_paths["chunk"]], schema_paths["chunk"], schemas)
        chunk_id = chunk["chunk_id"]
        if chunk_id in chunks:
            raise ContractError(f"primary evidence chunk ID is duplicated: {chunk_id}")
        if chunk["document_id"] not in sources:
            raise ContractError(f"{chunk_id}: source document does not exist")
        if not chunk["text"].startswith("SYNTHETIC PUBLIC EVIDENCE"):
            raise ContractError(f"{chunk_id}: public evidence must remain explicitly synthetic")
        if hashlib.sha256(chunk["text"].encode()).hexdigest() != chunk["text_hash"]:
            raise ContractError(f"{chunk_id}: text hash mismatch")
        chunks[chunk_id] = chunk

    cases: dict[str, dict[str, Any]] = {}
    groups_by_split: dict[str, set[str]] = {
        "evolution": set(),
        "validation": set(),
        "final_test": set(),
    }
    for path in case_paths:
        case = load_json(path)
        if not isinstance(case, dict):
            raise ContractError(f"{path.relative_to(ROOT)}: case must be an object")
        validate_instance(case, schemas[schema_paths["case"]], schema_paths["case"], schemas)
        case_id = case["case_id"]
        if case_id in cases:
            raise ContractError(f"primary case ID is duplicated: {case_id}")
        if (
            len(case["target_periods"]) != 1
            or len(case["allowed_document_ids"]) != 1
            or len(case["allowed_evidence_chunk_ids"]) != 1
            or len(case["allowed_financial_fact_ids"]) != 6
        ):
            raise ContractError(f"{case_id}: case must bind one six-metric target report")
        document_id = case["allowed_document_ids"][0]
        source = sources.get(document_id)
        if source is None:
            raise ContractError(f"{case_id}: allowed document does not exist")
        chunk_id = case["allowed_evidence_chunk_ids"][0]
        if chunks.get(chunk_id, {}).get("document_id") != document_id:
            raise ContractError(f"{case_id}: evidence chunk differs from target document")
        case_facts: list[dict[str, Any]] = []
        for fact_id in case["allowed_financial_fact_ids"]:
            fact = facts.get(fact_id)
            if fact is None:
                raise ContractError(f"{case_id}: allowed fact does not exist")
            case_facts.append(fact)
        if any(fact["source"]["document_id"] != document_id for fact in case_facts):
            raise ContractError(f"{case_id}: fact leaks from another target document")
        if case["company"] != source["company"] or case["target_periods"] != [
            source["reporting_period"]
        ]:
            raise ContractError(f"{case_id}: company or period differs from source")
        if datetime.fromisoformat(source["published_at"]) > datetime.fromisoformat(
            case["research_time"]
        ):
            raise ContractError(f"{case_id}: source was unavailable at research time")
        if case["sealed"] is not (case["split"] == "final_test"):
            raise ContractError(f"{case_id}: final-test sealing policy changed")
        groups_by_split[case["split"]].add(case["group_key"])
        cases[case_id] = case

    if groups_by_split != {
        "evolution": {"cn_300750", "cn_300014"},
        "validation": {"cn_002074"},
        "final_test": {"cn_300207"},
    }:
        raise ContractError("primary company split assignment changed")
    if any(
        groups_by_split[left] & groups_by_split[right]
        for left, right in (
            ("evolution", "validation"),
            ("evolution", "final_test"),
            ("validation", "final_test"),
        )
    ):
        raise ContractError("primary company groups cross benchmark splits")

    manifest = load_json(PRIMARY_MANIFEST_PATH)
    if not isinstance(manifest, dict):
        raise ContractError("primary manifest must be an object")
    expected_manifest_values = {
        "schema_version": CURRENT_ARTIFACT_VERSION,
        "evidence_status": "SIGNED",
        "formal_run_authorized": True,
        "source_document_count": 24,
        "financial_fact_count": 144,
        "evidence_chunk_count": 24,
        "case_count": 24,
        "split_counts": {"evolution": 12, "validation": 6, "final_test": 6},
        "raw_pdf_committed": False,
        "ground_truth_committed": False,
    }
    for key, expected in expected_manifest_values.items():
        if manifest.get(key) != expected:
            raise ContractError(f"primary manifest {key} must equal {expected!r}")
    if manifest["owner_signoff"] != {
        "status": "signed",
        "signed_at": "2026-09-01T19:14:33+08:00",
        "evidence_file": "docs/evidence/g3-primary-data-signoff.md",
    }:
        raise ContractError("primary package must retain the completed second owner signoff")
    if len(manifest["ground_truth_hashes"]) != 24 or set(manifest["ground_truth_hashes"]) != set(
        cases
    ):
        raise ContractError("primary ground-truth hash catalog differs from cases")
    for case_id, case in cases.items():
        if (
            case["verifier_ground_truth_ref"]["artifact_hash"]
            != manifest["ground_truth_hashes"][case_id]
        ):
            raise ContractError(f"{case_id}: verifier-only ground-truth hash differs")

    artifact_paths = sorted((*source_paths, *fact_paths, *chunk_paths, *case_paths))
    artifact_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in artifact_paths
    }
    if manifest["public_artifact_hashes"] != artifact_hashes:
        raise ContractError("primary public artifact hashes do not match package files")
    data_hashes = {
        **{f"source:{key}": _canonical_hash(value) for key, value in sources.items()},
        **{f"fact:{key}": _canonical_hash(value) for key, value in facts.items()},
        **{f"chunk:{key}": _canonical_hash(value) for key, value in chunks.items()},
        **{f"ground_truth:{key}": value for key, value in manifest["ground_truth_hashes"].items()},
        "preregistered_suite": hashlib.sha256(PRIMARY_SUITE_PATH.read_bytes()).hexdigest(),
    }
    if manifest["package_hash"] != _canonical_hash(data_hashes):
        raise ContractError("primary package hash does not match frozen inputs")
    if {case["package_hash"] for case in cases.values()} != {manifest["package_hash"]}:
        raise ContractError("primary cases do not share the frozen package hash")

    suite = load_json(PRIMARY_SUITE_PATH)
    expected_case_ids = {
        split: {entry["case_id"] for entry in suite["splits"][split]}
        for split in ("evolution", "validation", "final_test")
    }
    actual_case_ids = {
        split: {case_id for case_id, case in cases.items() if case["split"] == split}
        for split in ("evolution", "validation", "final_test")
    }
    if actual_case_ids != expected_case_ids:
        raise ContractError("primary cases differ from pre-registered split manifest")

    return actual_counts


def validate_contingency_benchmark(
    schemas: dict[Path, dict[str, Any]],
) -> tuple[int, int, int, int]:
    """Validate the sealed, primary-disjoint V1.5 contingency package."""
    source_paths = sorted(CONTINGENCY_SOURCE_DIR.glob("*.json"))
    fact_paths = sorted(CONTINGENCY_FACT_DIR.glob("*.json"))
    chunk_paths = sorted(CONTINGENCY_CHUNK_DIR.glob("*.json"))
    case_paths = sorted(CONTINGENCY_CASE_DIR.glob("*.json"))
    actual_counts = (len(source_paths), len(fact_paths), len(chunk_paths), len(case_paths))
    if actual_counts != (24, 144, 24, 24):
        raise ContractError(
            "contingency benchmark must contain 24 sources, 144 facts, 24 chunks, "
            f"and 24 cases; found {actual_counts}"
        )
    if any(CONTINGENCY_FIXTURE_DIR.rglob("*.pdf")):
        raise ContractError("contingency public package must not contain raw PDFs")

    schema_paths = {
        key: (SCHEMA_DIR / filename).resolve()
        for key, filename in {
            "source": "source-document.schema.json",
            "fact": "financial-fact.schema.json",
            "chunk": "evidence-chunk.schema.json",
            "case": "benchmark-case.schema.json",
        }.items()
    }
    sources: dict[str, dict[str, Any]] = {}
    for path in source_paths:
        source = load_json(path)
        if not isinstance(source, dict):
            raise ContractError(f"{path.relative_to(ROOT)}: source must be an object")
        validate_instance(source, schemas[schema_paths["source"]], schema_paths["source"], schemas)
        document_id = source["document_id"]
        if document_id in sources:
            raise ContractError(f"contingency source ID is duplicated: {document_id}")
        if urlparse(source["source_uri"]).netloc != "static.cninfo.com.cn":
            raise ContractError(f"{document_id}: source must be an official CNInfo artifact")
        if source["license"]["raw_payload_committed"] is not False:
            raise ContractError(f"{document_id}: raw filing must remain excluded")
        sources[document_id] = source

    facts: dict[str, dict[str, Any]] = {}
    metrics_by_document: dict[str, set[str]] = {document_id: set() for document_id in sources}
    for path in fact_paths:
        fact = load_json(path)
        if not isinstance(fact, dict):
            raise ContractError(f"{path.relative_to(ROOT)}: fact must be an object")
        validate_instance(fact, schemas[schema_paths["fact"]], schema_paths["fact"], schemas)
        fact_id = fact["fact_id"]
        document_id = fact["source"]["document_id"]
        source = sources.get(document_id)
        if fact_id in facts or source is None:
            raise ContractError(f"{fact_id}: duplicate ID or missing source document")
        if fact["company"] != source["company"]:
            raise ContractError(f"{fact_id}: company differs from source")
        if fact["source"]["content_hash"] != source["content_hash"]:
            raise ContractError(f"{fact_id}: source hash differs from document")
        if fact["value"] is None:
            raise ContractError(f"{fact_id}: frozen contingency fact cannot be missing")
        _decimal(fact["value"], fact_id)
        if not all(
            fact["source_locator"].get(key)
            for key in ("page", "section", "table", "row_label", "column_label")
        ):
            raise ContractError(f"{fact_id}: incomplete physical-page locator")
        metrics_by_document[document_id].add(fact["metric_code"])
        facts[fact_id] = fact
    if any(metrics != G0_REQUIRED_METRICS for metrics in metrics_by_document.values()):
        raise ContractError("contingency target document metric set changed")

    chunks: dict[str, dict[str, Any]] = {}
    for path in chunk_paths:
        chunk = load_json(path)
        if not isinstance(chunk, dict):
            raise ContractError(f"{path.relative_to(ROOT)}: chunk must be an object")
        validate_instance(chunk, schemas[schema_paths["chunk"]], schema_paths["chunk"], schemas)
        chunk_id = chunk["chunk_id"]
        if chunk_id in chunks or chunk["document_id"] not in sources:
            raise ContractError(f"{chunk_id}: duplicate ID or missing source document")
        if not chunk["text"].startswith("SYNTHETIC PUBLIC EVIDENCE"):
            raise ContractError(f"{chunk_id}: public evidence must remain explicitly synthetic")
        if hashlib.sha256(chunk["text"].encode()).hexdigest() != chunk["text_hash"]:
            raise ContractError(f"{chunk_id}: text hash mismatch")
        chunks[chunk_id] = chunk

    cases: dict[str, dict[str, Any]] = {}
    groups_by_split: dict[str, set[str]] = {
        "evolution": set(),
        "validation": set(),
        "final_test": set(),
    }
    for path in case_paths:
        case = load_json(path)
        if not isinstance(case, dict):
            raise ContractError(f"{path.relative_to(ROOT)}: case must be an object")
        validate_instance(case, schemas[schema_paths["case"]], schema_paths["case"], schemas)
        case_id = case["case_id"]
        if case_id in cases:
            raise ContractError(f"contingency case ID is duplicated: {case_id}")
        if tuple(
            len(case[field])
            for field in (
                "target_periods",
                "allowed_document_ids",
                "allowed_evidence_chunk_ids",
                "allowed_financial_fact_ids",
            )
        ) != (1, 1, 1, 6):
            raise ContractError(f"{case_id}: case must bind one six-metric target report")
        document_id = case["allowed_document_ids"][0]
        source = sources.get(document_id)
        chunk = chunks.get(case["allowed_evidence_chunk_ids"][0])
        case_facts = [facts.get(fact_id) for fact_id in case["allowed_financial_fact_ids"]]
        if source is None or chunk is None or any(fact is None for fact in case_facts):
            raise ContractError(f"{case_id}: references an unknown artifact")
        if chunk["document_id"] != document_id or any(
            fact["source"]["document_id"] != document_id for fact in case_facts if fact is not None
        ):
            raise ContractError(f"{case_id}: artifact leaks from another target document")
        if case["company"] != source["company"] or case["target_periods"] != [
            source["reporting_period"]
        ]:
            raise ContractError(f"{case_id}: company or period differs from source")
        if datetime.fromisoformat(source["published_at"]) > datetime.fromisoformat(
            case["research_time"]
        ):
            raise ContractError(f"{case_id}: source was unavailable at research time")
        if case["sealed"] is not (case["split"] == "final_test"):
            raise ContractError(f"{case_id}: final-test sealing policy changed")
        groups_by_split[case["split"]].add(case["group_key"])
        cases[case_id] = case

    expected_groups = {
        "evolution": {"cn_300438", "cn_688567"},
        "validation": {"cn_002594"},
        "final_test": {"cn_688772"},
    }
    if groups_by_split != expected_groups:
        raise ContractError("contingency company split assignment changed")
    all_groups = set().union(*groups_by_split.values())
    primary_groups = {load_json(path)["group_key"] for path in PRIMARY_CASE_DIR.glob("*.json")}
    if all_groups & primary_groups:
        raise ContractError("contingency company group overlaps the primary suite")

    manifest = load_json(CONTINGENCY_MANIFEST_PATH)
    if not isinstance(manifest, dict):
        raise ContractError("contingency manifest must be an object")
    expected_manifest_values = {
        "schema_version": CURRENT_ARTIFACT_VERSION,
        "evidence_status": "FROZEN_CONTINGENCY_SEALED",
        "formal_run_authorized": False,
        "contingency_activation_authorized": False,
        "sealed_until": "PRIMARY_VALIDATION_REJECTS_CANDIDATE",
        "source_document_count": 24,
        "financial_fact_count": 144,
        "evidence_chunk_count": 24,
        "case_count": 24,
        "split_counts": {"evolution": 12, "validation": 6, "final_test": 6},
        "raw_pdf_committed": False,
        "ground_truth_committed": False,
    }
    for key, expected in expected_manifest_values.items():
        if manifest.get(key) != expected:
            raise ContractError(f"contingency manifest {key} must equal {expected!r}")
    if manifest["representative_visual_review"]["status"] != "completed":
        raise ContractError("contingency representative visual review must be completed")
    if len(manifest["ground_truth_hashes"]) != 24 or set(manifest["ground_truth_hashes"]) != set(
        cases
    ):
        raise ContractError("contingency ground-truth hash catalog differs from cases")
    for case_id, case in cases.items():
        if (
            case["verifier_ground_truth_ref"]["artifact_hash"]
            != manifest["ground_truth_hashes"][case_id]
        ):
            raise ContractError(f"{case_id}: verifier-only ground-truth hash differs")

    artifact_paths = sorted((*source_paths, *fact_paths, *chunk_paths, *case_paths))
    expected_public_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in artifact_paths
    }
    if manifest["public_artifact_hashes"] != expected_public_hashes:
        raise ContractError("contingency public artifact hashes do not match package files")
    data_hashes = {
        **{f"source:{key}": _canonical_hash(value) for key, value in sources.items()},
        **{f"fact:{key}": _canonical_hash(value) for key, value in facts.items()},
        **{f"chunk:{key}": _canonical_hash(value) for key, value in chunks.items()},
        **{f"ground_truth:{key}": value for key, value in manifest["ground_truth_hashes"].items()},
        "preregistered_suite": hashlib.sha256(CONTINGENCY_SUITE_PATH.read_bytes()).hexdigest(),
    }
    if manifest["package_hash"] != _canonical_hash(data_hashes):
        raise ContractError("contingency package hash does not match frozen inputs")
    if {case["package_hash"] for case in cases.values()} != {manifest["package_hash"]}:
        raise ContractError("contingency cases do not share the frozen package hash")

    suite = load_json(CONTINGENCY_SUITE_PATH)
    if suite.get("purpose") != "ONE_TIME_CONTINGENCY_IF_V1_4_PRIMARY_HYPOTHESIS_IS_NOT_SUPPORTED":
        raise ContractError("contingency activation purpose changed")
    expected_case_ids = {
        split: {entry["case_id"] for entry in suite["splits"][split]}
        for split in ("evolution", "validation", "final_test")
    }
    actual_case_ids = {
        split: {case_id for case_id, case in cases.items() if case["split"] == split}
        for split in ("evolution", "validation", "final_test")
    }
    if actual_case_ids != expected_case_ids:
        raise ContractError("contingency cases differ from pre-registered split manifest")

    return actual_counts


def validate_n8n_evidence(schemas: dict[Path, dict[str, Any]]) -> None:
    """Check preserved Phase 4 outputs and the active Phase 5 workflow binding."""
    directory = ROOT / "docs/evidence/v1.5-n8n"
    summary = load_json(directory / "summary.json")
    workflow = ROOT / "integrations/n8n/researchforge.workflow.json"
    if summary["workflow_sha256"] != (
        "4993f55be251dd60df82c7de3dba43c89c06a10cddbc457dd1d7d55b9fb50bb2"
    ):
        raise ContractError("preserved Phase 4 n8n workflow binding changed")
    if summary["human_user_value_validated"] is not False or summary["status"] != "PASS":
        raise ContractError("n8n engineering evidence must not claim human validation")
    expected = {("cn_300750", "2024H1"), ("cn_300750", "2024FY"), ("cn_002594", "2024H1")}
    if {(row["company_id"], row["period"]) for row in summary["cases"]} != expected:
        raise ContractError("n8n runtime evidence must cover exactly the three real filings")
    schema = ACTIVE_PRODUCT_SCHEMA_DIR / "n8n-research-output.schema.json"
    for row in summary["cases"]:
        output = load_json(directory / f"{row['company_id']}-{row['period']}.json")
        validate_instance(output, schemas[schema], schema, schemas)
        result = output["research_result"]
        if (
            not output["run_id"]
            == result["run_id"]
            == output["research_trace"]["run_id"]
            == row["run_id"]
        ):
            raise ContractError("n8n artifact run linkage mismatch")
        for alias, field in {
            "conclusion": "executive_summary",
            "findings": "claims",
            "limitations": "limitations",
            "monitoring": "monitoring_items",
        }.items():
            if output[alias] != result[field]:
                raise ContractError(f"n8n presentation alias changed: {alias}")
        if output["counter_evidence"] != [
            {"claim_id": claim["claim_id"], "search": claim["counter_evidence_search"]}
            for claim in result["claims"]
        ]:
            raise ContractError("n8n counter evidence differs from backend claims")
        for field, count in {
            "financial_facts": "fact_count",
            "calculations": "calculation_count",
            "supporting_evidence": "evidence_count",
        }.items():
            if len(output[field]) != row[count]:
                raise ContractError("n8n summary count mismatch")

    hardening = load_json(
        ROOT / "docs/evidence/v1.5-product-hardening/n8n-form-runtime-summary.json"
    )
    if hardening["workflow_sha256"] != hashlib.sha256(workflow.read_bytes()).hexdigest():
        raise ContractError("Phase 5 n8n form evidence belongs to a different workflow artifact")
    if (
        hardening["status"] != "PASS"
        or hardening["human_user_value_validated"] is not False
        or hardening["native_form_success"] != "PASS"
        or hardening["native_form_failure"] != "PASS"
    ):
        raise ContractError("Phase 5 n8n form evidence is incomplete or claims human validation")
    if {(row["company_id"], row["period"]) for row in hardening["cases"]} != expected:
        raise ContractError("Phase 5 n8n form evidence must retain all three real filing cases")


def validate_product_disclosure_package(
    schemas: dict[Path, dict[str, Any]],
) -> tuple[int, int, int]:
    """Validate the three real slices without requiring ignored raw PDFs."""
    if any(PRODUCT_PACKAGE_DIR.parent.rglob("*.pdf")):
        raise ContractError("V1.5 product package must not contain a raw filing PDF")

    registry = load_json(PRODUCT_REGISTRY_PATH)
    if registry.get("schema_version") != "1.5.0" or registry.get("data_namespace") != "product":
        raise ContractError("V1.5 filing registry must be isolated in the product namespace")
    records = registry.get("records")
    if not isinstance(records, list) or len(records) != 3:
        raise ContractError("Phase 3 product registry must contain exactly three filings")
    expected_sources = {
        "catl-2024h1": "2a690cb2471c1f0d4539d909a9f068c03710a838ddd35313175790169e85eab1",
        "catl-2024fy": "b4f1713d7b821eb076c102711d177fe942ccc2bc8dd171ae5d7a95799a65b0ad",
        "byd-2024h1": "769e9fc195141e7f525d65f0daa308d441c7e39408f0dd584a3722cfc8a306ba",
    }
    if {record["record_id"]: record["expected_sha256"] for record in records} != expected_sources:
        raise ContractError("Phase 3 official document identities changed")
    serialized_registry = json.dumps(records, ensure_ascii=False)
    for forbidden_key in ("fact_specs", "reported_value", "page", "evidence_text"):
        if f'"{forbidden_key}"' in serialized_registry:
            raise ContractError(
                f"V1.5 filing registry contains prohibited prefilled field {forbidden_key}"
            )
    index = load_json(PRODUCT_INDEX_PATH)
    schema_path = (ACTIVE_PRODUCT_SCHEMA_DIR / "product-package-index.schema.json").resolve()
    validate_instance(index, schemas[schema_path], schema_path, schemas)
    if index["package_hash"] != _canonical_hash(index["packages"]):
        raise ContractError("Product index hash differs from package references")
    if {entry["path"] for entry in index["packages"]} != set(expected_sources):
        raise ContractError("Product index does not contain exactly the three filing cases")
    counts = [0, 0, 0]
    for record in records:
        package_dir = PRODUCT_PACKAGE_DIR.parent / record["record_id"]
        count = _validate_product_case(record, package_dir, schemas)
        package = load_json(package_dir / "manifest.json")
        entry = next(item for item in index["packages"] if item["path"] == record["record_id"])
        if any(entry[key] != package[key] for key in ("package_id", "package_hash")):
            raise ContractError("Product index reference differs from child manifest")
        counts = [total + increment for total, increment in zip(counts, count, strict=True)]
        evidence_dir = ROOT / "docs/evidence/v1.5-generalization" / record["record_id"]
        for kind in ("run-manifest", "research-result", "workflow-trace", "evaluation-result"):
            artifact = load_json(evidence_dir / f"{kind}.json")
            artifact_schema = (SCHEMA_DIR / f"{kind}.schema.json").resolve()
            validate_instance(artifact, schemas[artifact_schema], artifact_schema, schemas)
        result = load_json(evidence_dir / "research-result.json")
        if result["source_document_ids"] != [record["document_id"]]:
            raise ContractError("Generalization research evidence crossed filing boundaries")
        if not result["monitoring_items"] or not result["limitations"]:
            raise ContractError("Generalization result lacks monitoring or limitations")
        evaluation = load_json(evidence_dir / "evaluation-result.json")
        if evaluation["failure_events"]:
            raise ContractError("Generalization result failed its deterministic verifier")
        calculations = load_json(evidence_dir / "calculation-records.json")
        for calculation in calculations:
            calculation_schema = (SCHEMA_DIR / "calculation-record.schema.json").resolve()
            validate_instance(calculation, schemas[calculation_schema], calculation_schema, schemas)
    return counts[0], counts[1], counts[2]


def _validate_product_case(
    record: dict[str, Any], package_dir: Path, schemas: dict[Path, dict[str, Any]]
) -> tuple[int, int, int]:
    if urlparse(record.get("source_uri", "")).netloc not in {
        "disc.static.szse.cn",
        "static.cninfo.com.cn",
    }:
        raise ContractError("Product source is not an official disclosure host")
    ingestion = load_json(package_dir / "ingestion-manifest.json")
    ingestion_schema_path = (ACTIVE_PRODUCT_SCHEMA_DIR / "ingestion-manifest.schema.json").resolve()
    validate_instance(
        ingestion,
        schemas[ingestion_schema_path],
        ingestion_schema_path,
        schemas,
    )
    if ingestion["status"] != "ready" or ingestion["data_namespace"] != "product":
        raise ContractError("V1.5 product ingestion manifest must be ready and real-data only")
    if ingestion["abstentions"]:
        raise ContractError("V1.5 ready product package cannot retain an abstention")
    if ingestion["acquisition"]["raw_payload_committed"] is not False:
        raise ContractError("V1.5 product package cannot commit the raw filing")
    if ingestion["parser"]["page_count"] != record["expected_page_count"]:
        raise ContractError("Product page count differs from reviewed identity")
    if ingestion["acquisition"]["content_hash"] != record["expected_sha256"]:
        raise ContractError("Product acquisition hash differs from reviewed identity")
    if (
        ingestion["company"] != record["company"]
        or ingestion["reporting_period"] != record["reporting_period"]
    ):
        raise ContractError("Product extraction company or period differs from registry")
    extraction = ingestion.get("extraction")
    if not isinstance(extraction, dict):
        raise ContractError("V1.5 ready product package lacks deterministic extraction evidence")
    if extraction.get("llm_used") is not False:
        raise ContractError("V1.5 financial fact extraction cannot use an LLM")
    if extraction.get("parser_text_hash") != ingestion["parser"]["text_hash"]:
        raise ContractError("V1.5 extraction and parser text hashes differ")

    source_paths = sorted((package_dir / "source-documents").glob("*.json"))
    fact_paths = sorted((package_dir / "financial-facts").glob("*.json"))
    chunk_paths = sorted((package_dir / "evidence-chunks").glob("*.json"))
    if len(source_paths) != 1 or len(fact_paths) != 6 or len(chunk_paths) < 6:
        raise ContractError("Product case must have 1 source, 6 facts and at least 6 chunks")

    source_schema_path = (SCHEMA_DIR / "source-document.schema.json").resolve()
    fact_schema_path = (SCHEMA_DIR / "financial-fact.schema.json").resolve()
    chunk_schema_path = (SCHEMA_DIR / "evidence-chunk.schema.json").resolve()
    source = load_json(source_paths[0])
    validate_instance(source, schemas[source_schema_path], source_schema_path, schemas)
    if source["content_hash"] != record["expected_sha256"]:
        raise ContractError("V1.5 Source Document hash differs from the registry")

    values: dict[str, str] = {}
    facts_by_metric: dict[str, dict[str, Any]] = {}
    for path in fact_paths:
        fact = load_json(path)
        validate_instance(fact, schemas[fact_schema_path], fact_schema_path, schemas)
        if fact["source"]["document_id"] != source["document_id"]:
            raise ContractError("V1.5 fact points to an unexpected Source Document")
        if fact["source"]["content_hash"] != source["content_hash"]:
            raise ContractError("V1.5 fact source hash differs from the Source Document")
        if not all(
            fact["source_locator"].get(key)
            for key in ("page", "section", "table", "row_label", "column_label")
        ):
            raise ContractError("V1.5 fact has an incomplete source locator")
        values[fact["metric_code"]] = fact["value"]
        facts_by_metric[fact["metric_code"]] = fact
    expected_values = {
        "accounts_receivable": "58099476000.00",
        "inventory": "48050676200.00",
        "revenue": "166766833600.00",
        "operating_cost": "122517848800.00",
        "net_income": "22864987400.00",
        "operating_cash_flow": "44708954600.00",
    }
    if record["record_id"] == "catl-2024h1" and values != expected_values:
        raise ContractError("V1.5 CATL normalized fact values changed")
    expected_metric_set = set(expected_values)
    if set(extraction.get("target_metrics", [])) != expected_metric_set:
        raise ContractError("V1.5 extraction target metrics differ from the frozen six")
    recoveries = extraction.get("recoveries", [])
    if not isinstance(recoveries, list) or len(recoveries) != 6:
        raise ContractError("V1.5 extraction must contain exactly six recoveries")
    recoveries_by_metric = {item["metric_code"]: item for item in recoveries}
    if set(recoveries_by_metric) != expected_metric_set:
        raise ContractError("V1.5 extraction recoveries are not one-per-frozen-metric")
    if len({item["recovery_hash"] for item in recoveries}) != 6:
        raise ContractError("V1.5 extraction recovery hashes must be unique")
    for metric, recovery in recoveries_by_metric.items():
        fact = facts_by_metric[metric]
        if recovery["normalized_value"] != fact["value"]:
            raise ContractError(f"V1.5 {metric} recovery value differs from Financial Fact")
        locator = fact["source_locator"]
        if (
            recovery["page"] != locator["page"]
            or recovery["statement"] != locator["table"]
            or recovery["row_label"] != locator["row_label"]
            or recovery["column_label"] != locator["column_label"]
        ):
            raise ContractError(f"V1.5 {metric} recovery locator differs from Financial Fact")
        _validate_extraction_recovery(recovery, f"product:{metric}")

    counter_sections = 0
    for path in chunk_paths:
        chunk = load_json(path)
        validate_instance(chunk, schemas[chunk_schema_path], chunk_schema_path, schemas)
        if chunk["document_id"] != source["document_id"]:
            raise ContractError("V1.5 evidence points to an unexpected Source Document")
        if "SYNTHETIC PUBLIC EVIDENCE" in chunk["text"]:
            raise ContractError("V1.5 real product evidence cannot be a synthetic fixture")
        if chunk["section"].startswith("Counter evidence:"):
            counter_sections += 1
    if record["record_id"] == "catl-2024h1" and counter_sections != 2:
        raise ContractError("V1.5 product package must preserve two filing-based limitations")

    package = load_json(package_dir / "manifest.json")
    if package.get("data_namespace") != "product" or package.get("status") != "ready":
        raise ContractError("V1.5 product package manifest is not ready product data")
    artifact_paths = sorted((*source_paths, *fact_paths, *chunk_paths))
    artifact_hashes = {
        str(path.relative_to(package_dir)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in artifact_paths
    }
    if package.get("artifact_hashes") != artifact_hashes:
        raise ContractError("V1.5 product package artifact hashes do not match files")
    if package.get("package_hash") != _canonical_hash(artifact_hashes):
        raise ContractError("V1.5 product package hash does not match artifact hashes")
    output_hashes = {item["path"]: item["content_hash"] for item in ingestion["outputs"]}
    if output_hashes != artifact_hashes:
        raise ContractError("V1.5 ingestion output references differ from package artifacts")
    if ingestion["package_hash"] != package["package_hash"]:
        raise ContractError("V1.5 ingestion and product package hashes differ")

    return len(source_paths), len(fact_paths), len(chunk_paths)


def main() -> int:
    try:
        missing_files = [
            str(path.relative_to(ROOT)) for path in REQUIRED_CONTRACTS if not path.is_file()
        ]
        if missing_files:
            raise ContractError(f"missing required contract files: {sorted(missing_files)}")

        screenshot_names = (
            "research-page.png",
            "skill-lab-page.png",
            "research-page-v1.5-start.png",
            "research-page-v1.5-result.png",
            "research-page-v1.5-evidence.png",
            "quality-lab-page-v1.5.png",
            "research-page-v1.5-final-start.png",
            "research-page-v1.5-final-result.png",
            "n8n-form-v1.5.png",
            "n8n-result-v1.5.png",
            "n8n-abstention-v1.5.png",
        )
        for screenshot_name in screenshot_names:
            screenshot = ROOT / "docs" / "assets" / screenshot_name
            if not screenshot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
                raise ContractError(f"demo screenshot is not PNG: {screenshot_name}")
        demo_video = ROOT / "docs" / "assets" / "researchforge-v1.4-demo.mp4"
        video_header = demo_video.read_bytes()[:32]
        if b"ftyp" not in video_header or demo_video.stat().st_size < 1_000_000:
            raise ContractError("demo video is missing a valid MP4 file header or payload")

        validate_schema_catalog(SCHEMA_DIR, REQUIRED_SCHEMAS, "current V1.4")
        validate_schema_catalog(
            ACTIVE_PRODUCT_SCHEMA_DIR,
            ACTIVE_PRODUCT_REQUIRED_SCHEMAS,
            "preserved V1.5 productization",
        )
        validate_schema_catalog(V17_SCHEMA_DIR, V17_REQUIRED_SCHEMAS, "active V1.7 product")
        for version, directory in HISTORICAL_SCHEMA_DIRS.items():
            validate_schema_catalog(
                directory,
                HISTORICAL_REQUIRED_SCHEMAS[version],
                f"historical {version.upper()}",
            )

        schemas: dict[Path, dict[str, Any]] = {}
        schema_paths = sorted(SCHEMA_DIR.glob("*.schema.json"))
        schema_paths.extend(sorted(ACTIVE_PRODUCT_SCHEMA_DIR.glob("*.schema.json")))
        schema_paths.extend(sorted(V17_SCHEMA_DIR.glob("*.schema.json")))
        for version in HISTORICAL_SCHEMA_VERSIONS:
            schema_paths.extend(sorted(HISTORICAL_SCHEMA_DIRS[version].glob("*.schema.json")))
        for path in schema_paths:
            resolved = path.resolve()
            schema = load_json(path)
            if not isinstance(schema, dict):
                raise ContractError(f"{path.relative_to(ROOT)}: schema root must be object")
            validate_schema_shape(path, schema)
            schemas[resolved] = schema

        ids = [schema["$id"] for schema in schemas.values()]
        if len(ids) != len(set(ids)):
            raise ContractError("schema $id values must be unique")

        current_common = schemas[(SCHEMA_DIR / "common.schema.json").resolve()]
        current_schema_const = current_common["$defs"]["schemaVersion"]["const"]
        if current_schema_const != CURRENT_ARTIFACT_VERSION:
            raise ContractError("current common schema version does not match V1.4")
        active_product_common = schemas[
            (ACTIVE_PRODUCT_SCHEMA_DIR / "common.schema.json").resolve()
        ]
        if active_product_common["$defs"]["schemaVersion"]["const"] != (
            ACTIVE_PRODUCT_ARTIFACT_VERSION
        ):
            raise ContractError("active product common schema version does not match V1.5")
        historical_versions = {"v1.3": "1.3.0", "v1.2": "1.2.0"}
        for version, artifact_version in historical_versions.items():
            historical_common = schemas[
                (HISTORICAL_SCHEMA_DIRS[version] / "common.schema.json").resolve()
            ]
            if historical_common["$defs"]["schemaVersion"]["const"] != artifact_version:
                raise ContractError(f"historical {version.upper()} common schema changed")

        v17_result_schema = schemas[(V17_SCHEMA_DIR / "research-result.schema.json").resolve()]
        if v17_result_schema["properties"]["schema_version"].get("const") != V17_ARTIFACT_VERSION:
            raise ContractError("V1.7 general Research Result schema version is not frozen")
        if v17_result_schema["properties"]["task_type"].get("const") != "company_research":
            raise ContractError("V1.7 general Research Result must be company_research")

        reference_count = validate_all_refs(schemas)

        current_examples = validate_example_catalog(
            EXAMPLE_DIR,
            CURRENT_EXAMPLES,
            SCHEMA_DIR,
            schemas,
            "V1.4",
        )
        active_product_examples = validate_example_catalog(
            ACTIVE_PRODUCT_EXAMPLE_DIR,
            ACTIVE_PRODUCT_EXAMPLES,
            ACTIVE_PRODUCT_SCHEMA_DIR,
            schemas,
            "V1.5 productization",
        )
        for version, example_map in HISTORICAL_EXAMPLES.items():
            validate_example_catalog(
                HISTORICAL_EXAMPLE_DIRS[version],
                example_map,
                HISTORICAL_SCHEMA_DIRS[version],
                schemas,
                version.upper(),
            )

        workflow_example = current_examples["workflow-trace.example.json"]
        validate_workflow_trace(workflow_example)

        run_schema_path = (SCHEMA_DIR / "run-manifest.schema.json").resolve()
        research_run_example = current_examples["run-manifest.research.example.json"]

        checkpoint_path = ROOT / "project-status.json"
        checkpoint = load_json(checkpoint_path)
        project_schema_path = (
            ACTIVE_PRODUCT_SCHEMA_DIR / "project-checkpoint.schema.json"
        ).resolve()
        validate_instance(
            checkpoint,
            schemas[project_schema_path],
            project_schema_path,
            schemas,
        )
        checkpoint_path_count = validate_project_checkpoint(checkpoint)

        run_schema = schemas[run_schema_path]
        configuration_schema = run_schema["properties"]["configuration"]
        artifact_schema = run_schema["properties"]["artifacts"]
        if "workflow" not in configuration_schema["required"]:
            raise ContractError("V1.4 Run Manifest must require workflow configuration")
        if "workflow_trace_id" not in artifact_schema["required"]:
            raise ContractError("V1.4 Run Manifest must require workflow_trace_id")

        research_result_schema = schemas[(SCHEMA_DIR / "research-result.schema.json").resolve()]
        result_status_schema = research_result_schema["properties"]["status"]
        if result_status_schema.get("const") != "completed":
            raise ContractError("V1.4 Research Result must represent completed reports only")

        invalid_insufficient_run = json.loads(json.dumps(research_run_example))
        invalid_insufficient_run["lifecycle_state"] = "insufficient_data"
        invalid_insufficient_run["started_at"] = "2026-08-30T16:00:01+08:00"
        invalid_insufficient_run["finished_at"] = "2026-08-30T16:00:02+08:00"
        invalid_insufficient_run["artifacts"]["workflow_trace_id"] = "trace_demo_001"
        invalid_insufficient_run["artifacts"]["result_id"] = "result_forbidden_001"
        invalid_insufficient_run["failure"] = {
            "code": "INSUFFICIENT_DATA",
            "message": "Required authoritative filing evidence is unavailable.",
            "retryable": False,
        }
        try:
            validate_instance(
                invalid_insufficient_run,
                run_schema,
                run_schema_path,
                schemas,
            )
        except ContractError:
            pass
        else:
            raise ContractError("V1.4 insufficient_data run must reject a Research Result artifact")

        validate_v14_semantics(schemas, current_examples)
        validate_v15_product_semantics(schemas, active_product_examples)
        validate_seed_skill(schemas)
        g0_source_count, g0_fact_count, g0_golden_count = validate_g0_fixtures(schemas)
        primary_source_count, primary_fact_count, primary_chunk_count, primary_case_count = (
            validate_primary_benchmark(schemas)
        )
        (
            contingency_source_count,
            contingency_fact_count,
            contingency_chunk_count,
            contingency_case_count,
        ) = validate_contingency_benchmark(schemas)
        product_source_count, product_fact_count, product_chunk_count = (
            validate_product_disclosure_package(schemas)
        )
        validate_historical_scope_hashes()
        validate_n8n_evidence(schemas)

        markdown_link_count = validate_markdown_links()

        print(
            f"PASS: {len(V17_REQUIRED_SCHEMAS)} active V1.7, "
            f"{len(ACTIVE_PRODUCT_REQUIRED_SCHEMAS)} preserved V1.5 productization, "
            f"{len(REQUIRED_SCHEMAS)} preserved V1.4, "
            f"{len(HISTORICAL_REQUIRED_SCHEMAS['v1.3'])} historical V1.3, and "
            f"{len(HISTORICAL_REQUIRED_SCHEMAS['v1.2'])} historical V1.2 schemas parsed"
        )
        print(f"PASS: {reference_count} local schema references resolved")
        print(
            f"PASS: {len(ACTIVE_PRODUCT_EXAMPLES)} V1.5 productization, "
            f"{len(CURRENT_EXAMPLES)} V1.4, "
            f"{len(HISTORICAL_EXAMPLES['v1.3'])} V1.3, and "
            f"{len(HISTORICAL_EXAMPLES['v1.2'])} V1.2 examples validated"
        )
        print("PASS: insufficient_data cannot persist a Research Result artifact")
        print("PASS: model, simulation, budget, retrieval, and split semantics validated")
        print("PASS: immutable fundamental-research Seed Skill manifest and hash validated")
        print(
            "PASS: G0 fixture package validated "
            f"({g0_source_count} sources, {g0_fact_count} facts, "
            f"{g0_golden_count} golden cases)"
        )
        print(
            "PASS: V1.4 primary benchmark package validated "
            f"({primary_source_count} sources, {primary_fact_count} facts, "
            f"{primary_chunk_count} synthetic chunks, {primary_case_count} frozen cases)"
        )
        print(
            "PASS: sealed V1.5 contingency benchmark package validated "
            f"({contingency_source_count} sources, {contingency_fact_count} facts, "
            f"{contingency_chunk_count} synthetic chunks, "
            f"{contingency_case_count} frozen cases)"
        )
        print(
            "PASS: V1.5 three-filing product packages and research evidence validated "
            f"({product_source_count} source, {product_fact_count} facts, "
            f"{product_chunk_count} real evidence chunks)"
        )
        print("PASS: historical V1.3 and V1.2 scope hashes validated")
        print(
            "PASS: project-status.json validated "
            f"({checkpoint_path_count} referenced paths present)"
        )
        print(f"PASS: {markdown_link_count} local Markdown links resolved")
        print(
            f"PASS: {len(screenshot_names)} PNG screenshots and the preserved V1.4 MP4 "
            "demo asset validated"
        )
        print(f"PASS: {len(REQUIRED_CONTRACTS)} required contract files present")
        return 0
    except ContractError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
