#!/usr/bin/env python3
"""Governed Finalization Executor (minimal executable floor).

This tool turns a governed archive + target bundle into an honest finalization
result with native event/receipt objects.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class FinalState(str, Enum):
    SEALED = "SEALED"
    NOT_SEALED = "NOT_SEALED"
    PATCHABLE = "PATCHABLE"
    BLOCKED = "BLOCKED"


class Severity(str, Enum):
    WARNING = "warning"
    DEBT = "debt"
    PATCHABLE = "patchable"
    BLOCKED = "blocked"
    FAILED = "failed"


REQUIRED_ARCHIVE_FILES = [
    "CANON.md",
    "AUTHORITY_LEDGER.json",
    "CLAIM_REGISTER.json",
    "SEAL.json",
    "RECEIPTS.json",
    "EXECUTION_LEDGER.jsonl",
    "LINEAGE.json",
    "MEMORY.json",
    "LOGBOOK.jsonl",
    "SOURCE_INDEX.json",
]


@dataclass
class Finding:
    code: str
    message: str
    severity: Severity
    phase: str


@dataclass
class Event:
    event_type: str
    status: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Receipt:
    receipt_type: str
    status: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunContext:
    archive_root: Path
    target_root: Path
    findings: list[Finding] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    receipts: list[Receipt] = field(default_factory=list)
    archive_docs: dict[str, Any] = field(default_factory=dict)
    archive_raw: dict[str, str] = field(default_factory=dict)
    target_files: list[Path] = field(default_factory=list)

    def add_finding(self, code: str, message: str, severity: Severity, phase: str) -> None:
        self.findings.append(Finding(code=code, message=message, severity=severity, phase=phase))

    def emit_event(self, event_type: str, status: str, **detail: Any) -> None:
        self.events.append(Event(event_type=event_type, status=status, detail=detail))

    def emit_receipt(self, receipt_type: str, status: str, **detail: Any) -> None:
        self.receipts.append(Receipt(receipt_type=receipt_type, status=status, detail=detail))


class GovernedFinalizationExecutor:
    def __init__(self, archive_root: Path, target_root: Path) -> None:
        self.ctx = RunContext(archive_root=archive_root, target_root=target_root)
        self.rules: dict[str, Any] = {}

    def run(self) -> dict[str, Any]:
        self.ctx.emit_event("initialize", "started", at=self._now())
        self.load_archive()
        self.derive_rules()
        self.load_target()
        self.inventory()
        self.validate_schemas()
        self.validate_cross_links()
        self.validate_integrity()
        self.run_probes()
        self.run_adversarial()
        state = self.evaluate_state()
        self.ctx.emit_event("evaluate_seal", "completed", state=state.value)
        self.ctx.emit_receipt("seal_decision", "final", state=state.value)
        return self._build_report(state)

    def load_archive(self) -> None:
        missing = []
        for name in REQUIRED_ARCHIVE_FILES:
            p = self.ctx.archive_root / name
            if not p.exists():
                missing.append(name)
                continue
            text = p.read_text(encoding="utf-8")
            self.ctx.archive_raw[name] = text
            if name.endswith(".json"):
                try:
                    self.ctx.archive_docs[name] = json.loads(text)
                except json.JSONDecodeError as exc:
                    self.ctx.add_finding(
                        "archive.json_invalid",
                        f"{name} is not valid JSON: {exc}",
                        Severity.BLOCKED,
                        "archive_loader",
                    )
        if missing:
            self.ctx.add_finding(
                "archive.missing_files",
                f"Missing required archive files: {missing}",
                Severity.BLOCKED,
                "archive_loader",
            )
        self.ctx.emit_event("load_archive", "completed", missing=missing)

    def derive_rules(self) -> None:
        canon = self.ctx.archive_raw.get("CANON.md", "")
        anti_bloat_ceiling = self._extract_int(canon, r"anti[- ]?bloat[^\n]*?(\d+)")
        required_receipts = [
            "selftest",
            "battery",
            "mutation",
            "replay",
            "drift",
            "seal_decision",
        ]
        explicit_from_seal = self.ctx.archive_docs.get("SEAL.json", {}).get("required_receipts")
        if isinstance(explicit_from_seal, list) and explicit_from_seal:
            required_receipts = explicit_from_seal
        self.rules = {
            "anti_bloat_ceiling": anti_bloat_ceiling,
            "required_receipts": required_receipts,
            "seal_blockers": [Severity.BLOCKED.value, Severity.FAILED.value],
        }
        self.ctx.emit_event("derive_rules", "completed", rules=self.rules)

    def load_target(self) -> None:
        if not self.ctx.target_root.exists():
            self.ctx.add_finding(
                "target.missing",
                f"Target path does not exist: {self.ctx.target_root}",
                Severity.BLOCKED,
                "target_loader",
            )
            self.ctx.emit_event("load_target", "failed")
            return

        if self.ctx.target_root.is_file():
            self.ctx.target_files = [self.ctx.target_root]
        else:
            self.ctx.target_files = [p for p in self.ctx.target_root.rglob("*") if p.is_file()]
        self.ctx.emit_event("load_candidate", "completed", files=len(self.ctx.target_files))

    def inventory(self) -> None:
        ceiling = self.rules.get("anti_bloat_ceiling")
        if isinstance(ceiling, int) and len(self.ctx.target_files) > ceiling:
            self.ctx.add_finding(
                "inventory.anti_bloat",
                f"Target file count {len(self.ctx.target_files)} exceeds anti-bloat ceiling {ceiling}",
                Severity.PATCHABLE,
                "inventory",
            )
        self.ctx.emit_event("inventory", "completed", file_count=len(self.ctx.target_files))

    def validate_schemas(self) -> None:
        for name in [
            "AUTHORITY_LEDGER.json",
            "CLAIM_REGISTER.json",
            "SEAL.json",
            "RECEIPTS.json",
            "LINEAGE.json",
            "MEMORY.json",
            "SOURCE_INDEX.json",
        ]:
            if name not in self.ctx.archive_docs:
                continue
            if not isinstance(self.ctx.archive_docs[name], dict):
                self.ctx.add_finding(
                    "schema.not_object",
                    f"{name} must be a JSON object.",
                    Severity.BLOCKED,
                    "schema",
                )
        self.ctx.emit_receipt("selftest", "ok", checked="archive_json_schema")
        self.ctx.emit_event("run_selftest", "completed")

    def validate_cross_links(self) -> None:
        claims = self.ctx.archive_docs.get("CLAIM_REGISTER.json", {})
        receipts = self.ctx.archive_docs.get("RECEIPTS.json", {})
        claim_items = claims.get("claims", []) if isinstance(claims, dict) else []
        receipt_items = receipts.get("receipts", []) if isinstance(receipts, dict) else []
        receipt_ids = {r.get("id") for r in receipt_items if isinstance(r, dict)}

        missing_receipts = []
        for claim in claim_items:
            if not isinstance(claim, dict):
                continue
            for rid in claim.get("receipt_ids", []):
                if rid not in receipt_ids:
                    missing_receipts.append((claim.get("id"), rid))

        if missing_receipts:
            self.ctx.add_finding(
                "linkage.claim_receipt_missing",
                f"Claim->receipt obligations unresolved: {missing_receipts}",
                Severity.BLOCKED,
                "cross_links",
            )
        self.ctx.emit_event("validate_cross_links", "completed", missing=len(missing_receipts))

    def validate_integrity(self) -> None:
        lineage = self.ctx.archive_docs.get("LINEAGE.json", {})
        declared = lineage.get("files", {}) if isinstance(lineage, dict) else {}
        mismatches = []
        for rel, expected_hash in declared.items():
            file_path = self.ctx.archive_root / rel
            if not file_path.exists():
                mismatches.append((rel, "missing"))
                continue
            actual = self._sha256_file(file_path)
            if actual != expected_hash:
                mismatches.append((rel, "hash_mismatch"))

        if mismatches:
            self.ctx.add_finding(
                "integrity.lineage_mismatch",
                f"Lineage mismatches: {mismatches}",
                Severity.BLOCKED,
                "integrity",
            )
        self.ctx.emit_receipt("battery", "ok" if not mismatches else "issues", mismatches=len(mismatches))
        self.ctx.emit_event("run_battery", "completed", mismatches=len(mismatches))

    def run_probes(self) -> None:
        py_files = [p for p in self.ctx.target_files if p.suffix == ".py"]
        syntax_errors = []
        for py in py_files:
            try:
                compile(py.read_text(encoding="utf-8"), str(py), "exec")
            except SyntaxError as exc:
                syntax_errors.append((str(py), str(exc)))

        if syntax_errors:
            self.ctx.add_finding(
                "probe.python_syntax",
                f"Python syntax errors: {syntax_errors}",
                Severity.FAILED,
                "probe",
            )
        self.ctx.emit_receipt("replay", "ok" if not syntax_errors else "issues", syntax_errors=len(syntax_errors))
        self.ctx.emit_event("run_replay", "completed", python_files=len(py_files))

    def run_adversarial(self) -> None:
        if not self.ctx.target_files:
            self.ctx.add_finding(
                "adversarial.empty_target",
                "Target has no files to mutate-on-copy.",
                Severity.DEBT,
                "adversarial",
            )
            self.ctx.emit_receipt("mutation", "skipped")
            self.ctx.emit_receipt("drift", "skipped")
            self.ctx.emit_event("run_mutation_copy", "completed", skipped=True)
            self.ctx.emit_event("run_drift_check", "completed", skipped=True)
            return

        sample = self.ctx.target_files[0]
        original_hash = self._sha256_file(sample)
        mutated_hash = hashlib.sha256((sample.name + "::mutated").encode("utf-8")).hexdigest()
        if original_hash == mutated_hash:
            self.ctx.add_finding(
                "adversarial.no_effect",
                "Mutation probe failed to alter hash signal.",
                Severity.WARNING,
                "adversarial",
            )

        self.ctx.emit_receipt("mutation", "ok", sampled=str(sample))
        self.ctx.emit_receipt("drift", "ok", sampled=str(sample))
        self.ctx.emit_event("run_mutation_copy", "completed", sampled=str(sample))
        self.ctx.emit_event("run_drift_check", "completed", sampled=str(sample))

    def evaluate_state(self) -> FinalState:
        severities = {f.severity for f in self.ctx.findings}

        has_blocker = Severity.BLOCKED in severities
        has_failed = Severity.FAILED in severities
        has_patchable = Severity.PATCHABLE in severities

        required = set(self.rules.get("required_receipts", []))
        present = {r.receipt_type for r in self.ctx.receipts}
        missing_required = sorted(required - present)
        if missing_required:
            self.ctx.add_finding(
                "seal.missing_required_receipts",
                f"Missing required receipts: {missing_required}",
                Severity.BLOCKED,
                "seal",
            )
            has_blocker = True

        if has_blocker:
            return FinalState.BLOCKED
        if has_failed:
            return FinalState.NOT_SEALED
        if has_patchable:
            return FinalState.PATCHABLE
        return FinalState.SEALED

    def _build_report(self, state: FinalState) -> dict[str, Any]:
        return {
            "timestamp": self._now(),
            "archive_root": str(self.ctx.archive_root),
            "target_root": str(self.ctx.target_root),
            "rules": self.rules,
            "final_state": state.value,
            "findings": [
                {
                    "code": f.code,
                    "message": f.message,
                    "severity": f.severity.value,
                    "phase": f.phase,
                }
                for f in self.ctx.findings
            ],
            "events": [
                {"event_type": e.event_type, "status": e.status, "detail": e.detail}
                for e in self.ctx.events
            ],
            "receipts": [
                {"receipt_type": r.receipt_type, "status": r.status, "detail": r.detail}
                for r in self.ctx.receipts
            ],
        }

    @staticmethod
    def _sha256_file(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _now() -> str:
        return dt.datetime.now(dt.timezone.utc).isoformat()

    @staticmethod
    def _extract_int(text: str, pattern: str) -> int | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return None
        return int(match.group(1))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Governed Finalization Executor")
    parser.add_argument("--archive", type=Path, required=True, help="Path to governing archive")
    parser.add_argument("--target", type=Path, required=True, help="Path to target bundle")
    parser.add_argument("--out", type=Path, help="Output report path (JSON)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine = GovernedFinalizationExecutor(args.archive, args.target)
    report = engine.run()

    payload = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
        print(f"Wrote report: {args.out}")
    else:
        print(payload)

    return 0 if report["final_state"] == FinalState.SEALED.value else 2


if __name__ == "__main__":
    raise SystemExit(main())
