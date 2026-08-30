#!/usr/bin/env python3
"""Validate the ResearchForge contract package without third-party dependencies."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CURRENT_SCHEMA_VERSION = "v1.4"
CURRENT_ARTIFACT_VERSION = "1.4.0"
HISTORICAL_SCHEMA_VERSIONS = ("v1.3", "v1.2")
SCHEMA_DIR = ROOT / "schemas" / CURRENT_SCHEMA_VERSION
HISTORICAL_SCHEMA_DIRS = {
    version: ROOT / "schemas" / version for version in HISTORICAL_SCHEMA_VERSIONS
}
EXAMPLE_DIR = ROOT / "examples" / "contracts" / CURRENT_SCHEMA_VERSION
HISTORICAL_EXAMPLE_DIRS = {
    "v1.3": ROOT / "examples" / "contracts" / "v1.3",
    "v1.2": ROOT / "examples" / "contracts",
}
CONTRACT_PACKAGE_VERSION = "1.4.0"
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
    ROOT / "docs" / "architecture" / "implementation-blueprint.md",
    ROOT / "docs" / "product" / "researchforge-v1.4-scope.md",
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
    ROOT / "docs" / "operations" / "resume-playbook.md",
    ROOT / "docs" / "strategy" / "project-scorecard.md",
    ROOT / "docs" / "strategy" / "risk-register.md",
    ROOT / "docs" / "strategy" / "solo-success-plan.md",
    *{EXAMPLE_DIR / name for name in CURRENT_EXAMPLES},
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
    recognized_versions = {CURRENT_SCHEMA_VERSION, *HISTORICAL_SCHEMA_VERSIONS}
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
        "Scope: V1.4 active baseline",
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
                f"{path.relative_to(ROOT)}: missing required V1.4 text {fragment!r}"
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


def main() -> int:
    try:
        missing_files = [
            str(path.relative_to(ROOT)) for path in REQUIRED_CONTRACTS if not path.is_file()
        ]
        if missing_files:
            raise ContractError(f"missing required contract files: {sorted(missing_files)}")

        validate_schema_catalog(SCHEMA_DIR, REQUIRED_SCHEMAS, "current V1.4")
        for version, directory in HISTORICAL_SCHEMA_DIRS.items():
            validate_schema_catalog(
                directory,
                HISTORICAL_REQUIRED_SCHEMAS[version],
                f"historical {version.upper()}",
            )

        schemas: dict[Path, dict[str, Any]] = {}
        schema_paths = sorted(SCHEMA_DIR.glob("*.schema.json"))
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
        historical_versions = {"v1.3": "1.3.0", "v1.2": "1.2.0"}
        for version, artifact_version in historical_versions.items():
            historical_common = schemas[
                (HISTORICAL_SCHEMA_DIRS[version] / "common.schema.json").resolve()
            ]
            if historical_common["$defs"]["schemaVersion"]["const"] != artifact_version:
                raise ContractError(f"historical {version.upper()} common schema changed")

        reference_count = validate_all_refs(schemas)

        current_examples = validate_example_catalog(
            EXAMPLE_DIR,
            CURRENT_EXAMPLES,
            SCHEMA_DIR,
            schemas,
            "V1.4",
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
        project_schema_path = (SCHEMA_DIR / "project-checkpoint.schema.json").resolve()
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
        validate_historical_scope_hashes()

        markdown_link_count = validate_markdown_links()

        print(
            f"PASS: {len(REQUIRED_SCHEMAS)} current V1.4, "
            f"{len(HISTORICAL_REQUIRED_SCHEMAS['v1.3'])} historical V1.3, and "
            f"{len(HISTORICAL_REQUIRED_SCHEMAS['v1.2'])} historical V1.2 schemas parsed"
        )
        print(f"PASS: {reference_count} local schema references resolved")
        print(
            f"PASS: {len(CURRENT_EXAMPLES)} V1.4, "
            f"{len(HISTORICAL_EXAMPLES['v1.3'])} V1.3, and "
            f"{len(HISTORICAL_EXAMPLES['v1.2'])} V1.2 examples validated"
        )
        print("PASS: insufficient_data cannot persist a Research Result artifact")
        print("PASS: model, simulation, budget, retrieval, and split semantics validated")
        print("PASS: historical V1.3 and V1.2 scope hashes validated")
        print(
            "PASS: project-status.json validated "
            f"({checkpoint_path_count} referenced paths present)"
        )
        print(f"PASS: {markdown_link_count} local Markdown links resolved")
        print(f"PASS: {len(REQUIRED_CONTRACTS)} required contract files present")
        return 0
    except ContractError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
