#!/usr/bin/env python3
"""Prepare empty review forms, or reconcile two human H0 annotation documents."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.adjudication import (  # noqa: E402
    DECISION_SCHEMA,
    decision_template,
    prepare_review_document,
    reconcile_annotations,
    reviewer_template,
)


def _write(path: Path, document: object) -> None:
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewer-a", type=Path)
    parser.add_argument("--reviewer-b", type=Path)
    parser.add_argument("--decisions", type=Path)
    parser.add_argument("--empty-templates", action="store_true")
    parser.add_argument("--prepare-review", type=Path, help="Add unsigned provenance, reason and confidence fields to a replay export")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.empty_templates and any((args.reviewer_a, args.reviewer_b, args.decisions, args.prepare_review)):
        parser.error("--empty-templates cannot be combined with other inputs")
    if args.prepare_review and any((args.reviewer_a, args.reviewer_b, args.decisions)):
        parser.error("--prepare-review cannot be combined with reviewer or decision inputs")
    if not args.empty_templates and not args.prepare_review and (not args.reviewer_a or not args.reviewer_b):
        parser.error("Supply both --reviewer-a and --reviewer-b, or --empty-templates")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output must be a new or empty directory, preserving earlier review versions")
    if args.empty_templates:
        output = {
            "reviewer_a_empty.json": reviewer_template(),
            "reviewer_b_empty.json": reviewer_template(),
            "decisions_empty.json": {"schema_version": DECISION_SCHEMA, "source_document_sha256": {}, "decisions": []},
        }
        summary = {"status": "empty_unsigned_templates", "human_reference_count": 0}
    elif args.prepare_review:
        prepared = prepare_review_document(json.loads(args.prepare_review.read_text(encoding="utf-8")))
        output = {"review_to_complete.json": prepared}
        summary = {"status": "provenance_requires_human_completion", "source_annotation_count": len(prepared["annotations"])}
    else:
        def read(path):
            return json.loads(path.read_text(encoding="utf-8"))

        result = reconcile_annotations(read(args.reviewer_a), read(args.reviewer_b), read(args.decisions) if args.decisions else None)
        output = {
            "reconciliation.json": result,
            "decisions_template.json": decision_template(result),
            "adjudicated_reference.json": result["adjudicated_reference"],
        }
        summary = {"status": result["status"], **result["counts"]}
    args.output.mkdir(parents=True, exist_ok=True)
    for name, document in output.items():
        _write(args.output / name, document)
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
