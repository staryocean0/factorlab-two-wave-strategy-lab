#!/usr/bin/env python3
"""Build the frozen v0.6.48 blinded independent reference-label packet.

No model direction/prediction, harmless-offset information, future bar, return,
PnL or hidden stratum is written into the annotator-facing ZIP.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.data import load_development_bars
from factor_lab.visual_structure.two_wave.reference_label_packet_v0648 import (
    CASES_PER_YEAR_PER_STRATUM,
    LOOKBACK_BARS,
    YEARS,
    public_manifest,
    sampling_commitment,
    select_blinded_cases,
)
from scripts.run_two_wave_independent_temporal_replication_v0647 import build_publications

DATA_PATH = ROOT / "data/development/5m_offset_0.parquet"
MANIFEST_PATH = ROOT / "data/manifest.json"
VIEW = "5m_offset_0"
EXPECTED_SOURCE_SHA256 = "bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48"
PROTOCOL = "docs/research/TWO_WAVE_INDEPENDENT_REFERENCE_LABEL_CONSTRUCTION_V0648_PROTOCOL.md"
LABEL_COLUMNS = [
    "case_id",
    "annotator_id",
    "two_complete_same_scale_waves",
    "parent_state",
    "p0",
    "p1",
    "p2",
    "p3",
    "p4",
    "confidence",
    "notes",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dump_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def git_head() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def annotator_readme() -> str:
    return """# Two-Wave v0.6.48 — Blinded Annotation Instructions

You are labeling chart morphology, not evaluating a trading strategy.

## What you see

Each PNG contains exactly 96 consecutive CSI1000 5-minute OHLC bars and ends at bar position 95. Prices are normalized so the first visible close equals 100. Absolute date/year, sample stratum, model pivots, model labels and future bars are intentionally hidden.

## Primary question

Does the visible history contain **two complete, visibly comparable same-scale waves belonging to one parent structure near the right edge**?

Choose exactly one value in `two_complete_same_scale_waves`:

- `yes` — two completed comparable waves are visually identifiable;
- `no` — that semantic object is not present;
- `uncertain` — genuinely ambiguous from the visible history.

Do not mechanically reproduce a numerical algorithm. Judge the semantic morphology.

## Parent state

If presence is `yes`, label the parent as one of:

- `range`
- `uptrend`
- `downtrend`
- `uncertain`

If presence is `no`, set `parent_state=not_applicable`.

If you can identify the five alternating extrema of the two-wave parent, enter their chart positions in `p0`..`p4` as integers from 0 to 95. These anchor fields are optional; do not invent anchors when uncertain.

Set `confidence` to `high`, `medium`, or `low`.

## Independence rules

- Do not inspect the project repository, model outputs or hidden sample construction while labeling.
- Do not discuss cases with another annotator before both first-pass sheets are submitted and hashed.
- Do not use future bars, returns, P&L, later market history or external strategy labels.
- Do not infer a model answer from the case ID; case IDs are blinded hashes.
- Label every case. Difficult cases should be marked `uncertain`/`low`, not deleted.

Return the completed CSV unchanged except for the annotation columns. Keep every `case_id` exactly as supplied.
"""


def render_case(frame: pd.DataFrame, cutoff: int, case_id: str, output: Path) -> None:
    start = int(cutoff) - LOOKBACK_BARS + 1
    if start < 0:
        raise ValueError("case does not have the frozen lookback")
    window = frame.iloc[start : int(cutoff) + 1].copy()
    if len(window) != LOOKBACK_BARS:
        raise AssertionError("annotation window length drift")
    base = float(window["close"].iloc[0])
    if base <= 0:
        raise ValueError("non-positive normalization base")
    for col in ("open", "high", "low", "close"):
        window[col] = window[col].astype(float) / base * 100.0

    fig, ax = plt.subplots(figsize=(11.0, 5.0))
    x = list(range(LOOKBACK_BARS))
    # Neutral single-color OHLC glyphs prevent red/green direction priming.
    for i, row in enumerate(window.itertuples(index=False)):
        o = float(row.open)
        h = float(row.high)
        low = float(row.low)
        c = float(row.close)
        ax.vlines(i, low, h, linewidth=0.7)
        ax.hlines(o, i - 0.28, i, linewidth=0.9)
        ax.hlines(c, i, i + 0.28, linewidth=0.9)
    ax.plot(x, window["close"].to_numpy(float), linewidth=0.8, alpha=0.65)
    ax.axvline(LOOKBACK_BARS - 1, linestyle="--", linewidth=0.7, alpha=0.6)
    ax.set_title(case_id)
    ax.set_xlabel("bar position (case cutoff = 95)")
    ax.set_ylabel("normalized index level (first close = 100)")
    ax.set_xlim(-1, LOOKBACK_BARS)
    ax.grid(True, linewidth=0.35, alpha=0.35)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        output,
        dpi=130,
        bbox_inches="tight",
        metadata={"Software": "FactorLab Two-Wave v0.6.48 blinded packet builder"},
    )
    plt.close(fig)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def deterministic_zip(zip_path: Path, public_root: Path, relative_paths: list[str]) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in sorted(relative_paths):
            src = public_root / rel
            info = zipfile.ZipInfo(rel, date_time=(2026, 9, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, src.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="experiments/two_wave_independent_reference_label_v0648",
        help="repository-side packet metadata/output directory",
    )
    parser.add_argument(
        "--packet-dir",
        default=None,
        help="optional annotator-facing output directory; defaults to <output>/public_packet",
    )
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    public_root = Path(args.packet_dir) if args.packet_dir else output / "public_packet"
    if not public_root.is_absolute():
        public_root = ROOT / public_root
    output.mkdir(parents=True, exist_ok=True)
    public_root.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(MANIFEST_PATH.read_text())
    entry = next(x for x in manifest["products"] if x["path"] == "data/development/5m_offset_0.parquet")
    source_sha = sha256_file(DATA_PATH)
    if source_sha != EXPECTED_SOURCE_SHA256 or source_sha != entry["sha256"]:
        raise RuntimeError("frozen main-view source SHA256 mismatch")

    bars, source_audit = load_development_bars(DATA_PATH, MANIFEST_PATH)
    frame = pd.read_parquet(DATA_PATH).copy()
    if len(frame) != len(bars) or len(frame) != int(entry["row_count"]):
        raise RuntimeError("source row-count mismatch")

    publication_rows, _, generation_summary = build_publications(VIEW, bars)
    qualified_confirmations = {
        int(row["publishing_confirmation_bar"])
        for row in publication_rows
        if bool(row["candidate_qualified"])
    }
    cases = select_blinded_cases(frame, qualified_confirmations)

    readme_path = public_root / "ANNOTATOR_README.md"
    readme_path.write_text(annotator_readme())

    public_rows = public_manifest(cases)
    write_csv(
        public_root / "PUBLIC_CASE_MANIFEST.csv",
        public_rows,
        ["case_id", "chart_file"],
    )
    empty_rows = []
    for case in cases:
        row = {name: "" for name in LABEL_COLUMNS}
        row["case_id"] = case.case_id
        empty_rows.append(row)
    write_csv(public_root / "EMPTY_LABEL_SHEET.csv", empty_rows, LABEL_COLUMNS)

    for case in cases:
        render_case(frame, case.cutoff_bar, case.case_id, public_root / case.chart_file)

    visible_rel = [
        "ANNOTATOR_README.md",
        "EMPTY_LABEL_SHEET.csv",
        "PUBLIC_CASE_MANIFEST.csv",
        *[case.chart_file for case in cases],
    ]
    zip_path = output / "two_wave_v0648_blinded_annotation_packet.zip"
    deterministic_zip(zip_path, public_root, visible_rel)

    public_hashes = {rel: sha256_file(public_root / rel) for rel in sorted(visible_rel)}
    commitment = sampling_commitment(cases)
    counts_by_year = {
        str(year): {
            "candidate": sum(c.year == year and c.stratum == "candidate" for c in cases),
            "control": sum(c.year == year and c.stratum == "control" for c in cases),
        }
        for year in YEARS
    }
    packet_manifest = {
        "schema": "two_wave_independent_reference_label_packet@0.6.48",
        "protocol": PROTOCOL,
        "code_commit": git_head(),
        "source": {
            "path": str(entry["path"]),
            "sha256": source_sha,
            "rows": int(entry["row_count"]),
            "minimum_trading_day": entry["minimum_trading_day"],
            "maximum_trading_day": entry["maximum_trading_day"],
            "data_role": entry["data_role"],
            "manifest_verified": bool(source_audit["manifest_verified"]),
        },
        "sample": {
            "total_cases": len(cases),
            "lookback_bars": LOOKBACK_BARS,
            "cases_per_year_per_hidden_stratum": CASES_PER_YEAR_PER_STRATUM,
            "counts_by_year": counts_by_year,
            "hidden_strata_not_in_annotator_zip": True,
            "sampling_commitment_sha256": commitment,
        },
        "qualification_generation_control": {
            "view": VIEW,
            "candidate_qualified_publications": int(generation_summary["candidate_qualified"]),
            "future_outcome_used": False,
            "trade_authority": False,
        },
        "annotator_visible_files": {
            "count": len(visible_rel),
            "sha256": public_hashes,
        },
        "zip": {
            "path": zip_path.name,
            "sha256": sha256_file(zip_path),
            "bytes": zip_path.stat().st_size,
        },
        "independent_labels_present": False,
        "model_scoring_started": False,
        "morphology_acceptance": False,
        "trade_authority": False,
        "production_authority": False,
    }
    dump_json(output / "PACKET_MANIFEST.json", packet_manifest)
    dump_json(
        output / "SAMPLING_COMMITMENT.json",
        {
            "schema": "two_wave_reference_sampling_commitment@0.6.48",
            "commitment_algorithm": "sha256(canonical_json(hidden_deterministic_case_mapping))",
            "sha256": commitment,
            "hidden_mapping_written_to_public_packet": False,
            "reproducible_from_frozen_source_and_generator": True,
        },
    )
    dump_json(
        output / "SCORING_BLOCKED.json",
        {
            "schema": "two_wave_reference_scoring_block@0.6.48",
            "independent_labels_present": False,
            "model_scoring_allowed": False,
            "reason": "two independent blinded first-pass label sheets and adjudicated final reference labels do not yet exist",
            "next_action": "obtain_two_independent_blinded_annotations_then_freeze_their_sha256_hashes",
            "morphology_acceptance": False,
            "trade_authority": False,
            "production_authority": False,
        },
    )

    print(json.dumps({
        "cases": len(cases),
        "counts_by_year": counts_by_year,
        "sampling_commitment": commitment,
        "packet_zip_sha256": packet_manifest["zip"]["sha256"],
        "candidate_qualified_publications": generation_summary["candidate_qualified"],
        "model_scoring_started": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
