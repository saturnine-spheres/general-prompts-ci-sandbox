#!/usr/bin/env python3
"""Validate an installed project assurance scaffold without external packages."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
from typing import Any

sys.dont_write_bytecode = True  # keep installed .assurance/tools free of __pycache__

from validate_artifacts import content_sha256, normalized_bytes, read_json, schema_accepts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd(), help="repository root")
    parser.add_argument("--report", type=pathlib.Path, help="JSON report path")
    args = parser.parse_args()

    root = args.root.resolve()
    assurance = root / ".assurance"
    schemas = assurance / "schemas"
    report_path = (args.report or assurance / "evidence/installed-assurance-validation.json").resolve()
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    def add(identifier: str, passed: bool, detail: str) -> None:
        checks.append({"id": identifier, "passed": bool(passed), "detail": detail})
        if not passed:
            failures.append(f"{identifier}: {detail}")

    manifest_path = assurance / "assurance-system-manifest.json"
    footprint = "full"
    if manifest_path.is_file():
        try:
            footprint = read_json(manifest_path).get("installation", {}).get("footprint", "full")
        except (OSError, ValueError):
            pass
    # A minimal installation (AGENTS.md plus .assurance/) adds product and architecture documents later.
    required = [
        "AGENTS.md",
        ".assurance/assurance-system-manifest.json", ".assurance/project-assurance-profile.json",
        ".assurance/control-catalog.yaml", ".assurance/change-class-evidence-matrix.json",
        ".assurance/generalized-development-assurance-guidelines.md", ".assurance/tiered-verifier-contract.md",
    ]
    if footprint != "minimal":
        required += [
            "README.md", "docs/START-HERE.md", "docs/product/project-discovery.md",
            "docs/product/product-brief.md", "docs/product/requirements.md",
            "docs/architecture/architecture.md", "docs/roadmap/roadmap.md",
            "docs/quality/test-strategy.md", "docs/status/current-status.md",
        ]
    missing = [name for name in required if not (root / name).is_file()]
    add("installed-required-artifacts", not missing, f"Required {footprint}-footprint artifacts are present." if not missing else ", ".join(missing))

    instances = {
        "profile": (assurance / "project-assurance-profile.json", schemas / "project-assurance-profile.schema.json"),
        "catalog": (assurance / "control-catalog.yaml", schemas / "control-catalog.schema.json"),
        "matrix": (assurance / "change-class-evidence-matrix.json", schemas / "change-class-evidence-matrix.schema.json"),
        "manifest": (assurance / "assurance-system-manifest.json", schemas / "assurance-system-manifest.schema.json"),
    }
    for name, (instance, schema) in instances.items():
        passed, errors = schema_accepts(instance, schema)
        add(f"installed-{name}-schema", passed, f"{instance} conforms." if passed else "; ".join(errors))

    # Files added in package 1.4.0 are checked when present, so earlier installations keep validating.
    optional_instances = {
        "process-contract": (assurance / "process.json", schemas / "process-contract.schema.json"),
        "verifier-config": (assurance / "verifiers.json", schemas / "verifier-config.schema.json"),
    }
    for name, (instance, schema) in optional_instances.items():
        if instance.is_file():
            passed, errors = schema_accepts(instance, schema)
            add(f"installed-{name}-schema", passed, f"{instance} conforms." if passed else "; ".join(errors))
    migration_records = sorted((assurance / "migrations").glob("*.json")) if (assurance / "migrations").is_dir() else []
    bad_records = []
    for record in migration_records:
        passed, errors = schema_accepts(record, schemas / "migration-record.schema.json")
        if not passed:
            bad_records.append(f"{record.name}: {'; '.join(errors[:2])}")
    if migration_records:
        add("installed-migration-records-schema", not bad_records, f"{len(migration_records)} migration record(s) conform." if not bad_records else ", ".join(bad_records))

    agents = root / "AGENTS.md"
    agents_bytes = len(normalized_bytes(agents.read_bytes())) if agents.is_file() else 0
    add("installed-agents-size", 0 < agents_bytes <= 8192, f"{agents_bytes} bytes with LF line endings; maximum 8192.")

    catalog_path = assurance / "control-catalog.yaml"
    if catalog_path.is_file():
        catalog = read_json(catalog_path)
        ids = [item["id"] for item in catalog.get("controls", [])]
        add("installed-control-ids", bool(ids) and len(ids) == len(set(ids)), f"{len(ids)} controls; {len(set(ids))} unique IDs.")
    else:
        add("installed-control-ids", False, "Catalog unavailable.")

    active_drafts = [
        root / "README.md", root / "AGENTS.md", assurance / "project-assurance-profile.json",
        root / "docs/START-HERE.md", root / "docs/product/project-discovery.md",
        root / "docs/product/product-brief.md", root / "docs/product/requirements.md",
        root / "docs/architecture/architecture.md", root / "docs/roadmap/roadmap.md",
        root / "docs/quality/test-strategy.md", root / "docs/status/current-status.md",
    ]
    placeholders = []
    for path in active_drafts:
        if path.is_file() and "REPLACE" in path.read_text(encoding="utf-8-sig"):
            placeholders.append(path.relative_to(root).as_posix())
    add("installed-active-placeholders-resolved", not placeholders, "No REPLACE markers remain in active baseline documents." if not placeholders else ", ".join(placeholders))

    manifest_errors: list[str] = []
    if manifest_path.is_file():
        manifest = read_json(manifest_path)
        seen: set[str] = set()
        for item in manifest.get("managed_artifacts", []):
            relative = item.get("path", "")
            if relative in seen:
                manifest_errors.append(f"duplicate:{relative}")
                continue
            seen.add(relative)
            candidate = (root / pathlib.PurePosixPath(relative)).resolve(strict=False)
            try:
                candidate.relative_to(root)
            except ValueError:
                manifest_errors.append(f"escape:{relative}")
                continue
            if not candidate.is_file():
                manifest_errors.append(f"missing:{relative}")
                continue
            # Line-ending-normalized digest: equal to the raw digest for LF files, stable across CRLF checkouts.
            actual = f"sha256:{content_sha256(candidate)}"
            if actual != item.get("installed_digest"):
                manifest_errors.append(f"current-digest:{relative}")
            upstream_differs = item.get("upstream_digest") != item.get("installed_digest")
            if bool(item.get("local_changes")) != upstream_differs:
                manifest_errors.append(f"local-change-flag:{relative}")
    else:
        manifest_errors.append("manifest unavailable")
    add("installed-manifest-lineage", not manifest_errors, "Managed paths are unique, contained, present, digest-matched, and consistently labelled." if not manifest_errors else ", ".join(manifest_errors))

    report = {
        "schema_version": "1.0.0",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "validator": "tools/validate_installed_assurance.py",
        "root": str(root),
        "status": "pass" if not failures else "fail",
        "checks": checks,
        "failures": failures,
        "limitations": [
            "This validates scaffold structure, selected JSON schemas, placeholders, IDs, and recorded file lineage; it does not approve product decisions or prove evidence truth.",
            "Project-native verify tier implementation and stack-specific checks remain separate work after technology choices are accepted.",
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    print(f"PASS: {len(checks)} installed-assurance checks; report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
