#!/usr/bin/env python3
"""Formal v0.6.47 post-2020 temporal morphology replication.

The protocol is frozen in
TWO_WAVE_INDEPENDENT_TEMPORAL_MORPHOLOGY_REPLICATION_V0647_PROTOCOL.md.
No future outcome, PnL, threshold search or cross-offset runtime feature enters
this runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.d1_huber_margin_rescue_v0625 import (
    MIN_CONSENSUS_MARGIN,
    d1_primary_margin_rescue,
)
from factor_lab.visual_structure.two_wave.extremum_ridge_v052 import build_ridge_run
from factor_lab.visual_structure.two_wave.morphology_identity_v060 import strict_anchor_edge
from factor_lab.visual_structure.two_wave.ordinal0_predecessor_support_v064 import (
    project_birth_with_predecessor,
)
from factor_lab.visual_structure.two_wave.path_gate_demotion_v0618 import (
    requalify_v066_control,
)
from factor_lab.visual_structure.two_wave.published_identity_qualification_v066 import (
    qualify_published_raw_identity,
)
from factor_lab.visual_structure.two_wave.same_scale_v043 import MaturityConfig
from factor_lab.visual_structure.two_wave.scale_invariant_predecessor_publication_v065 import (
    publish_first_valid_candidate,
)
from factor_lab.visual_structure.two_wave.unmatched_identity_decomposition_v061 import (
    build_edge_graph,
    canonicalize_tuple_births,
)
from factor_lab.visual_structure.two_wave.validation_resample_v0647 import (
    VIEWS,
    exact_ohlc_timestamp_equivalence,
    resample_five_minute_offset,
)
from scripts.run_two_wave_d1_huber_erosion_consensus_v0623 import (
    fkey,
    metrics,
    reconstruct_pair,
)

YEARS = (2024, 2025, 2026)
MAIN_VIEW = "5m_offset_0"
OTHER_VIEWS = VIEWS[1:]
SAFETY_REASONS = {
    "long_cycle",
    "long_pair",
    "too_many_observed_days",
    "wall_span_too_long",
}
EXPECTED_INPUTS = {
    "2024_1m.parquet": "52e1d078fefbb1232b07a8b64682f41654ee171d850c5fe5c928350aba9d6b25",
    "2024_5m_offset_0.parquet": "f9c536d99daa6aaf02d00efd7010316b528e54b5866dc8cf44d002d87f9c3667",
    "2025_1m.parquet": "aebbf7c7bedb78863455192d6efed7536f785c6558fcecd14b475e276e95e1e6",
    "2025_5m_offset_0.parquet": "5fbecf49d76cd2560e7db5af280b60c012a440a6e69ba6b8306acbbbd4e49333",
    "2026_1m.parquet": "60b2054d2055bef8010a9948a0589bc1c4b0bb18dd6f373a9366f97e689fdf87",
}
EXPECTED_1M_ROWS = {2024: 58080, 2025: 58320, 2026: 36960}
EXPECTED_NATIVE_5M_ROWS = {2024: 11616, 2025: 11664}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dump_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _json_safe(value):
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def normalize_external_frame(path: Path, *, require_one_minute_metadata: bool) -> pd.DataFrame:
    """Apply the source manifest's Shanghai-wall-clock interpretation exactly."""
    frame = pd.read_parquet(path).copy()
    required = {"timestamp", "trading_day", "symbol", "open", "high", "low", "close"}
    if require_one_minute_metadata:
        required |= {"causal_flat_fill", "source_minute_count", "high_frequency_analysis_eligible"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"{path.name}: missing required external columns {missing}")
    if frame.empty:
        raise ValueError(f"{path.name}: empty external frame")
    if set(frame["symbol"].astype(str).unique()) != {"000852.SH"}:
        raise ValueError(f"{path.name}: symbol drift")

    # Source archive contract: a trailing Z wraps Shanghai wall-clock text.
    # Use first 19 characters, localize Shanghai, then convert to true UTC.
    wall = frame["timestamp"].astype(str).str[:19]
    naive = pd.to_datetime(wall, errors="raise", format="mixed")
    if getattr(naive.dt, "tz", None) is not None:
        naive = naive.dt.tz_localize(None)
    frame["timestamp"] = naive.dt.tz_localize("Asia/Shanghai").dt.tz_convert("UTC")

    if frame["timestamp"].isna().any() or frame["timestamp"].duplicated().any():
        raise ValueError(f"{path.name}: invalid/duplicate normalized timestamps")
    if not frame["timestamp"].is_monotonic_increasing:
        raise ValueError(f"{path.name}: source order is not strictly increasing")
    local_day = frame["timestamp"].dt.tz_convert("Asia/Shanghai").dt.strftime("%Y-%m-%d")
    trading_day = pd.to_datetime(frame["trading_day"], errors="raise").dt.strftime("%Y-%m-%d")
    if not (local_day.to_numpy() == trading_day.to_numpy()).all():
        raise ValueError(f"{path.name}: trading_day disagrees with normalized Shanghai date")

    prices = frame[["open", "high", "low", "close"]].astype(float)
    if prices.isna().any().any() or (prices <= 0).any().any():
        raise ValueError(f"{path.name}: non-positive/non-finite OHLC")
    if ((prices["low"] > prices[["open", "close"]].min(axis=1)) |
        (prices["high"] < prices[["open", "close"]].max(axis=1)) |
        (prices["low"] > prices["high"])).any():
        raise ValueError(f"{path.name}: invalid OHLC ordering")
    return frame


def bars_from_frame(frame: pd.DataFrame) -> list[dict]:
    """Expose only observed causal bar information to the frozen morphology chain."""
    out = []
    for row in frame.to_dict("records"):
        stamp = pd.Timestamp(row["timestamp"]).isoformat()
        out.append({
            "timestamp": stamp,
            "trading_day": str(row["trading_day"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            # available_at is not a morphology input. Use bar-end causal knowledge
            # rather than importing another project's delayed archival timestamp.
            "available_at": stamp,
            "volume": None if pd.isna(row.get("volume")) else float(row.get("volume")),
        })
    return out


def build_publications(view: str, bars: list[dict]) -> tuple[list[dict], list[dict], dict]:
    """Run the frozen v0.6.18 publication/qualification chain without dev-count asserts."""
    cfg = MaturityConfig(timeframe=view)
    ridge = build_ridge_run(bars, cfg=cfg)
    if ridge.lineage_anomalies:
        raise AssertionError(f"v0.5.2 lineage anomalies on {view}: {len(ridge.lineage_anomalies)}")

    filtered_rows = canonicalize_tuple_births(ridge.tuple_births, bars)
    groups: dict[tuple[str, tuple[int, ...]], list[dict]] = defaultdict(list)
    for birth in ridge.tuple_births:
        phase = str(birth.nodes[0].node.kind)
        filtered = tuple(int(x) for x in birth.occurrence_indices)
        candidate = project_birth_with_predecessor(
            birth,
            ridge.ridge_nodes_by_level[int(birth.level)],
            bars,
        )
        candidate = dict(candidate)
        candidate.update({
            "event_id": str(birth.event_id),
            "birth_level": int(birth.level),
            "birth_confirmation_bar": int(birth.confirmation_index),
        })
        groups[(phase, filtered)].append(candidate)
    if len(groups) != len(filtered_rows):
        raise AssertionError("publication grouping drifted from canonical tuple-birth universe")

    rows = []
    no_valid = 0
    suppressed_rewrites = 0
    safety_candidates = 0
    for (phase, filtered), members in sorted(groups.items(), key=lambda x: (x[0][1], x[0][0])):
        publication = publish_first_valid_candidate(phase, filtered, members)
        suppressed_rewrites += int(publication["suppressed_would_be_rewrite_count"])
        event = publication["publication_event"]
        if event is None:
            no_valid += 1
            continue
        raw = tuple(int(x) for x in event["published_raw_occurrence_bars"])
        confirmation = int(event["publishing_birth_confirmation_bar"])
        control = qualify_published_raw_identity(phase, raw, confirmation, bars, cfg=cfg)
        candidate = requalify_v066_control(control)
        old_hard = [str(x) for x in control["v054_hard_rejection_reasons"]]
        new_hard = [str(x) for x in candidate["v0618_hard_rejection_reasons"]]
        expected_new = [x for x in old_hard if x not in {"inefficient_leg", "jump_dominated_leg"}]
        if new_hard != expected_new:
            raise AssertionError("v0.6.18 changed a non-registered hard reason")
        if bool(control["scale_qualified"]) and not bool(candidate["scale_qualified"]):
            raise AssertionError("v0.6.18 demotion cannot reject a v0.6.6-qualified identity")
        if any(x in SAFETY_REASONS for x in old_hard):
            safety_candidates += 1
            if bool(candidate["scale_qualified"]):
                raise AssertionError("v0.6.18 bypassed an unchanged long-span safety gate")

        rows.append({
            "phase": phase,
            "five_filtered_occurrence_bars": list(filtered),
            "five_filtered_occurrence_times": [str(bars[i]["timestamp"]) for i in filtered],
            "published_raw_occurrence_bars": list(raw),
            "five_occurrence_times": [str(bars[i]["timestamp"]) for i in raw],
            "publishing_confirmation_bar": confirmation,
            "control_qualified": bool(control["scale_qualified"]),
            "candidate_qualified": bool(candidate["scale_qualified"]),
            "control_hard_reasons": old_hard,
            "candidate_hard_reasons": new_hard,
            "demoted_path_diagnostics": candidate["demoted_path_diagnostics"],
            "future_outcome_used": False,
            "trade_authority": False,
        })

    summary = {
        "view": view,
        "bars": len(bars),
        "tuple_births": len(ridge.tuple_births),
        "canonical_filtered_groups": len(filtered_rows),
        "published_identities": len(rows),
        "no_valid_publication": no_valid,
        "suppressed_would_be_rewrites": suppressed_rewrites,
        "control_qualified": sum(r["control_qualified"] for r in rows),
        "candidate_qualified": sum(r["candidate_qualified"] for r in rows),
        "newly_qualified": sum(r["candidate_qualified"] and not r["control_qualified"] for r in rows),
        "control_hard_reason_counts": dict(Counter(x for r in rows for x in r["control_hard_reasons"])),
        "candidate_hard_reason_counts": dict(Counter(x for r in rows for x in r["candidate_hard_reasons"])),
        "long_span_safety_candidates_checked": safety_candidates,
        "future_outcome_used": False,
        "trade_authority": False,
    }
    return rows, filtered_rows, summary


def record_state(row: dict, bars: list[dict], closes: list[float], view: str) -> dict:
    pair = reconstruct_pair(row, bars, view)
    d1 = str(pair["direction_versions"]["D1"])
    amp = float(pair["amplitude_unit_price"])
    cand = d1_primary_margin_rescue(
        d1,
        closes,
        row["published_raw_occurrence_bars"],
        amp,
    )
    if d1 != "uncertain":
        if str(cand["classification"]) != d1 or bool(cand["D1_decisive_overridden"]):
            raise AssertionError("v0.6.25 overrode a D1 decisive state")
    return {
        "D1": d1,
        "v0625": str(cand["classification"]),
        "rescue": bool(cand["rescue_applied"]),
        "overridden": bool(cand["D1_decisive_overridden"]),
    }


def qualification_matrix(pairs: list[tuple[dict, dict]]) -> dict:
    out = {
        "both_qualified": 0,
        "both_rejected": 0,
        "main_only_qualified": 0,
        "other_only_qualified": 0,
    }
    for a, b in pairs:
        qa, qb = bool(a["candidate_qualified"]), bool(b["candidate_qualified"])
        if qa and qb:
            out["both_qualified"] += 1
        elif not qa and not qb:
            out["both_rejected"] += 1
        elif qa:
            out["main_only_qualified"] += 1
        else:
            out["other_only_qualified"] += 1
    return out


def gates_for_slice(per_offset: dict, pooled_d1: dict, pooled_v0625: dict, rescue_count: int, override_count: int) -> dict:
    shares = pooled_v0625["pooled_decisive_label_shares"]
    return {
        "D1_decisive_override_zero": override_count == 0,
        "all_offsets_exact_agreement_nonworse": all(
            row["v0625"]["exact_agreement"] >= row["D1"]["exact_agreement"]
            for row in per_offset.values()
        ),
        "pooled_exact_agreement_nonworse": pooled_v0625["exact_agreement"] >= pooled_d1["exact_agreement"],
        "pooled_decisive_coverage_material": (
            pooled_v0625["pooled_decisive_coverage"] >= 0.65
            and pooled_v0625["pooled_decisive_coverage"] >= pooled_d1["pooled_decisive_coverage"] + 0.15
        ),
        "each_offset_side_decisive_coverage_at_least_55pct": all(
            min(row["v0625"]["main_decisive_coverage"], row["v0625"]["other_decisive_coverage"]) >= 0.55
            for row in per_offset.values()
        ),
        "pooled_decisive_agreement_at_least_99_5pct": pooled_v0625["decisive_agreement"] >= 0.995,
        "opposite_trend_conflict_zero": pooled_v0625["opposite_trend_conflict_count"] == 0,
        "decisive_class_diversity": (
            shares.get("uptrend", 0.0) >= 0.15
            and shares.get("downtrend", 0.0) >= 0.15
            and shares.get("range", 0.0) >= 0.02
        ),
        "nonzero_margin_rescue": rescue_count > 0,
    }


def evaluate_year(year: int, views: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    bars = {view: bars_from_frame(frame) for view, frame in views.items()}
    closes = {view: [float(r["close"]) for r in bars[view]] for view in VIEWS}
    records, filtered, maps, states, generation = {}, {}, {}, {}, {}
    rescue_count = 0
    override_count = 0

    for view in VIEWS:
        records[view], filtered[view], generation[view] = build_publications(view, bars[view])
        maps[view] = {fkey(r): r for r in records[view]}
        states[view] = {}
        for row in records[view]:
            if not bool(row["candidate_qualified"]):
                continue
            state = record_state(row, bars[view], closes[view], view)
            states[view][fkey(row)] = state
            rescue_count += int(state["rescue"])
            override_count += int(state["overridden"])
    if override_count != 0:
        raise AssertionError("D1 decisive override count must remain zero")

    per_offset = {}
    pair_payload = {}
    pooled_d1_pairs = []
    pooled_v0625_pairs = []
    total_filtered = total_raw = total_bothq = 0
    qmats = {}

    for view in OTHER_VIEWS:
        graph = build_edge_graph(
            filtered[MAIN_VIEW],
            filtered[view],
            time_field="five_filtered_occurrence_times",
            nominal_bar_minutes=5.0,
            require_phase=True,
        )
        filtered_pairs = list(graph.mutual_unique_matches)
        strict = []
        for i, j in filtered_pairs:
            left = maps[MAIN_VIEW].get(fkey(filtered[MAIN_VIEW][i]))
            right = maps[view].get(fkey(filtered[view][j]))
            if left is None or right is None:
                continue
            if strict_anchor_edge(left, right, 5.0) is not None:
                strict.append((left, right))
        qmat = qualification_matrix(strict)
        both = [(a, b) for a, b in strict if a["candidate_qualified"] and b["candidate_qualified"]]
        d1_pairs = []
        cand_pairs = []
        for left, right in both:
            ls = states[MAIN_VIEW][fkey(left)]
            rs = states[view][fkey(right)]
            d1_pairs.append((ls["D1"], rs["D1"]))
            cand_pairs.append((ls["v0625"], rs["v0625"]))
        per_offset[view] = {"D1": metrics(d1_pairs), "v0625": metrics(cand_pairs)}
        pair_payload[view] = {"D1": d1_pairs, "v0625": cand_pairs}
        qmats[view] = qmat
        total_filtered += len(filtered_pairs)
        total_raw += len(strict)
        total_bothq += len(both)
        pooled_d1_pairs.extend(d1_pairs)
        pooled_v0625_pairs.extend(cand_pairs)

    pooled_d1 = metrics(pooled_d1_pairs)
    pooled_v0625 = metrics(pooled_v0625_pairs)
    gates = gates_for_slice(per_offset, pooled_d1, pooled_v0625, rescue_count, override_count)
    result = {
        "year": year,
        "generation": generation,
        "controls": {
            "filtered_mutual_unique_pairs": total_filtered,
            "raw_strict_pairs": total_raw,
            "both_v0618_qualified_pairs": total_bothq,
            "qualification_matrix_by_offset": qmats,
        },
        "rescue_audit": {
            "v0625_rescued_record_count": rescue_count,
            "D1_decisive_override_count": override_count,
            "minimum_consensus_margin": MIN_CONSENSUS_MARGIN,
        },
        "per_offset": per_offset,
        "pooled": {"D1": pooled_d1, "v0625": pooled_v0625},
        "gates": gates,
        "all_original_v0625_gates_pass": all(gates.values()),
    }
    return result, pair_payload


def combine_overall(year_results: dict[int, dict], pair_payloads: dict[int, dict]) -> dict:
    per_offset = {}
    pooled_d1_pairs = []
    pooled_cand_pairs = []
    for view in OTHER_VIEWS:
        d1_pairs = []
        cand_pairs = []
        for year in YEARS:
            d1_pairs.extend(pair_payloads[year][view]["D1"])
            cand_pairs.extend(pair_payloads[year][view]["v0625"])
        per_offset[view] = {"D1": metrics(d1_pairs), "v0625": metrics(cand_pairs)}
        pooled_d1_pairs.extend(d1_pairs)
        pooled_cand_pairs.extend(cand_pairs)

    d1 = metrics(pooled_d1_pairs)
    cand = metrics(pooled_cand_pairs)
    rescue_count = sum(year_results[y]["rescue_audit"]["v0625_rescued_record_count"] for y in YEARS)
    override_count = sum(year_results[y]["rescue_audit"]["D1_decisive_override_count"] for y in YEARS)
    gates = gates_for_slice(per_offset, d1, cand, rescue_count, override_count)
    return {
        "controls": {
            "filtered_mutual_unique_pairs": sum(year_results[y]["controls"]["filtered_mutual_unique_pairs"] for y in YEARS),
            "raw_strict_pairs": sum(year_results[y]["controls"]["raw_strict_pairs"] for y in YEARS),
            "both_v0618_qualified_pairs": sum(year_results[y]["controls"]["both_v0618_qualified_pairs"] for y in YEARS),
        },
        "rescue_audit": {
            "v0625_rescued_record_count": rescue_count,
            "D1_decisive_override_count": override_count,
            "minimum_consensus_margin": MIN_CONSENSUS_MARGIN,
        },
        "per_offset": per_offset,
        "pooled": {"D1": d1, "v0625": cand},
        "gates": gates,
        "all_original_v0625_gates_pass": all(gates.values()),
    }


def write_card(path: Path, result: dict) -> None:
    lines = [
        "# Two-Wave v0.6.47 independent temporal morphology replication result",
        "",
        f"Formal verdict: **`{result['verdict']}`**",
        "",
        "This is post-2020 temporal replication of frozen components, not a new challenger and not global morphology acceptance.",
        "",
        "## External pre-score controls",
        "",
        f"- Development five-offset equivalence run: `{result['controls']['development_resampler_precheck_run']}` (pass).",
        f"- 2024 native offset-0 exact: **{result['controls']['external_native_offset0_equivalence']['2024']['exact']}**.",
        f"- 2025 native offset-0 exact: **{result['controls']['external_native_offset0_equivalence']['2025']['exact']}**.",
        "",
        "## Year-isolated replication",
        "",
        "| slice | both-qualified pairs | D1 exact | v0.6.25 exact | D1 coverage | v0.6.25 coverage | decisive agreement | opposite conflicts | all original gates |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key in ("2024", "2025", "2026", "overall"):
        row = result["years"][key] if key != "overall" else result["overall"]
        d1 = row["pooled"]["D1"]
        cand = row["pooled"]["v0625"]
        lines.append(
            f"| {key} | {row['controls']['both_v0618_qualified_pairs']} | "
            f"{d1['exact_agreement']:.4%} | {cand['exact_agreement']:.4%} | "
            f"{d1['pooled_decisive_coverage']:.4%} | {cand['pooled_decisive_coverage']:.4%} | "
            f"{cand['decisive_agreement']:.4%} | {cand['opposite_trend_conflict_count']} | "
            f"{row['all_original_v0625_gates_pass']} |"
        )
    lines += [
        "",
        "## Authority",
        "",
        "- qualification champion remains v0.6.18;",
        "- parent-direction winner remains unset;",
        "- morphology_acceptance remains false;",
        "- trade_authority remains false;",
        "- production_authority remains false;",
        "- independent reference morphology labels are still required for full acceptance.",
    ]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--external-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    input_audit = {}
    for name, expected in EXPECTED_INPUTS.items():
        path = args.external_root / name
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise AssertionError(f"external SHA256 mismatch for {name}: {actual} != {expected}")
        input_audit[name] = {"sha256": actual, "bytes": path.stat().st_size}

    one_minute = {}
    for year in YEARS:
        path = args.external_root / f"{year}_1m.parquet"
        frame = normalize_external_frame(path, require_one_minute_metadata=True)
        if len(frame) != EXPECTED_1M_ROWS[year]:
            raise AssertionError(f"{year} 1m row-count drift: {len(frame)}")
        years = set(pd.to_datetime(frame["trading_day"]).dt.year.unique())
        if years != {year}:
            raise AssertionError(f"{year} 1m contains wrong trading years: {years}")
        one_minute[year] = frame

    native_controls = {}
    for year in (2024, 2025):
        native = normalize_external_frame(
            args.external_root / f"{year}_5m_offset_0.parquet",
            require_one_minute_metadata=False,
        )
        if len(native) != EXPECTED_NATIVE_5M_ROWS[year]:
            raise AssertionError(f"{year} native 5m row-count drift: {len(native)}")
        generated = resample_five_minute_offset(one_minute[year], 0)
        control = exact_ohlc_timestamp_equivalence(generated, native)
        native_controls[str(year)] = control
        if not bool(control["exact"]):
            dump_json(args.output / "PRE_SCORE_CONTROL_FAILURE.json", {
                "year": year,
                "control": control,
                "morphology_scoring_started": False,
            })
            raise AssertionError(f"{year} external native offset-0 equivalence failed before morphology scoring")

    # Only after both external native controls pass may morphology scoring begin.
    year_results = {}
    pair_payloads = {}
    for year in YEARS:
        views = {VIEWS[offset]: resample_five_minute_offset(one_minute[year], offset) for offset in range(5)}
        year_result, payload = evaluate_year(year, views)
        year_results[year] = year_result
        pair_payloads[year] = payload
        dump_json(args.output / f"year_{year}.json", year_result)
        print(json.dumps({
            "year": year,
            "both_v0618_qualified_pairs": year_result["controls"]["both_v0618_qualified_pairs"],
            "D1_exact": year_result["pooled"]["D1"]["exact_agreement"],
            "v0625_exact": year_result["pooled"]["v0625"]["exact_agreement"],
            "v0625_coverage": year_result["pooled"]["v0625"]["pooled_decisive_coverage"],
            "all_original_gates": year_result["all_original_v0625_gates_pass"],
        }, sort_keys=True), flush=True)

    overall = combine_overall(year_results, pair_payloads)
    all_pass = all(year_results[y]["all_original_v0625_gates_pass"] for y in YEARS) and overall["all_original_v0625_gates_pass"]
    result = {
        "schema": "two_wave_independent_temporal_morphology_replication@0.6.47",
        "verdict": (
            "v0647_temporal_replication_under_original_v0625_gate_all_pass"
            if all_pass
            else "v0647_temporal_replication_under_original_v0625_gate_not_all_pass"
        ),
        "controls": {
            "development_resampler_precheck_run": 34623300582,
            "development_all_five_offsets_exact": True,
            "external_input_audit": input_audit,
            "external_native_offset0_equivalence": native_controls,
            "external_timestamp_policy": "first19_as_Asia/Shanghai_wall_clock_then_convert_to_UTC",
            "year_isolated_recognition": True,
            "cross_year_parent_edges": 0,
        },
        "years": {str(y): year_results[y] for y in YEARS},
        "overall": overall,
        "qualification_policy": "v0.6.18",
        "direction_component": "v0.6.25",
        "direction_winner": None,
        "morphology_acceptance": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "production_authority": False,
        "fresh_oos_claimed": False,
        "interpretation": "temporal_replication_only_independent_reference_labels_still_required",
    }
    dump_json(args.output / "summary.json", result)
    write_card(args.output / "RESULT_CARD.md", result)
    print(json.dumps({
        "verdict": result["verdict"],
        "overall_D1_exact": overall["pooled"]["D1"]["exact_agreement"],
        "overall_v0625_exact": overall["pooled"]["v0625"]["exact_agreement"],
        "overall_v0625_coverage": overall["pooled"]["v0625"]["pooled_decisive_coverage"],
        "overall_all_original_gates": overall["all_original_v0625_gates_pass"],
        "morphology_acceptance": False,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
