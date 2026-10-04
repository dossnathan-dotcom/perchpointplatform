"""Strict, dependency-free validation for Phase 6 execution evidence."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2
PROVENANCE_FIELDS = (
    "schema_version", "kind", "commit", "tree_hash", "source_clean",
    "command", "timestamp", "exit_code", "raw_artifacts",
)


class EvidenceError(ValueError):
    """Evidence is absent, malformed, or does not prove its claim."""


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"missing evidence: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"evidence root must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_provenance(root: Path) -> dict[str, Any]:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    tree_hash = subprocess.check_output(
        ["git", "rev-parse", f"{commit}^{{tree}}"], cwd=root, text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"], cwd=root, text=True
    )
    source_changes = [
        line for line in status.splitlines()
        if line and not line[3:].replace("\\", "/").startswith("test_reports/phase6/")
    ]
    return {"commit": commit, "tree_hash": tree_hash, "source_clean": not source_changes}


def raw_artifact(root: Path, path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def validate_provenance(
    report: dict[str, Any],
    *,
    kind: str,
    commit: str | None = None,
    require_tests: bool = True,
) -> list[str]:
    errors: list[str] = []
    for field in PROVENANCE_FIELDS:
        if field not in report:
            errors.append(f"missing {field}")
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported schema_version")
    if report.get("kind") != kind:
        errors.append(f"kind must be {kind}")
    if commit is not None and report.get("commit") != commit:
        errors.append("obsolete commit")
    report_commit = report.get("commit")
    if isinstance(report_commit, str) and report_commit:
        try:
            expected_tree = subprocess.check_output(
                ["git", "rev-parse", f"{report_commit}^{{tree}}"],
                text=True,
            ).strip()
            if report.get("tree_hash") != expected_tree:
                errors.append("source tree hash mismatch")
        except subprocess.CalledProcessError:
            errors.append("unknown evidence commit")
    if report.get("source_clean") is not True:
        errors.append("evidence started from a dirty source tree")
    artifacts = report.get("raw_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("missing raw artifacts")
    else:
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                errors.append("invalid raw artifact")
                continue
            path = Path(str(artifact.get("path", "")))
            if not path.is_file():
                errors.append(f"absent raw artifact:{path}")
                continue
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != artifact.get("sha256"):
                errors.append(f"raw artifact digest mismatch:{path}")
            if len(data) != artifact.get("bytes") or not data:
                errors.append(f"raw artifact size mismatch:{path}")
    command = report.get("command")
    if not isinstance(command, str) or not command.strip():
        errors.append("empty command")
    timestamp = report.get("timestamp")
    if not isinstance(timestamp, str):
        errors.append("invalid timestamp")
    else:
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            errors.append("invalid timestamp")
    if type(report.get("exit_code")) is not int:
        errors.append("exit_code must be an integer")
    elif report["exit_code"] != 0:
        errors.append("nonzero exit")
    if require_tests:
        totals = report.get("totals")
        if not isinstance(totals, dict):
            errors.append("missing totals")
        else:
            for field in ("total", "passed", "failed", "skipped"):
                if type(totals.get(field)) is not int or totals[field] < 0:
                    errors.append(f"invalid totals.{field}")
            numeric_totals = all(type(totals.get(field)) is int and totals[field] >= 0 for field in ("total", "passed", "failed", "skipped"))
            if numeric_totals:
                if totals["total"] <= 0:
                    errors.append("zero tests")
                if totals["passed"] + totals["failed"] + totals["skipped"] != totals["total"]:
                    errors.append("inconsistent totals")
                if totals["failed"]:
                    errors.append("failed tests")
                if totals["skipped"]:
                    errors.append("required skips")
    return errors


def validate_executions(report: dict[str, Any], required_steps: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    executions = report.get("executions")
    if not isinstance(executions, list) or not executions:
        return ["missing executions"]
    by_step: dict[str, dict[str, Any]] = {}
    for execution in executions:
        if not isinstance(execution, dict):
            errors.append("execution must be an object")
            continue
        step = execution.get("step")
        if not isinstance(step, str) or not step:
            errors.append("execution missing step")
            continue
        if step in by_step:
            errors.append(f"duplicate execution:{step}")
        by_step[step] = execution
        if execution.get("exit_code") != 0:
            errors.append(f"{step}:nonzero exit")
        if not execution.get("command") or not execution.get("started_at") or not execution.get("finished_at"):
            errors.append(f"{step}:incomplete provenance")
        digest = execution.get("output_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append(f"{step}:missing output digest")
        if int(execution.get("output_bytes", 0)) <= 0:
            errors.append(f"{step}:empty output")
        output_path = Path(str(execution.get("output_path", "")))
        if not output_path.is_file():
            errors.append(f"{step}:missing raw output")
        else:
            output = output_path.read_bytes()
            if hashlib.sha256(output).hexdigest() != digest:
                errors.append(f"{step}:raw output digest mismatch")
            if len(output) != execution.get("output_bytes"):
                errors.append(f"{step}:raw output size mismatch")
    for step in required_steps:
        if step not in by_step:
            errors.append(f"missing execution:{step}")
    extra = set(by_step) - set(required_steps)
    for step in sorted(extra):
        errors.append(f"unknown execution:{step}")
    return errors
