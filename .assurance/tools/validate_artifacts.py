#!/usr/bin/env python3
"""Dependency-free validator for the assurance artifact distribution.

Implements the JSON Schema Draft-07 keyword subset used by this distribution,
then applies the same cross-field semantic checks as validate-artifacts.ps1.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


class SchemaFailure(ValueError):
    pass


def read_json(path: pathlib.Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def resolve_ref(root_schema: dict[str, Any], reference: str) -> Any:
    if not reference.startswith("#/"):
        raise SchemaFailure(f"unsupported non-local $ref: {reference}")
    current: Any = root_schema
    for encoded in reference[2:].split("/"):
        key = encoded.replace("~1", "/").replace("~0", "~")
        current = current[key]
    return current


def matches_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    raise SchemaFailure(f"unsupported schema type: {expected}")


def validate_datetime(value: str) -> bool:
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = dt.datetime.fromisoformat(normalized)
        return parsed.tzinfo is not None
    except ValueError:
        return False


def validate_instance(
    value: Any,
    schema: Any,
    root_schema: dict[str, Any],
    location: str = "$",
) -> list[str]:
    errors: list[str] = []
    if schema is True:
        return errors
    if schema is False:
        return [f"{location}: false schema rejects value"]
    if not isinstance(schema, dict):
        return [f"{location}: schema is not an object or boolean"]

    if "$ref" in schema:
        try:
            referenced = resolve_ref(root_schema, schema["$ref"])
        except (KeyError, SchemaFailure) as exc:
            return [f"{location}: {exc}"]
        return validate_instance(value, referenced, root_schema, location)

    if "const" in schema and value != schema["const"]:
        errors.append(f"{location}: expected const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{location}: value is not in enum")

    expected_type = schema.get("type")
    if expected_type is not None:
        allowed_types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(matches_type(value, item) for item in allowed_types):
            errors.append(f"{location}: expected type {allowed_types}, got {type(value).__name__}")
            return errors

    if isinstance(value, dict):
        required = schema.get("required", [])
        for name in required:
            if name not in value:
                errors.append(f"{location}: missing required property {name!r}")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for name, child in value.items():
            child_location = f"{location}.{name}"
            if name in properties:
                errors.extend(validate_instance(child, properties[name], root_schema, child_location))
            elif additional is False:
                errors.append(f"{child_location}: additional property is forbidden")
            elif isinstance(additional, dict):
                errors.extend(validate_instance(child, additional, root_schema, child_location))
        if "minProperties" in schema and len(value) < schema["minProperties"]:
            errors.append(f"{location}: fewer than minProperties")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{location}: fewer than minItems")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{location}: more than maxItems")
        if schema.get("uniqueItems"):
            encoded = [canonical(item) for item in value]
            if len(encoded) != len(set(encoded)):
                errors.append(f"{location}: items are not unique")
        if "items" in schema:
            for index, child in enumerate(value):
                errors.extend(validate_instance(child, schema["items"], root_schema, f"{location}[{index}]"))

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{location}: shorter than minLength")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{location}: longer than maxLength")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{location}: does not match pattern {schema['pattern']!r}")
        if schema.get("format") == "date-time" and not validate_datetime(value):
            errors.append(f"{location}: invalid RFC3339 date-time")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{location}: below minimum")

    return errors


def schema_accepts(instance_path: pathlib.Path, schema_path: pathlib.Path) -> tuple[bool, list[str]]:
    try:
        instance = read_json(instance_path)
        schema = read_json(schema_path)
        errors = validate_instance(instance, schema, schema)
        return not errors, errors
    except (OSError, json.JSONDecodeError, SchemaFailure) as exc:
        return False, [str(exc)]


TIER_RANK = {"routine": 0, "notable": 1, "significant": 2}


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def same_value(left: Any, right: Any) -> bool:
    if is_number(left) and is_number(right):
        return float(left) == float(right)
    return type(left) is type(right) and left == right


def review_semantic(value: dict[str, Any]) -> bool:
    reviewer = value["reviewer"]
    implementer = value["implementer"]
    if reviewer["independent"]:
        if reviewer["identity"] == implementer["identity"]:
            return False
        if reviewer["context_id"] == implementer["context_id"]:
            return False
        if re.search(r"renamed.*self|same agent|same context", reviewer["independence_basis"], re.I):
            return False
    if value["decision"] == "approve" and reviewer["independent"] and value["signature"]["state"] != "verified":
        return False
    criteria = value.get("acceptance_criteria", [])
    criterion_ids = [item["id"] for item in criteria]
    if len(criterion_ids) != len(set(criterion_ids)):
        return False
    if any(item["verdict"] == "met" and not item["evidence"] for item in criteria):
        return False
    if value["decision"] == "approve" and any(item["verdict"] == "not_met" for item in criteria):
        return False
    return True


def verification_semantic(value: dict[str, Any]) -> bool:
    if value["status"] == "pass":
        if any(check["blocking"] and check["status"] != "pass" for check in value["checks"]):
            return False
        if any(item["required"] for item in value["unrun_checks"]):
            return False
    for check in value["checks"]:
        if "vulnerability_data" in check and check["tool"]["version"] == "unknown":
            return False
        if check.get("findings") and check["status"] == "pass":
            return False
    for sentinel in value.get("sentinels", []):
        if sentinel["outcome"] == "not_measured":
            if value["status"] == "pass":
                return False
            continue
        expected, observed = sentinel["expected"], sentinel["observed"]
        if observed is None:
            return False
        if sentinel["comparison"] == "at_most":
            if not (is_number(expected) and is_number(observed)):
                return False
            within = observed <= expected
        else:
            within = same_value(observed, expected)
        if (sentinel["outcome"] == "pass") != within:
            return False
        if value["status"] == "pass" and sentinel["outcome"] != "pass":
            return False
    return True


def run_manifest_semantic(value: dict[str, Any]) -> bool:
    if TIER_RANK[value["approved_tier"]] < TIER_RANK[value["computed_tier"]]:
        return False
    if value["status"] == "succeeded":
        if value["completed_at"] is None:
            return False
        if any(stage["outcome"] not in {"pass", "not_required"} for stage in value["stages"]):
            return False
        if any(approval["decision"] == "reject" for approval in value["approvals"]):
            return False
        if value["approved_tier"] == "significant" and not any(
            approval["decision"] == "approve" and approval["tier"] == "significant" for approval in value["approvals"]
        ):
            return False
    return True


def process_contract_semantic(value: dict[str, Any]) -> bool:
    stages = {stage["id"]: stage for stage in value["stages"]}
    if len(stages) != len(value["stages"]):
        return False
    if value["rework_limit"] > 2:
        return False
    significant = value["approvals"]["significant"]
    if not significant["run_approval_required"] or significant["minimum_approvals"] < 1:
        return False
    for tier, rule in value["approvals"].items():
        if rule["run_approval_required"]:
            if rule["minimum_approvals"] < 1 or rule["before_stage"] not in stages:
                return False
            if tier not in stages[rule["before_stage"]]["applies_to_tiers"]:
                return False
    return all(stage["fresh_context"] for stage in value["stages"] if "review_record" in stage["produces"])


def profile_semantic(value: dict[str, Any]) -> bool:
    involvement = value.get("human_involvement")
    if involvement is None:
        return True
    timers = involvement["timers"]
    if not timers["reminder_hours"] < timers["escalation_hours"] < timers["expiry_hours"]:
        return False
    rules = involvement["tier_rules"]
    if rules["routine_max_changed_lines"] > rules["notable_max_changed_lines"]:
        return False
    if set(rules["routine_path_allowlist"]) & set(rules["protected_paths"]):
        return False
    roles = involvement["roles"]
    return bool(roles["significant"]["stakeholders"]) and bool(roles["notable"]["reviewers"])


def waiver_semantic(value: dict[str, Any], controls: dict[str, dict[str, Any]]) -> bool:
    if value["owner"]["identity"] == value["approver"]["identity"]:
        return False
    issued = dt.datetime.fromisoformat(value["issued_at"].replace("Z", "+00:00"))
    expires = dt.datetime.fromisoformat(value["expires_at"].replace("Z", "+00:00"))
    if expires <= issued:
        return False
    if value["status"] == "active" and value["signature"]["state"] != "verified":
        return False
    return all(control_id in controls and bool(controls[control_id]["exception_eligible"])
               for control_id in value["control_ids"])


def effect_semantic(value: dict[str, Any]) -> bool:
    if value["delegation"]["may_expand_authority"]:
        return False
    if value["status"] == "complete":
        if value["cleanup"]["status"] in {"failed", "partial", "planned"}:
            return False
        for effect in value["external_effects"]:
            if effect["requested"] and not effect["authorized"]:
                return False
            if effect["requested"] and effect["status"] not in {"confirmed", "reverted", "not_executed"}:
                return False
    return True


def verifier_config_semantic(value: dict[str, Any]) -> bool:
    for tier in value["tiers"].values():
        identifiers = [check["id"] for check in tier["checks"]]
        if len(identifiers) != len(set(identifiers)):
            return False
    return True


def migration_record_semantic(value: dict[str, Any]) -> bool:
    if (value["kind"] == "rollback") != (value["rolls_back"] is not None):
        return False
    applied = value["status"] == "applied"
    if applied and value["kind"] == "update" and value["snapshot_dir"] is None:
        return False
    for action in value["actions"]:
        kind = action["action"]
        if applied and kind == "CONFLICT":
            return False
        if action["ownership"] == "project-owned" and kind not in {"KEEP", "SKIP", "SUGGEST", "ADD", "REMOVE"}:
            return False
        if kind == "REMOVE" and value["kind"] != "rollback":
            return False
        if action["ownership"] == "derived" and kind not in {"ADD", "REPLACE", "RESTORE", "REMOVE", "SKIP"}:
            return False
        if kind == "ADD" and action["before_digest"] is not None:
            return False
        if applied and kind in {"ADD", "REPLACE", "MERGE", "RESTORE"} and action["after_digest"] is None:
            return False
        if kind in {"REPLACE", "MERGE", "RESTORE", "REMOVE"} and action["before_digest"] is None:
            return False
    return True


def gate_result_semantic(value: dict[str, Any]) -> bool:
    if TIER_RANK[value["effective_tier"]] != max(TIER_RANK[value["computed_tier"]], TIER_RANK[value["approved_tier"]]):
        return False
    new = [item for item in value["findings"] if item["status"] == "new"]
    if value["status"] == "pass" and new:
        return False
    if value["status"] in {"fail", "report_only"} and not new:
        return False
    if any(item["status"] == "known" and not item["ratchetable"] for item in value["findings"]):
        return False
    return value["status"] != "report_only" or value["mode"] in {"report", "ratchet"}


def gate_baseline_semantic(value: dict[str, Any]) -> bool:
    fingerprints = [item["fingerprint"] for item in value["findings"]]
    return len(fingerprints) == len(set(fingerprints))


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_bytes(data: bytes) -> bytes:
    """Text with CRLF line endings converted to LF; binary content (containing NUL) is unchanged."""
    return data if b"\0" in data else data.replace(b"\r\n", b"\n")


def content_sha256(path: pathlib.Path) -> str:
    """Digest that ignores CRLF/LF checkout conversion, so lineage survives Git line-ending settings."""
    return hashlib.sha256(normalized_bytes(path.read_bytes())).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent.parent)
    parser.add_argument("--report", type=pathlib.Path)
    args = parser.parse_args()

    root = args.root.resolve()
    report_path = (args.report or root / "validation-report.json").resolve()
    schema_dir = root / "schemas"
    example_dir = root / "examples"
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    def add_check(identifier: str, passed: bool, detail: str) -> None:
        checks.append({"id": identifier, "passed": bool(passed), "detail": detail})
        if not passed:
            failures.append(f"{identifier}: {detail}")

    schemas = {
        "profile": schema_dir / "project-assurance-profile.schema.json",
        "catalog": schema_dir / "control-catalog.schema.json",
        "waiver": schema_dir / "waiver.schema.json",
        "effect": schema_dir / "agent-effect-manifest.schema.json",
        "verification": schema_dir / "verification-result.schema.json",
        "matrix": schema_dir / "change-class-evidence-matrix.schema.json",
        "review": schema_dir / "review-record.schema.json",
        "manifest": schema_dir / "assurance-system-manifest.schema.json",
        "run-manifest": schema_dir / "run-manifest.schema.json",
        "process-contract": schema_dir / "process-contract.schema.json",
        "verifier-config": schema_dir / "verifier-config.schema.json",
        "migration-record": schema_dir / "migration-record.schema.json",
        "gate-result": schema_dir / "gate-result.schema.json",
        "gate-baseline": schema_dir / "gate-baseline.schema.json",
    }

    for name, path in schemas.items():
        try:
            value = read_json(path)
            passed = isinstance(value, dict) and value.get("$schema") == "http://json-schema.org/draft-07/schema#"
        except (OSError, json.JSONDecodeError):
            passed = False
        add_check(f"schema-syntax-{name}", passed, str(path))

    profile_template = root / "project-assurance-profile.template.json"
    passed, _ = schema_accepts(profile_template, schemas["profile"])
    add_check("profile-template-schema", passed, "Template conforms to project profile schema.")

    process_template = root / "process-contract.template.json"
    passed, _ = schema_accepts(process_template, schemas["process-contract"])
    passed = passed and process_contract_semantic(read_json(process_template))
    add_check("process-contract-template-valid", passed, "Default process contract conforms to its schema and semantic rules.")

    manifest_template = root / "assurance-system-manifest.template.json"
    passed, _ = schema_accepts(manifest_template, schemas["manifest"])
    add_check("manifest-template-schema", passed, "Installed-system manifest template conforms to its schema.")

    catalog_path = root / "control-catalog.template.yaml"
    passed, _ = schema_accepts(catalog_path, schemas["catalog"])
    add_check("catalog-json-compatible-yaml-schema", passed, "Catalog is JSON-compatible YAML 1.2 and conforms to schema.")

    matrix_path = root / "change-class-evidence-matrix.json"
    passed, _ = schema_accepts(matrix_path, schemas["matrix"])
    add_check("change-matrix-schema", passed, "Change-class matrix conforms to schema.")

    catalog = read_json(catalog_path)
    control_ids = [control["id"] for control in catalog["controls"]]
    add_check("control-ids-unique", len(control_ids) == len(set(control_ids)), f"{len(control_ids)} controls; {len(set(control_ids))} unique IDs.")

    vague = re.compile(r"\bwhen feasible\b|\bas applicable\b|\bwhen practical\b|\bproportional to risk\b", re.I)
    vague_controls = [control["id"] for control in catalog["controls"] if vague.search(control["action"])]
    add_check("control-actions-no-vague-escape-hatches", not vague_controls, "No prohibited vague phrase in control actions." if not vague_controls else f"Found in: {', '.join(vague_controls)}")

    bad_blocking = [control["id"] for control in catalog["controls"] if control["blocking"] and control["strength"] not in {"MUST", "MUST NOT"}]
    add_check("blocking-controls-normative", not bad_blocking, "All blocking controls use MUST or MUST NOT." if not bad_blocking else f"Invalid: {', '.join(bad_blocking)}")

    controls = {control["id"]: control for control in catalog["controls"]}
    required_coverage = {
        "GOV-001", "GOV-002", "GOV-004", "GOV-005", "GOV-006", "GOV-007", "GOV-008", "GOV-009", "GOV-010",
        "DES-001", "DES-002", "DES-003",
        "ENG-003", "ENG-004", "ENG-006", "ENG-007", "ENG-008", "ENG-009", "ENG-010", "ENG-011",
        "VER-001", "VER-003", "VER-004", "SEC-002", "SEC-003", "SEC-004", "SEC-006", "SEC-007",
        "DAT-001", "DAT-002", "DAT-003", "DAT-004", "AGT-001", "AGT-002", "AGT-003",
        "AGT-004", "AGT-005", "AGT-006", "AGT-007", "AGT-008", "AGT-009", "AGT-010",
        "AGT-011", "AGT-012", "OPS-001", "OPS-002", "OPS-003", "OPS-004", "OPS-005", "OPS-006",
        "REL-001", "REL-002", "REL-003",
    }
    missing_coverage = sorted(required_coverage - controls.keys())
    add_check("required-policy-coverage-controls-present", not missing_coverage, "All required engineering and corporate-agent policy areas have stable controls." if not missing_coverage else ", ".join(missing_coverage))

    profile_examples = [
        example_dir / "project-profile-web-service.valid.json",
        example_dir / "project-profile-corporate-agent.valid.json",
    ]
    for path in profile_examples:
        passed, _ = schema_accepts(path, schemas["profile"])
        stem = path.stem
        add_check(f"profile-example-{stem}", passed, str(path))
        description = read_json(path)["project"]["description"]
        add_check(f"profile-example-nonnormative-{stem}", "non-normative" in description.lower(), "Example description declares non-normative status.")

    bad_profile_semantics = [path.name for path in [profile_template, *profile_examples] if not profile_semantic(read_json(path))]
    add_check("profile-delivery-blocks-semantic", not bad_profile_semantics, "Template and example human_involvement blocks satisfy timer, threshold, path, and role rules." if not bad_profile_semantics else ", ".join(bad_profile_semantics))

    manifest_valid = example_dir / "assurance-system-manifest.valid.json"
    manifest_invalid = example_dir / "assurance-system-manifest.invalid.json"
    passed, _ = schema_accepts(manifest_valid, schemas["manifest"])
    add_check("manifest-valid-accepted", passed, "Positive installed-system manifest fixture passes schema validation.")
    passed, _ = schema_accepts(manifest_invalid, schemas["manifest"])
    add_check("manifest-invalid-rejected", not passed, "Negative installed-system manifest fixture is rejected.")

    matrix = read_json(matrix_path)
    classes = [item["class"] for item in matrix["classes"]]
    add_check("change-classes-unique-and-complete", len(classes) == 12 and len(set(classes)) == 12, "All twelve required change classes occur exactly once.")
    trigger_ids = [trigger["id"] for item in matrix["classes"] for trigger in item["escalation_triggers"]]
    add_check("matrix-trigger-ids-unique", len(trigger_ids) == len(set(trigger_ids)), f"{len(trigger_ids)} escalation triggers are unique.")

    fixture_sets = [
        ("review-record", schemas["review"], lambda value: review_semantic(value)),
        ("verification-result", schemas["verification"], lambda value: verification_semantic(value)),
        ("waiver", schemas["waiver"], lambda value: waiver_semantic(value, controls)),
        ("agent-effect-manifest", schemas["effect"], lambda value: effect_semantic(value)),
        ("run-manifest", schemas["run-manifest"], lambda value: run_manifest_semantic(value)),
        ("process-contract", schemas["process-contract"], lambda value: process_contract_semantic(value)),
        ("project-profile", schemas["profile"], lambda value: profile_semantic(value)),
        ("verifier-config", schemas["verifier-config"], lambda value: verifier_config_semantic(value)),
        ("migration-record", schemas["migration-record"], lambda value: migration_record_semantic(value)),
        ("assurance-system-manifest", schemas["manifest"], lambda value: True),
        ("gate-result", schemas["gate-result"], lambda value: gate_result_semantic(value)),
        ("gate-baseline", schemas["gate-baseline"], lambda value: gate_baseline_semantic(value)),
    ]
    explicitly_checked = {"assurance-system-manifest.valid.json", "assurance-system-manifest.invalid.json"}
    for name, schema_path, semantic in fixture_sets:
        # <name>.valid.json / <name>.invalid.json keep their original check IDs; <name>.valid-<case>.json adds <name>-valid-<case>-accepted.
        for kind, expected in (("valid", True), ("invalid", False)):
            paths = sorted((path for path in example_dir.glob(f"{name}.{kind}*.json") if path.name not in explicitly_checked), key=lambda item: item.name)
            if kind == "invalid":
                add_check(f"{name}-negative-fixtures-present", bool(paths), f"{len(paths)} negative fixture(s).")
            for path in paths:
                case = path.name[len(f"{name}.{kind}"):-len(".json")]
                check_id = f"{name}-{kind}{case}-{'accepted' if expected else 'rejected'}"
                schema_ok, _ = schema_accepts(path, schema_path)
                semantic_ok = schema_ok and semantic(read_json(path))
                if expected:
                    add_check(check_id, schema_ok and semantic_ok, f"{path.name}: positive fixture passes schema and semantic validation.")
                else:
                    add_check(check_id, not (schema_ok and semantic_ok), f"{path.name}: schema={schema_ok} semantic={semantic_ok}; combined validation rejects it.")

    families = sorted({control_id.split("-", 1)[0] for control_id in control_ids})
    control_pattern = re.compile(r"\b(?:" + "|".join(re.escape(item) for item in families) + r")-[0-9]{3}\b")
    unknown_references: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".json", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8-sig")
        for match in control_pattern.findall(text):
            if match not in controls:
                unknown_references.append(f"{path.relative_to(root)}:{match}")
    add_check("example-control-references-known", not unknown_references, "All referenced control IDs exist." if not unknown_references else ", ".join(unknown_references))

    template_profile = read_json(profile_template)
    ineligible_marked = [control_id for control_id in template_profile["exceptions"]["prohibited_control_ids"] if control_id in controls and controls[control_id]["exception_eligible"]]
    add_check("template-prohibited-controls-not-eligible", not ineligible_marked, "Profile-prohibited controls are catalog-ineligible." if not ineligible_marked else f"Mismatch: {', '.join(ineligible_marked)}")

    profile_exception_errors: list[str] = []
    for path in [profile_template, *profile_examples]:
        candidate = read_json(path)
        for control_id in candidate["exceptions"]["prohibited_control_ids"]:
            if control_id not in controls:
                profile_exception_errors.append(f"{path.name}:{control_id} missing")
            elif controls[control_id]["exception_eligible"]:
                profile_exception_errors.append(f"{path.name}:{control_id} catalog-eligible")
    add_check("profile-prohibited-controls-consistent", not profile_exception_errors, "All template/example prohibited controls exist and are catalog-ineligible." if not profile_exception_errors else ", ".join(profile_exception_errors))

    agents_path = root / "AGENTS.template.md"
    agents_bytes = len(normalized_bytes(agents_path.read_bytes()))
    add_check("agents-template-size-4-to-8-kib", 4096 <= agents_bytes <= 8192, f"{agents_bytes} bytes with LF line endings (required range 4096..8192; detailed policy remains outside the runner entry instructions).")

    markdown_link = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    missing_links: list[str] = []
    relocatable_templates = {"project-start-here.template.md", "project-readme.template.md"}
    for path in root.rglob("*.md"):
        if path.name in relocatable_templates:
            continue
        text = path.read_text(encoding="utf-8-sig")
        for target in markdown_link.findall(text):
            if re.match(r"^(https?://|mailto:|#)", target):
                continue
            local = target.split("#", 1)[0]
            if not local:
                continue
            from urllib.parse import unquote
            resolved = (path.parent / unquote(local)).resolve()
            if not resolved.exists():
                missing_links.append(f"{path.name} -> {target}")
    add_check("relative-markdown-links-resolve", not missing_links, "All relative Markdown links resolve." if not missing_links else "; ".join(missing_links))

    architecture_path = root / "architecture-assurance.template.md"
    architecture_text = architecture_path.read_text(encoding="utf-8-sig") if architecture_path.exists() else ""
    architecture_markers = [
        "## Required views", "### System context", "### Container/component and dependency view",
        "### Deployment and environment view", "### Data-flow and trust-boundary view",
        "## Critical behavioral flows", "## Threat and abuse register",
        "## Diagram-to-reality and contract traceability", "```mermaid",
    ]
    missing_architecture_markers = [marker for marker in architecture_markers if marker not in architecture_text]
    add_check(
        "architecture-template-required-sections",
        not missing_architecture_markers,
        "Architecture template contains structural views, conditional behavioral flows, threat register, traceability, and diagram-as-code examples."
        if not missing_architecture_markers else ", ".join(missing_architecture_markers),
    )

    onboarding_markers = {
        "START-HERE.md": ["## Five required inputs", "## Facts the agent may derive", "## Result"],
        "bootstrap-prompt.md": ["Lead a short discovery/bootstrap interview", "Stop before coding and report"],
        "profile-selection-guide.md": ["## Selection algorithm", "## Lightweight", "## General", "## Corporate/high-risk", "## Burden rule"],
        "installation-and-update-guide.md": ["## Canonical greenfield structure", "## Existing repository adoption", "## Ownership and safe update", "## Optional safe scaffolder"],
    }
    missing_onboarding: list[str] = []
    for name, markers in onboarding_markers.items():
        path = root / name
        text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
        missing_onboarding.extend(f"{name}:{marker}" for marker in markers if marker not in text)
    add_check("onboarding-workflow-required-sections", not missing_onboarding, "Onboarding defines inputs, inference boundaries, preset selection, greenfield/existing installation, and safe updates." if not missing_onboarding else ", ".join(missing_onboarding))

    lifecycle_markers = {
        "project-discovery.template.md": ["## Minimum discovery", "## Assurance selection worksheet", "## Open decisions and stop conditions"],
        "product-brief.template.md": ["## Problem and users", "## Product outcome", "## Scope"],
        "requirements.template.md": ["## Functional requirements", "## Quality requirements and budgets", "## Traceability"],
        "roadmap.template.md": ["## Phase plan", "## Decision gates"],
        "test-strategy.template.md": ["## Verification tiers", "## Requirement and risk coverage", "## Unrun checks and limitations"],
        "adr.template.md": ["## Context", "## Options considered", "## Decision", "## Consequences and controls"],
        "project-status.template.md": ["## Current outcome", "## Verification state", "## Next approved action"],
    }
    missing_lifecycle: list[str] = []
    for name, markers in lifecycle_markers.items():
        path = root / name
        text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
        missing_lifecycle.extend(f"{name}:{marker}" for marker in markers if marker not in text)
    add_check("precode-lifecycle-templates-required-sections", not missing_lifecycle, "Discovery, product, requirements, roadmap, test, ADR, and status templates contain required decision/evidence sections." if not missing_lifecycle else ", ".join(missing_lifecycle))

    work_item_path = root / "work-item.template.md"
    work_item_text = work_item_path.read_text(encoding="utf-8-sig") if work_item_path.exists() else ""
    work_item_markers = ["## Acceptance criteria", "`AC-1`", "`met`, `not_met`, or `not_verifiable`", "## Value check", "## Kill or rethink criteria", "## Rigor budget", "`light | standard | full`"]
    missing_work_item = [marker for marker in work_item_markers if marker not in work_item_text]
    add_check("work-item-template-delivery-sections", not missing_work_item, "Work-item template contains acceptance criteria, value check, kill or rethink criteria, and rigor budget." if not missing_work_item else ", ".join(missing_work_item))

    guardrail_markers = ["two-strike rule", "rigor budget", "re-entry trigger"]
    missing_guardrails: list[str] = []
    for name in ("AGENTS.template.md", "generalized-development-assurance-guidelines.md"):
        path = root / name
        text = path.read_text(encoding="utf-8-sig").lower() if path.exists() else ""
        missing_guardrails.extend(f"{name}:{marker}" for marker in guardrail_markers if marker not in text)
    add_check("process-guardrails-present", not missing_guardrails, "AGENTS template and guidelines state the two-strike rule, rigor budget stop, and re-entry triggers." if not missing_guardrails else ", ".join(missing_guardrails))

    scaffold_path = root / "tools/scaffold_project.py"
    scaffold_text = scaffold_path.read_text(encoding="utf-8-sig") if scaffold_path.exists() else ""
    scaffold_markers = ["if args.apply and args.mode == \"existing\"", "destination already exists", "PLAN ONLY", "is_reparse_or_symlink", "commonpath"]
    missing_scaffold = [marker for marker in scaffold_markers if marker not in scaffold_text]
    add_check("scaffolder-safety-markers", not missing_scaffold, "Scaffolder is plan-first and contains existing-mode, overwrite, path-containment, and reparse/symlink refusals." if not missing_scaffold else ", ".join(missing_scaffold))

    update_markers = ["changed since the plan was reviewed", "uncommitted change overlaps planned write", "downgrade refused",
                      "project file is never overwritten", "schema migration needed", "changed after the migration", "--apply is refused without --plan"]
    missing_update = [marker for marker in update_markers if marker not in scaffold_text]
    add_check("scaffolder-update-safety-markers", not missing_update, "Scaffolder refuses stale plans, dirty overlaps, downgrades, schema migrations, unsafe rollbacks, and never writes project-owned files." if not missing_update else ", ".join(missing_update))

    wrapper_problems: list[str] = []
    for name, markers in {"adapters/github/assurance-gate.yml": ["assurance_gate.py classify", "assurance_gate.py \"${args[@]}\"", "fetch-depth: 0"],
                          "adapters/gitlab/assurance-gate.gitlab-ci.yml": ["assurance_gate.py classify", "assurance_gate.py \"$@\"", "GIT_DEPTH: \"0\""]}.items():
        path = root / name
        text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
        wrapper_problems += [f"{name}:{marker}" for marker in markers if marker not in text]
        for line in text.splitlines():
            used = re.search(r"uses:\s*([^\s#]+)", line)
            if used and not re.search(r"@[0-9a-f]{40}$", used.group(1)):
                wrapper_problems.append(f"{name}: action not pinned to a full commit SHA: {used.group(1)}")
    add_check("ci-gate-wrappers", not wrapper_problems, "GitHub and GitLab wrappers call the forge-neutral gate with full history and pin every action to a commit SHA." if not wrapper_problems else "; ".join(wrapper_problems))

    claude_problems: list[str] = []
    adapter = root / "adapters/claude-code"
    try:
        settings = read_json(adapter / "settings.json")
        handlers = [handler for groups in settings["hooks"].values() for group in groups for handler in group["hooks"]]
        if set(settings["hooks"]) != {"PostToolUse", "PreToolUse", "Stop"}:
            claude_problems.append("settings.json must configure PostToolUse, PreToolUse, and Stop hooks")
        claude_problems += [f"hook does not call assurance-hook.sh: {handler.get('command')}" for handler in handlers
                            if handler.get("type") != "command" or "${CLAUDE_PROJECT_DIR}/.claude/hooks/assurance-hook.sh" not in handler.get("command", "")]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        claude_problems.append(f"settings.json: {exc}")

    def front(path: pathlib.Path) -> str:
        text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
        match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
        return match.group(1) if match else ""

    skill = front(adapter / "skills/deliver/SKILL.md")
    claude_problems += [f"deliver skill frontmatter lacks {marker}" for marker in ("name: deliver", "description:", "disable-model-invocation: true") if marker not in skill]
    for name in ("assurance-specifier", "assurance-builder", "assurance-reviewer"):
        head = front(adapter / f"agents/{name}.md")
        if f"name: {name}" not in head or "description:" not in head:
            claude_problems.append(f"agents/{name}.md needs name: {name} and a description")
    reviewer = front(adapter / "agents/assurance-reviewer.md")
    tools_line = re.search(r"^tools:(.*)$", reviewer, re.M)
    if not tools_line or re.search(r"\b(Edit|MultiEdit|NotebookEdit)\b", tools_line.group(1)) or "reviewer-write" not in reviewer:
        claude_problems.append("reviewer must list tools without Edit and scope its writes with the reviewer-write hook")
    claude_text = (adapter / "CLAUDE.md").read_text(encoding="utf-8-sig") if (adapter / "CLAUDE.md").exists() else ""
    claude_problems += [f"CLAUDE.md lacks {marker}" for marker in ("@AGENTS.md", "@.assurance/agent-pack.md") if marker not in claude_text]
    pack_text = (root / "tools/agent_pack.py").read_text(encoding="utf-8-sig") if (root / "tools/agent_pack.py").exists() else ""
    if "LIMIT = 6144" not in pack_text:
        claude_problems.append("agent_pack.py must enforce the 6 KiB pack limit")
    add_check("claude-code-adapter", not claude_problems, "Claude Code adapter: hooks call the entrypoint, the deliver skill is user-invoked, the reviewer cannot edit code, CLAUDE.md imports AGENTS.md and the pack, and the pack is size-limited." if not claude_problems else "; ".join(claude_problems))

    version_path = root / "VERSION"
    package_version = version_path.read_text(encoding="utf-8").strip() if version_path.exists() else ""
    readme_text = (root / "README.md").read_text(encoding="utf-8-sig")
    manifest_version = read_json(manifest_template)["system"]["version"]
    version_ok = bool(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", package_version)) and f"Distribution version: `{package_version}`" in readme_text and manifest_version == package_version
    add_check("distribution-version-consistent", version_ok, f"VERSION={package_version!r}, manifest template={manifest_version!r}, README must state the same distribution version.")

    installed_validator_path = root / "tools/validate_installed_assurance.py"
    installed_validator_text = installed_validator_path.read_text(encoding="utf-8-sig") if installed_validator_path.exists() else ""
    installed_validator_markers = ["installed-required-artifacts", "installed-active-placeholders-resolved", "installed-manifest-lineage", "installed-control-ids"]
    missing_installed_validator = [marker for marker in installed_validator_markers if marker not in installed_validator_text]
    add_check("installed-validator-scope-markers", not missing_installed_validator, "Installed validator covers structure, active placeholders, catalog IDs, and provenance lineage." if not missing_installed_validator else ", ".join(missing_installed_validator))

    required_files = [
        "README.md", "START-HERE.md", "bootstrap-prompt.md", "profile-selection-guide.md", "installation-and-update-guide.md",
        "AGENTS.template.md", "generalized-development-assurance-guidelines.md", "project-discovery.template.md",
        "product-brief.template.md", "requirements.template.md", "roadmap.template.md", "test-strategy.template.md", "adr.template.md",
        "project-status.template.md", "project-start-here.template.md", "assurance-directory-readme.template.md",
        "project-readme.template.md",
        "project-assurance-profile.template.json", "assurance-system-manifest.template.json", "control-catalog.template.yaml", "work-item.template.md", "architecture-assurance.template.md",
        "change-class-evidence-matrix.json", "tiered-verifier-contract.md", "adoption-guide.md",
        "glossary.md", "compliance-reference-map.md", "tools/validate-artifacts.ps1",
        "tools/validate-artifacts.sh", "tools/validate_artifacts.py", "tools/scaffold_project.py",
        "tools/validate-installed-assurance.ps1", "tools/validate-installed-assurance.sh", "tools/validate_installed_assurance.py",
        "schemas/assurance-system-manifest.schema.json", "examples/assurance-system-manifest.valid.json", "examples/assurance-system-manifest.invalid.json",
        "process-contract.template.json", "schemas/process-contract.schema.json", "schemas/run-manifest.schema.json",
        "VERSION", "schemas/verifier-config.schema.json", "schemas/migration-record.schema.json", "tools/run_verifier.py",
        "tools/verify-entrypoint.sh", "tools/verify-entrypoint.ps1", "tools/test_scaffold_project.py",
        "tools/assurance_gate.py", "tools/test_assurance_gate.py", "schemas/gate-result.schema.json", "schemas/gate-baseline.schema.json",
        "adapters/github/assurance-gate.yml", "adapters/gitlab/assurance-gate.gitlab-ci.yml", "adapters/gitlab/gitlab_mr.py",
        "tools/delivery_run.py", "tools/agent_pack.py", "tools/test_claude_adapter.py",
        "adapters/claude-code/CLAUDE.md", "adapters/claude-code/settings.json", "adapters/claude-code/hooks/assurance-hook.sh",
        "adapters/claude-code/hooks/assurance_hooks.py", "adapters/claude-code/skills/deliver/SKILL.md",
        "adapters/claude-code/agents/assurance-specifier.md", "adapters/claude-code/agents/assurance-builder.md", "adapters/claude-code/agents/assurance-reviewer.md",
    ]
    missing_required = [name for name in required_files if not (root / name).exists()]
    add_check("required-artifacts-present", not missing_required, "All required top-level artifacts are present." if not missing_required else ", ".join(missing_required))

    files = []
    excluded_reports = {report_path, (root / "validation-report.json").resolve()}
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.as_posix()):
        if path.resolve() in excluded_reports:
            continue
        files.append({"path": path.relative_to(root).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256(path)})

    report = {
        "schema_version": "1.0.0",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "validator": "tools/validate-artifacts.sh -> tools/validate_artifacts.py",
        "python": sys.version.split()[0],
        "root": str(root),
        "status": "pass" if not failures else "fail",
        "checks": checks,
        "failures": failures,
        "limitations": [
            "The dependency-free Python validator implements only the Draft-07 keyword subset used by this distribution and does not fetch an online meta-schema.",
            "External HTTP links are recorded but not fetched by this offline validator.",
            "Relative-link checking excludes project-start-here.template.md and project-readme.template.md because their links resolve only after repository relocation.",
            "The distribution check confirms architecture-template sections and diagram-as-code examples but does not parse or render Mermaid; each adopter must pin and run its declared renderer.",
            "Semantic checks cover declared cross-field invariants but do not prove evidence truth, identity ownership, signature cryptography, or compliance.",
        ],
        "files": files,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    print(f"PASS: {len(checks)} checks; report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
