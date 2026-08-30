#!/usr/bin/env python3
"""Validate the ResearchForge contract package without third-party dependencies."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
CURRENT_SCHEMA_VERSION = "v1.3"
CURRENT_ARTIFACT_VERSION = "1.3.0"
LEGACY_SCHEMA_VERSION = "v1.2"
SCHEMA_DIR = ROOT / "schemas" / CURRENT_SCHEMA_VERSION
LEGACY_SCHEMA_DIR = ROOT / "schemas" / LEGACY_SCHEMA_VERSION
EXAMPLE_DIR = ROOT / "examples" / "contracts" / CURRENT_SCHEMA_VERSION
LEGACY_EXAMPLE_DIR = ROOT / "examples" / "contracts"
CONTRACT_PACKAGE_VERSION = "1.3.0"
LEGACY_SCOPE_SHA256 = "513f4a9ae8eabab7a77cb34dedabf6b064a0f9a5710386856f93a7219250816e"

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
}

LEGACY_REQUIRED_SCHEMAS = REQUIRED_SCHEMAS - {"workflow-trace.schema.json"}

REQUIRED_CONTRACTS = {
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "CHANGELOG.md",
    ROOT / "DECISIONS.md",
    ROOT / "PORTFOLIO.md",
    ROOT / "PROJECT_STATUS.md",
    ROOT / "project-status.json",
    ROOT / "docs" / "architecture" / "implementation-blueprint.md",
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
    EXAMPLE_DIR / "benchmark-case.example.json",
    EXAMPLE_DIR / "run-manifest.research.example.json",
    EXAMPLE_DIR / "run-manifest.patch-generation.example.json",
    EXAMPLE_DIR / "workflow-trace.example.json",
    LEGACY_EXAMPLE_DIR / "benchmark-case.example.json",
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


def iter_schema_nodes(node: dict[str, Any], location: str = "$"):
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
    if version_directory not in {CURRENT_SCHEMA_VERSION, LEGACY_SCHEMA_VERSION}:
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


def resolve_ref(ref: str, current_path: Path, schemas: dict[Path, dict[str, Any]]) -> tuple[Any, Path]:
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
    target = json_pointer(schemas[target_path], fragment if separator else "", f"{current_path.name}:{ref}")
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
            raise ContractError(f"{location}: expected type {expected_types}, got {type(instance).__name__}")

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
                validate_instance(item, schema["items"], schema_path, schemas, f"{location}/{index}")

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
                raise ContractError(f"{location}: {keyword} requires {expected_matches} match, got {matches}")

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
        raise ContractError("project-status.json: completed current gate missing from completed_gates")
    if gate_status != "completed" and current_gate in completed_gates:
        raise ContractError("project-status.json: active current gate cannot also be completed")
    if checkpoint["current_milestone"]["status"] != gate_status:
        raise ContractError("project-status.json: milestone status must match gate_status")

    path_count = 0
    referenced_paths = (
        checkpoint["resumption"]["read_first"]
        + checkpoint["last_session"]["files_changed"]
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
        "Scope: V1.3 active baseline",
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


def validate_legacy_scope_hash() -> None:
    path = ROOT / "docs" / "product" / "researchforge-v1.2-scope-freeze.md"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != LEGACY_SCOPE_SHA256:
        raise ContractError("historical V1.2 scope hash changed")


def main() -> int:
    try:
        missing_files = [str(path.relative_to(ROOT)) for path in REQUIRED_CONTRACTS if not path.is_file()]
        if missing_files:
            raise ContractError(f"missing required contract files: {sorted(missing_files)}")

        actual_schema_names = {path.name for path in SCHEMA_DIR.glob("*.schema.json")}
        missing_schemas = REQUIRED_SCHEMAS - actual_schema_names
        unexpected_schemas = actual_schema_names - REQUIRED_SCHEMAS
        if missing_schemas or unexpected_schemas:
            raise ContractError(
                f"schema catalog mismatch; missing={sorted(missing_schemas)}, "
                f"unexpected={sorted(unexpected_schemas)}"
            )

        legacy_schema_names = {
            path.name for path in LEGACY_SCHEMA_DIR.glob("*.schema.json")
        }
        legacy_missing = LEGACY_REQUIRED_SCHEMAS - legacy_schema_names
        legacy_unexpected = legacy_schema_names - LEGACY_REQUIRED_SCHEMAS
        if legacy_missing or legacy_unexpected:
            raise ContractError(
                f"legacy schema catalog mismatch; missing={sorted(legacy_missing)}, "
                f"unexpected={sorted(legacy_unexpected)}"
            )

        schemas: dict[Path, dict[str, Any]] = {}
        schema_paths = sorted(SCHEMA_DIR.glob("*.schema.json")) + sorted(
            LEGACY_SCHEMA_DIR.glob("*.schema.json")
        )
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
            raise ContractError("current common schema version does not match V1.3")
        legacy_common = schemas[(LEGACY_SCHEMA_DIR / "common.schema.json").resolve()]
        if legacy_common["$defs"]["schemaVersion"]["const"] != "1.2.0":
            raise ContractError("historical common schema version changed")

        reference_count = validate_all_refs(schemas)

        example_path = EXAMPLE_DIR / "benchmark-case.example.json"
        example = load_json(example_path)
        benchmark_path = (SCHEMA_DIR / "benchmark-case.schema.json").resolve()
        validate_instance(example, schemas[benchmark_path], benchmark_path, schemas)

        legacy_example_path = LEGACY_EXAMPLE_DIR / "benchmark-case.example.json"
        legacy_example = load_json(legacy_example_path)
        legacy_benchmark_path = (
            LEGACY_SCHEMA_DIR / "benchmark-case.schema.json"
        ).resolve()
        validate_instance(
            legacy_example,
            schemas[legacy_benchmark_path],
            legacy_benchmark_path,
            schemas,
        )

        workflow_example_path = EXAMPLE_DIR / "workflow-trace.example.json"
        workflow_example = load_json(workflow_example_path)
        workflow_schema_path = (SCHEMA_DIR / "workflow-trace.schema.json").resolve()
        validate_instance(
            workflow_example,
            schemas[workflow_schema_path],
            workflow_schema_path,
            schemas,
        )
        validate_workflow_trace(workflow_example)

        run_schema_path = (SCHEMA_DIR / "run-manifest.schema.json").resolve()
        research_run_example: dict[str, Any] | None = None
        for run_example_name in (
            "run-manifest.research.example.json",
            "run-manifest.patch-generation.example.json",
        ):
            run_example = load_json(EXAMPLE_DIR / run_example_name)
            validate_instance(
                run_example,
                schemas[run_schema_path],
                run_schema_path,
                schemas,
            )
            if run_example_name == "run-manifest.research.example.json":
                research_run_example = run_example

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
            raise ContractError("V1.3 Run Manifest must require workflow configuration")
        if "workflow_trace_id" not in artifact_schema["required"]:
            raise ContractError("V1.3 Run Manifest must require workflow_trace_id")

        research_result_schema = schemas[
            (SCHEMA_DIR / "research-result.schema.json").resolve()
        ]
        result_status_schema = research_result_schema["properties"]["status"]
        if result_status_schema.get("const") != "completed":
            raise ContractError(
                "V1.3 Research Result must represent completed reports only"
            )

        if research_run_example is None:
            raise ContractError("missing V1.3 Research Run example")
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
            raise ContractError(
                "V1.3 insufficient_data run must reject a Research Result artifact"
            )

        validate_legacy_scope_hash()

        markdown_link_count = validate_markdown_links()

        print(
            f"PASS: {len(REQUIRED_SCHEMAS)} current V1.3 and "
            f"{len(LEGACY_REQUIRED_SCHEMAS)} historical V1.2 schemas parsed"
        )
        print(f"PASS: {reference_count} local schema references resolved")
        print("PASS: V1.3 Benchmark, Workflow Trace, and two Run Manifest examples validated")
        print("PASS: insufficient_data cannot persist a Research Result artifact")
        print("PASS: historical V1.2 Benchmark Case and scope hash validated")
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
