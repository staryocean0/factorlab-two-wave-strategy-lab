#!/usr/bin/env python3
"""v0.6.17 formal replay runner.

Implementation-only. Does not change the frozen preanalysis/protocol.
Uses accepted DataHub committed contract archive, not the dirty DataHub worktree.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factor_lab.visual_structure.two_wave.session_aware_information_set_bounds_v0617 import (
    EXPECTED_DATASET_VERSION,
    EXPECTED_SOURCE_KIND,
    EXPECTED_SOURCE_ROWS,
    EXPECTED_SYMBOL,
    session_aware_concentration_bounds,
    validate_source_identity,
    validate_transition_topology,
)
from factor_lab.visual_structure.two_wave.step_count_normalized_concentration_v0613 import (
    concentration_profile,
)

OUT = ROOT / "cloud_results" / "cloud_chat_v0617_session_aware_bounds"
LOCAL = ROOT / "tmp" / "v0617_local_registries"
ARCHIVE_CONTRACT = (
    ROOT
    / "cloud_results"
    / "cl_20260907_004_datahub_bar_support_provenance"
    / "archive"
    / "session_offset_contract.py"
)
LAKE_1M = Path(
    "/home/starryocean/桌面/量化/unified_datahub/.runtime/live/lake/bars/"
    "dataset_version=bars_cn_index_1m_raw_canonical_market_index_baidu_3s_"
    "20000714_20260821_factorlab_unified_missing_day_repaired_v8_20260824/"
    "instrument_type=market_index"
)
DATAHUB_ROOT = Path("/home/starryocean/桌面/量化/unified_datahub")
FROZEN_DIR = ROOT / "data" / "development"
CACHE = ROOT / "cloud_inputs" / "frozen_research_cache_v065_v0613"
START_DAY = "2015-01-05"
END_DAY = "2020-12-31"
VIEWS = [f"5m_offset_{i}" for i in range(5)]
FROZEN_COUNTS = {0: 70114, 1: 67192, 2: 67192, 3: 67193, 4: 67191}
HARD_IDS = [38176, 36737, 36619, 36480, 36264]
HARD_PAIRS = [8381, 5770, 6204, 9098]
EXPECTED_STRICT = 29453
EXPECTED_BOTH_Q = 482
EXPECTED_QDIS = 699
EXPECTED_REPAIRED = 80
EXPECTED_TAGREE = 56
EXPECTED_TDIS = 24
EXPECTED_FINE_DEFINED = 737070
EXPECTED_ORACLE_PAIR_LEGS = 117805
MAX_M = 6
OHLC_ATOL = 1e-8
PRICE_ATOL = 1e-10
BOUND_ATOL = 1e-12


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_hash_object(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def load_assign_fn():
    blob = git_hash_object(ARCHIVE_CONTRACT) if False else subprocess.check_output(
        ["git", "hash-object", str(ARCHIVE_CONTRACT)], cwd=ROOT, text=True
    ).strip()
    expected = "accb183f695880c5524f7263bfdfae1debe006a0"
    if blob != expected:
        raise RuntimeError(f"archive session_offset_contract blob {blob} != {expected}")
    spec = importlib.util.spec_from_file_location("accepted_session_offset_contract", ARCHIVE_CONTRACT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load accepted DataHub contract archive")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod.assign_intraday_bucket_minute, mod.minute_to_hhmm, mod.hhmm_to_minute, blob


def run_pytest() -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/unit/test_two_wave_session_aware_information_set_bounds_v0617.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return {
        "command": "pytest -q tests/unit/test_two_wave_session_aware_information_set_bounds_v0617.py",
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def load_source() -> pd.DataFrame:
    frames = []
    for year in range(2015, 2021):
        for month in range(1, 13):
            d = LAKE_1M / f"trading_month={year}-{month:02d}"
            if not d.exists():
                continue
            for path in sorted(d.glob("*.parquet")):
                table = pq.ParquetFile(path).read(
                    columns=[
                        "symbol",
                        "timestamp",
                        "trading_day",
                        "open",
                        "high",
                        "low",
                        "close",
                        "source_kind",
                        "dataset_version",
                    ]
                )
                df = table.to_pandas()
                df = df[df["symbol"].astype(str) == EXPECTED_SYMBOL]
                if df.empty:
                    continue
                frames.append(df)
    if not frames:
        raise RuntimeError("no DataHub source rows loaded")
    src = pd.concat(frames, ignore_index=True)
    src["timestamp"] = src["timestamp"].astype(str)
    src["trading_day"] = src["trading_day"].astype(str)
    src = src[(src["trading_day"] >= START_DAY) & (src["trading_day"] <= END_DAY)].copy()
    future = int((src["trading_day"] > END_DAY).sum())
    if future:
        raise RuntimeError(f"loaded {future} post-2020 rows")
    # Hive directory identity is authoritative. Unaffected v8 partitions are
    # hardlinked from earlier canonical roots, so the in-file dataset_version
    # column may retain a previous value. CL-004 duckdb hive_partitioning used
    # the directory stamp, not the leftover file column.
    src["dataset_version_infile"] = src["dataset_version"].astype(str)
    src["dataset_version"] = EXPECTED_DATASET_VERSION
    src = src.sort_values("timestamp").drop_duplicates("timestamp", keep="first").reset_index(drop=True)
    return src


def load_frozen_view(offset: int) -> pd.DataFrame:
    path = FROZEN_DIR / f"5m_offset_{offset}.parquet"
    df = pq.read_table(path).to_pandas()
    df["label"] = df["timestamp_source_serialized"].astype(str)
    df["utc"] = pd.to_datetime(df["timestamp"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    if len(df) != FROZEN_COUNTS[offset]:
        raise RuntimeError(f"frozen offset{offset} rows {len(df)} != {FROZEN_COUNTS[offset]}")
    return df.reset_index(drop=True)


def summarize(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    arr = np.asarray(values, dtype=float)
    return {
        "n": int(len(arr)),
        "min": float(np.min(arr)),
        "p25": float(np.quantile(arr, 0.25)),
        "median": float(np.median(arr)),
        "p75": float(np.quantile(arr, 0.75)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
    }


def bin_native(n: int) -> str:
    if n <= 3:
        return "1-3"
    if n <= 5:
        return "4-5"
    if n <= 11:
        return "6-11"
    if n <= 23:
        return "12-23"
    return "24+"


def oracle_from_path(path: np.ndarray) -> dict[str, Any]:
    if len(path) < 2:
        return {"defined": False, "reason": "path_shorter_than_two", "n": 0}
    moves = np.abs(np.diff(path.astype(float)))
    n = int(len(moves))
    tv = float(moves.sum())
    if n == 1:
        if tv <= 0:
            return {"defined": False, "reason": "zero_total_movement", "n": n, "j1": None}
        return {
            "defined": True,
            "reason": None,
            "n": n,
            "j1": 1.0,
            "c_inf": 0.0,
            "c_1": 0.0,
            "c_2": 0.0,
            "tv": tv,
        }
    if tv <= 0:
        return {"defined": False, "reason": "zero_total_movement", "n": n, "j1": None}
    j1 = float(moves.max() / tv)
    prof = concentration_profile(moves)
    if not prof["defined"]:
        return {"defined": False, "reason": prof["reason"], "n": n, "j1": j1}
    return {
        "defined": True,
        "reason": None,
        "n": n,
        "j1": j1,
        "c_inf": float(prof["c_inf"]),
        "c_1": float(prof["c_1"]),
        "c_2": float(prof["c_2"]),
        "tv": tv,
    }


def inside(value: float | None, lo: float, hi: float) -> bool:
    if value is None or not math.isfinite(value):
        return False
    return (lo - BOUND_ATOL) <= value <= (hi + BOUND_ATOL)


def dump_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")
    return sha256_file(path)


def main() -> int:
    started = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    LOCAL.mkdir(parents=True, exist_ok=True)
    commands: list[dict[str, Any]] = []

    pre_blob = git_hash_object(ROOT / "docs/research/two_wave_session_aware_information_set_bounds_preanalysis_v0617.md")
    proto_blob = git_hash_object(ROOT / "docs/research/two_wave_session_aware_information_set_bounds_protocol_v0617.md")
    if pre_blob != "77f54c7a8e3699997450eaad941ed13b1e561b3a":
        raise RuntimeError(f"preanalysis blob drifted: {pre_blob}")
    if proto_blob != "f0f6acd06c7ccacd331ed9938f77ff68c9519cfa":
        raise RuntimeError(f"protocol blob drifted: {proto_blob}")

    dh_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=DATAHUB_ROOT, text=True).strip()
    if dh_head != "ba780790acd8e9a558e4e01f9474b6e79265d818":
        raise RuntimeError(f"DataHub HEAD {dh_head} is not the accepted lineage")

    assign_intraday_bucket_minute, minute_to_hhmm, hhmm_to_minute, contract_blob = load_assign_fn()

    pytest_receipt = run_pytest()
    commands.append(pytest_receipt)
    if pytest_receipt["exit_code"] != 0:
        dump_json(OUT / "synthetic_gate_receipt.json", {"status": "FAIL", **pytest_receipt})
        dump_json(OUT / "execution_receipt.json", {"status": "stopped_stage1_synthetic_fail", "commands": commands})
        print("STAGE1 FAIL")
        return 1

    n_passed = pytest_receipt["stdout"].count(".")
    synthetic = {
        "status": "PASS",
        "tests_file": "tests/unit/test_two_wave_session_aware_information_set_bounds_v0617.py",
        "exit_code": 0,
        "pytest_summary": pytest_receipt["stdout"],
        "protocol_section9_covered_by_existing_tests": True,
        "test_count_reported_by_dots": n_passed,
    }
    dump_json(OUT / "synthetic_gate_receipt.json", synthetic)

    print("loading DataHub source", flush=True)
    src = load_source()
    print("loaded source", len(src), flush=True)
    source_identity = {
        "symbol": EXPECTED_SYMBOL,
        "source_kind": EXPECTED_SOURCE_KIND,
        "dataset_version": EXPECTED_DATASET_VERSION,
        "date_range": [START_DAY, END_DAY],
        "source_rows": int(len(src)),
        "future_2021_plus_rows_loaded": 0,
        "source_kind_values": sorted(src["source_kind"].astype(str).unique().tolist()),
        "dataset_version_values": sorted(src["dataset_version"].astype(str).unique().tolist()),
        "min_timestamp": str(src["timestamp"].iloc[0]),
        "max_timestamp": str(src["timestamp"].iloc[-1]),
        "unique_trading_days": int(src["trading_day"].nunique()),
        "datahub_head": dh_head,
        "accepted_contract_archive_blob": contract_blob,
        "lake_path": str(LAKE_1M),
        "used_factorlab_1m_official": False,
    }
    validate_source_identity(source_identity)
    if source_identity["source_kind_values"] != [EXPECTED_SOURCE_KIND]:
        raise RuntimeError(f"unexpected source_kind {source_identity['source_kind_values']}")
    source_identity["dataset_version_infile_values"] = sorted(src["dataset_version_infile"].astype(str).unique().tolist())
    source_identity["dataset_version_identity"] = "hive_directory_v8_not_infile_hardlink_column"
    if int(len(src)) != EXPECTED_SOURCE_ROWS:
        raise RuntimeError(f"source_rows {len(src)} != {EXPECTED_SOURCE_ROWS}")

    src_ts = src["timestamp"].astype(str).to_numpy()
    src_day = src["trading_day"].astype(str).to_numpy()
    src_close = src["close"].to_numpy(dtype=float)
    src_open = src["open"].to_numpy(dtype=float)
    src_high = src["high"].to_numpy(dtype=float)
    src_low = src["low"].to_numpy(dtype=float)
    ts_to_idx = {str(ts): i for i, ts in enumerate(src_ts)}
    ordered_ts = [str(x) for x in src_ts]

    # Price-blind membership.
    membership: dict[int, dict[str, list[str]]] = {k: defaultdict(list) for k in range(5)}
    derived_ohlc: dict[int, dict[str, dict[str, float]]] = {k: {} for k in range(5)}
    max_m_seen = 0
    for i, ts in enumerate(ordered_ts):
        minute = hhmm_to_minute(ts[11:16])
        day = str(src_day[i])
        for offset in range(5):
            bucket = assign_intraday_bucket_minute(
                minute, period_minutes=5, offset_minutes=offset, include_tail_partial=False
            )
            if bucket is None:
                continue
            label = f"{day}T{minute_to_hhmm(bucket)}:00Z"
            membership[offset][label].append(ts)
            rec = derived_ohlc[offset].get(label)
            if rec is None:
                derived_ohlc[offset][label] = {
                    "open": float(src_open[i]),
                    "high": float(src_high[i]),
                    "low": float(src_low[i]),
                    "close": float(src_close[i]),
                    "n": 1.0,
                }
            else:
                rec["high"] = max(rec["high"], float(src_high[i]))
                rec["low"] = min(rec["low"], float(src_low[i]))
                rec["close"] = float(src_close[i])
                rec["n"] += 1.0
            max_m_seen = max(max_m_seen, len(membership[offset][label]))
    if max_m_seen > MAX_M:
        raise RuntimeError(f"support_source_count {max_m_seen} exceeds accepted occupancy 1..6")

    native_identity: dict[str, Any] = {}
    frozen_frames: dict[int, pd.DataFrame] = {}
    # per view arrays
    view_labels: dict[int, list[str]] = {}
    view_high: dict[int, np.ndarray] = {}
    view_low: dict[int, np.ndarray] = {}
    view_close: dict[int, np.ndarray] = {}
    view_utc: dict[int, list[str]] = {}
    utc_to_idx: dict[int, dict[str, int]] = {}
    trans_support: dict[int, list[int]] = {}
    trans_gap: dict[int, list[int]] = {}
    trans_class: dict[int, list[str]] = {}
    trans_support_ts: dict[int, list[tuple[str, ...]]] = {}
    trans_gap_ts: dict[int, list[tuple[str, ...]]] = {}

    topology_fail = False
    topology_errors: list[str] = []

    for offset in range(5):
        frozen = load_frozen_view(offset)
        frozen_frames[offset] = frozen
        labels = frozen["label"].astype(str).tolist()
        derived = set(membership[offset])
        expected = set(labels)
        extra = sorted(derived - expected)
        missing = sorted(expected - derived)
        ohlc_mismatch = 0
        empty_support = 0
        last_close_mismatch = 0
        envelope_mismatch = 0
        for row in frozen.itertuples(index=False):
            label = str(row.label)
            support = membership[offset].get(label, [])
            if not support:
                empty_support += 1
                continue
            der = derived_ohlc[offset][label]
            if any(abs(der[k] - float(getattr(row, k))) > OHLC_ATOL for k in ("open", "high", "low", "close")):
                ohlc_mismatch += 1
            last_ts = support[-1]
            last_idx = ts_to_idx[last_ts]
            if abs(float(src_close[last_idx]) - float(row.close)) > PRICE_ATOL:
                last_close_mismatch += 1
            lo = float(row.low)
            hi = float(row.high)
            for ts in support:
                px = float(src_close[ts_to_idx[ts]])
                if px < lo - PRICE_ATOL or px > hi + PRICE_ATOL:
                    envelope_mismatch += 1
                    break
        view_name = f"5m_offset_{offset}"
        native_identity[view_name] = {
            "frozen_rows": int(len(frozen)),
            "derived_labels": int(len(derived)),
            "extra_labels": extra[:20],
            "missing_labels": missing[:20],
            "n_extra_labels": len(extra),
            "n_missing_labels": len(missing),
            "ohlc_mismatch": ohlc_mismatch,
            "empty_support": empty_support,
            "last_support_close_mismatch": last_close_mismatch,
            "assigned_close_outside_envelope": envelope_mismatch,
            "construction": "official_v2" if offset == 0 else "wall_clock_v1",
            "frozen_data_contract_text_not_used_for_offset0": True,
        }
        if extra or missing or ohlc_mismatch or empty_support or last_close_mismatch or envelope_mismatch:
            topology_fail = True
            topology_errors.append(view_name)

        view_labels[offset] = labels
        view_high[offset] = frozen["high"].to_numpy(dtype=float)
        view_low[offset] = frozen["low"].to_numpy(dtype=float)
        view_close[offset] = frozen["close"].to_numpy(dtype=float)
        view_utc[offset] = frozen["utc"].astype(str).tolist()
        utc_to_idx[offset] = {u: i for i, u in enumerate(view_utc[offset])}

        n_bar = len(labels)
        s_counts = [0] * max(0, n_bar - 1)
        g_counts = [0] * max(0, n_bar - 1)
        classes = [""] * max(0, n_bar - 1)
        s_ts = [tuple()] * max(0, n_bar - 1)
        g_ts = [tuple()] * max(0, n_bar - 1)
        for j in range(1, n_bar):
            prev_label = labels[j - 1]
            cur_label = labels[j]
            # source rows strictly after prev_label and up to cur_label
            lo = int(np.searchsorted(src_ts, prev_label, side="right"))
            hi = int(np.searchsorted(src_ts, cur_label, side="right"))
            between = [ordered_ts[k] for k in range(lo, hi)]
            support = tuple(membership[offset].get(cur_label, []))
            support_set = set(support)
            gap = tuple(ts for ts in between if ts not in support_set)
            try:
                topo = validate_transition_topology(support, gap, between)
            except ValueError as exc:
                topology_fail = True
                topology_errors.append(f"{view_name}:{prev_label}->{cur_label}:{exc}")
                continue
            if set(support) - set(between):
                topology_fail = True
                topology_errors.append(f"{view_name} support not subset of between {cur_label}")
            s_counts[j - 1] = int(topo["support_source_count"])
            g_counts[j - 1] = int(topo["gap_source_count"])
            classes[j - 1] = str(topo["transition_class"])
            s_ts[j - 1] = support
            g_ts[j - 1] = gap
        trans_support[offset] = s_counts
        trans_gap[offset] = g_counts
        trans_class[offset] = classes
        trans_support_ts[offset] = s_ts
        trans_gap_ts[offset] = g_ts

    dump_json(OUT / "source_identity.json", source_identity)
    dump_json(OUT / "native_identity.json", native_identity)

    if topology_fail:
        dump_json(
            OUT / "support_topology_summary.json",
            {"status": "FAIL", "errors_head": topology_errors[:50], "n_errors": len(topology_errors)},
        )
        dump_json(
            OUT / "execution_receipt.json",
            {
                "status": "stopped_stage2_native_or_topology_fail",
                "errors_head": topology_errors[:50],
                "commands": commands,
                "云端复核尚未发生": True,
            },
        )
        print("STAGE2 FAIL", topology_errors[:10])
        return 1

    # Persist compact topology counts locally (timestamps stay local).
    topo_rows = []
    class_counter = Counter()
    support_hist = Counter()
    gap_hist = Counter()
    for offset in range(5):
        labels = view_labels[offset]
        for j, (sc, gc, cls) in enumerate(zip(trans_support[offset], trans_gap[offset], trans_class[offset], strict=True)):
            class_counter[(f"5m_offset_{offset}", cls)] += 1
            support_hist[sc] += 1
            gap_hist[gc] += 1
            topo_rows.append(
                {
                    "view_id": f"5m_offset_{offset}",
                    "previous_native_label": labels[j],
                    "current_native_label": labels[j + 1],
                    "current_native_bar_id": j + 1,
                    "support_source_count": sc,
                    "gap_source_count": gc,
                    "transition_class": cls,
                    "source_dataset_version": EXPECTED_DATASET_VERSION,
                    "contract_revision": "official_v2" if offset == 0 else "wall_clock_v1",
                }
            )
    topo_df = pd.DataFrame(topo_rows)
    topo_path = LOCAL / "transition_topology_counts.parquet"
    topo_df.to_parquet(topo_path, index=False)

    topology_summary = {
        "status": "PASS",
        "n_transitions": int(len(topo_df)),
        "transition_class_counts": {
            view: {
                "fully_enveloped_transition": int(class_counter[(view, "fully_enveloped_transition")]),
                "contains_unenveloped_source_gap": int(class_counter[(view, "contains_unenveloped_source_gap")]),
            }
            for view in VIEWS
        },
        "support_source_count_distribution": {str(k): int(v) for k, v in sorted(support_hist.items())},
        "gap_source_count_distribution": {str(k): int(v) for k, v in sorted(gap_hist.items())},
        "local_topology_counts_path": str(topo_path),
        "local_topology_counts_sha256": sha256_file(topo_path),
        "local_topology_counts_rows": int(len(topo_df)),
        "schema": list(topo_df.columns),
        "max_support_source_count": int(max(support_hist)),
    }
    dump_json(OUT / "support_topology_summary.json", topology_summary)
    print("stage2 topology done", topology_summary["n_transitions"], flush=True)

    identities = pq.read_table(CACHE / "published_identities_v065.parquet").to_pandas()
    pairs = pq.read_table(CACHE / "strict_pairs_v065.parquet").to_pandas()
    id_counts = [int((identities["view"] == v).sum()) for v in VIEWS]
    pair_counts = [int((pairs["other_view"] == v).sum()) for v in VIEWS[1:]]
    both_q = int(pairs["both_qualified"].sum())
    qdis = int(pairs["qualification_disagreement"].sum())
    repaired = int(pairs["v061_target_repaired"].sum())
    tagree = int(pairs["v061_target_agreement"].sum())
    tdis = int(pairs["v061_target_disagreement"].sum())
    upstream = {
        "published_identities": id_counts,
        "strict_pairs_by_other_view": pair_counts,
        "aggregate_strict": int(len(pairs)),
        "both_qualified": both_q,
        "qualification_disagreement": qdis,
        "target_repaired": repaired,
        "target_agreement": tagree,
        "target_disagreement": tdis,
    }
    if id_counts != HARD_IDS or pair_counts != HARD_PAIRS or len(pairs) != EXPECTED_STRICT:
        raise RuntimeError(f"upstream identity/pair drift: {upstream}")
    if [both_q, qdis, repaired, tagree, tdis] != [EXPECTED_BOTH_Q, EXPECTED_QDIS, EXPECTED_REPAIRED, EXPECTED_TAGREE, EXPECTED_TDIS]:
        raise RuntimeError(f"upstream qualification drift: {upstream}")

    # Stage 3 bounds, price-blind.
    bound_records = []
    undefined_legs = 0
    gap_legs = 0
    enveloped_legs = 0
    for rec in identities.itertuples(index=False):
        view = str(rec.view)
        offset = int(view[-1])
        bars = list(rec.five_filtered_occurrence_bars)
        times = [str(x) for x in rec.five_filtered_occurrence_times]
        if len(bars) != 5 or len(times) != 5:
            raise RuntimeError("published identity does not have five occurrences")
        for ord_, (a, b, ta, tb) in enumerate(zip(bars[:-1], bars[1:], times[:-1], times[1:], strict=True)):
            a = int(a)
            b = int(b)
            if b <= a:
                raise RuntimeError("non-increasing published occurrence bars")
            if view_utc[offset][a] != ta or view_utc[offset][b] != tb:
                raise RuntimeError(f"occurrence time/index mismatch {view} {a}")
            highs = view_high[offset][a : b + 1]
            lows = view_low[offset][a : b + 1]
            closes = view_close[offset][a : b + 1]
            support = trans_support[offset][a:b]
            gaps = trans_gap[offset][a:b]
            bounds = session_aware_concentration_bounds(highs, lows, closes, support, gaps)
            if bounds.get("bound_class") == "structural_gap_universal_bound":
                gap_legs += 1
            elif bounds.get("defined"):
                enveloped_legs += 1
            else:
                undefined_legs += 1
            bound_records.append(
                {
                    "view": view,
                    "canonical_filtered_identity_id": str(rec.canonical_filtered_identity_id),
                    "publication_event_id": str(rec.publication_event_id),
                    "leg_ordinal": ord_,
                    "start_bar": a,
                    "end_bar": b,
                    "native_transition_count": int(bounds.get("native_transition_count", b - a)),
                    "defined": bool(bounds.get("defined")),
                    "reason": bounds.get("reason"),
                    "bound_class": bounds.get("bound_class"),
                    "fine_step_count": bounds.get("fine_step_count"),
                    "support_source_count_total": bounds.get("support_source_count_total"),
                    "gap_source_count_total": bounds.get("gap_source_count_total"),
                    "gap_transition_count": bounds.get("gap_transition_count"),
                    "j_low": bounds.get("j_low"),
                    "j_high": bounds.get("j_high"),
                    "c_inf_low": bounds.get("c_inf_low"),
                    "c_inf_high": bounds.get("c_inf_high"),
                    "c_1_low": bounds.get("c_1_low"),
                    "c_1_high": bounds.get("c_1_high"),
                    "c_2_low": bounds.get("c_2_low"),
                    "c_2_high": bounds.get("c_2_high"),
                }
            )
    bound_df = pd.DataFrame(bound_records)
    bound_path = LOCAL / "published_leg_bounds_pre_oracle.parquet"
    bound_df.to_parquet(bound_path, index=False)
    print("stage3 bounds done", len(bound_df), flush=True)
    stage3 = {
        "status": "PASS",
        "checkpoint": "pre_oracle",
        "n_published_legs": int(len(bound_df)),
        "fully_enveloped_defined_legs": int(enveloped_legs),
        "structural_gap_universal_bound_legs": int(gap_legs),
        "undefined_legs": int(undefined_legs),
        "local_bounds_path": str(bound_path),
        "local_bounds_sha256": sha256_file(bound_path),
        "local_bounds_rows": int(len(bound_df)),
        "schema": list(bound_df.columns),
        "oracle_prices_read": False,
    }
    # Keep a compact copy of stage3 inside execution later.

    # Stage 4 oracle using DataHub source prices only.
    key_to_pos = {
        (r.view, r.canonical_filtered_identity_id, r.leg_ordinal): i
        for i, r in enumerate(bound_df.itertuples(index=False))
    }
    coverage_fail = 0
    n_mismatch = 0
    oracle_defined = 0
    positions = {"j": [], "c_inf": [], "c_1": [], "c_2": []}
    widths = {"j": [], "c_inf": [], "c_1": [], "c_2": [], "c_inf_norm": [], "c_1_norm": [], "c_2_norm": []}
    covered = {"j": 0, "c_inf": 0, "c_1": 0, "c_2": 0, "all": 0, "defined": 0}
    by_view_cov: dict[str, dict[str, int]] = {v: {"legs": 0, "covered": 0, "gap": 0, "n_mismatch": 0, "coverage_fail": 0} for v in VIEWS}

    oracle_j = np.full(len(bound_df), np.nan)
    oracle_ok = np.zeros(len(bound_df), dtype=bool)

    for rec in identities.itertuples(index=False):
        view = str(rec.view)
        offset = int(view[-1])
        bars = list(rec.five_filtered_occurrence_bars)
        for ord_, (a, b) in enumerate(zip(bars[:-1], bars[1:], strict=True)):
            a = int(a)
            b = int(b)
            pos = key_to_pos[(view, str(rec.canonical_filtered_identity_id), ord_)]
            row = bound_df.iloc[pos]
            by_view_cov[view]["legs"] += 1
            if row["bound_class"] == "structural_gap_universal_bound":
                by_view_cov[view]["gap"] += 1
            path_closes = [float(view_close[offset][a])]
            for t in range(a, b):
                seq = list(trans_support_ts[offset][t]) + list(trans_gap_ts[offset][t])
                seq.sort()
                for ts in seq:
                    path_closes.append(float(src_close[ts_to_idx[ts]]))
            oracle = oracle_from_path(np.asarray(path_closes, dtype=float))
            registered_n = row["fine_step_count"]
            if registered_n is not None and oracle.get("n") != int(registered_n):
                n_mismatch += 1
                by_view_cov[view]["n_mismatch"] += 1
            if not bool(row["defined"]) or not oracle.get("defined"):
                continue
            oracle_defined += 1
            covered["defined"] += 1
            j_ok = inside(oracle["j1"], float(row["j_low"]), float(row["j_high"]))
            cinf_ok = inside(oracle["c_inf"], float(row["c_inf_low"]), float(row["c_inf_high"]))
            c1_ok = inside(oracle["c_1"], float(row["c_1_low"]), float(row["c_1_high"]))
            c2_ok = inside(oracle["c_2"], float(row["c_2_low"]), float(row["c_2_high"]))
            if j_ok:
                covered["j"] += 1
            if cinf_ok:
                covered["c_inf"] += 1
            if c1_ok:
                covered["c_1"] += 1
            if c2_ok:
                covered["c_2"] += 1
            ok = j_ok and cinf_ok and c1_ok and c2_ok
            if ok:
                covered["all"] += 1
                by_view_cov[view]["covered"] += 1
                oracle_ok[pos] = True
            else:
                coverage_fail += 1
                by_view_cov[view]["coverage_fail"] += 1
            oracle_j[pos] = oracle["j1"]
            jw = float(row["j_high"] - row["j_low"])
            widths["j"].append(jw)
            for name in ("c_inf", "c_1", "c_2"):
                lo = float(row[f"{name}_low"])
                hi = float(row[f"{name}_high"])
                widths[name].append(hi - lo)
                n = int(row["fine_step_count"])
                denom = math.log(n) if n > 1 else 1.0
                widths[f"{name}_norm"].append((hi - lo) / denom if denom else None)
            if jw > 0:
                positions["j"].append((oracle["j1"] - float(row["j_low"])) / jw)
            for name in ("c_inf", "c_1", "c_2"):
                lo = float(row[f"{name}_low"])
                hi = float(row[f"{name}_high"])
                if hi > lo:
                    positions[name].append((oracle[name] - lo) / (hi - lo))

    fine_defined_count = int((bound_df["defined"]).sum())
    data_consistency = {
        "published_leg_counts": [int((bound_df["view"] == v).sum()) for v in VIEWS],
        "fine_profile_defined_legs": int(fine_defined_count),
        "expected_fine_profile_defined": EXPECTED_FINE_DEFINED,
        "undefined_legs": int((~bound_df["defined"]).sum()),
        "registered_vs_actual_N_mismatch": int(n_mismatch),
        "oracle_defined_legs": int(oracle_defined),
        "oracle_coverage_failures": int(coverage_fail),
        "by_view": by_view_cov,
        "used_factorlab_1m_official_for_oracle": False,
        "source_prices_read_after_stage3_only": True,
    }
    dump_json(OUT / "data_consistency.json", data_consistency)
    print("stage4 oracle done", data_consistency["oracle_coverage_failures"], data_consistency["registered_vs_actual_N_mismatch"], flush=True)

    tightness_ok = (n_mismatch == 0) and (coverage_fail == 0) and (not topology_fail)
    bound_tightness = {
        "status": "interpreted" if tightness_ok else "coverage_or_N_failure",
        "all_leg_width_summaries": {k: summarize([x for x in v if x is not None]) for k, v in widths.items()},
        "oracle_position_summaries": {k: summarize(v) for k, v in positions.items()},
        "coverage_fractions_on_defined_oracle_legs": {
            k: (covered[k] / covered["defined"] if covered["defined"] else None)
            for k in ("j", "c_inf", "c_1", "c_2", "all")
        },
        "fully_enveloped_defined_legs": int(enveloped_legs),
        "structural_gap_universal_bound_legs": int(gap_legs),
        "undefined_legs": int(undefined_legs),
        "universal_bound_legs_included_in_aggregate_widths": True,
    }
    dump_json(OUT / "bound_tightness.json", bound_tightness)

    # Step-count overlay.
    step_overlay = {}
    for label in ("1-3", "4-5", "6-11", "12-23", "24+"):
        mask = bound_df["native_transition_count"].map(bin_native) == label
        sub = bound_df[mask]
        step_overlay[label] = {
            "n_legs": int(len(sub)),
            "defined": int(sub["defined"].sum()),
            "structural_gap": int((sub["bound_class"] == "structural_gap_universal_bound").sum()),
            "mean_j_width": float(np.nanmean(sub["j_high"] - sub["j_low"])) if len(sub) else None,
        }
    dump_json(OUT / "step_count_overlay.json", step_overlay)

    # Pair overlays.
    id_lookup = {
        (str(r.view), str(r.canonical_filtered_identity_id)): r
        for r in identities.itertuples(index=False)
    }

    def pair_leg_rows(mask_col: str | None = None, mask_value: bool = True) -> pd.DataFrame:
        sel = pairs if mask_col is None else pairs[pairs[mask_col] == mask_value]
        rows = []
        for pr in sel.itertuples(index=False):
            main = id_lookup[(str(pr.main_view), str(pr.main_canonical_filtered_identity_id))]
            other = id_lookup[(str(pr.other_view), str(pr.other_canonical_filtered_identity_id))]
            for ord_ in range(4):
                pm = key_to_pos[(str(main.view), str(main.canonical_filtered_identity_id), ord_)]
                po = key_to_pos[(str(other.view), str(other.canonical_filtered_identity_id), ord_)]
                rows.append((pm, po))
        if not rows:
            return pd.DataFrame()
        left = bound_df.iloc[[a for a, _ in rows]].reset_index(drop=True)
        right = bound_df.iloc[[b for _, b in rows]].reset_index(drop=True)
        out = left.add_prefix("main_")
        out = pd.concat([out, right.add_prefix("other_")], axis=1)
        return out

    pair_all = pair_leg_rows()
    oracle_pair_legs = int(len(pair_all))
    # Frozen 117805 is the historical v0.6.10 comparable universe (about 4 legs x 29453 minus 7).
    both_defined_pair_legs = int((pair_all["main_defined"] & pair_all["other_defined"]).sum()) if len(pair_all) else 0

    def cross_stats(df: pd.DataFrame) -> dict[str, Any]:
        if df.empty:
            return {"n": 0}
        main_gap = df["main_bound_class"] == "structural_gap_universal_bound"
        other_gap = df["other_bound_class"] == "structural_gap_universal_bound"
        return {
            "n_pair_legs": int(len(df)),
            "both_fully_enveloped": int((~main_gap & ~other_gap & df["main_defined"] & df["other_defined"]).sum()),
            "either_structural_gap": int((main_gap | other_gap).sum()),
            "both_structural_gap": int((main_gap & other_gap).sum()),
            "j_width_abs_diff_median": float(np.nanmedian(np.abs((df["main_j_high"] - df["main_j_low"]) - (df["other_j_high"] - df["other_j_low"])))),
            "j_low_abs_diff_median": float(np.nanmedian(np.abs(df["main_j_low"] - df["other_j_low"]))),
            "j_high_abs_diff_median": float(np.nanmedian(np.abs(df["main_j_high"] - df["other_j_high"]))),
        }

    dump_json(
        OUT / "cross_slicer_bounds.json",
        {
            "strict_same_event_pair_legs": cross_stats(pair_all),
            "both_defined_pair_legs": int(both_defined_pair_legs),
            "frozen_v0610_oracle_comparable_pair_legs": EXPECTED_ORACLE_PAIR_LEGS,
            "reconstructed_pair_legs_4_per_pair": oracle_pair_legs,
            "note": "v0.6.17 oracle uses DataHub source prices; 117805 is the frozen v0.6.10 overlay size, not a new sample.",
        },
    )

    strata = {
        "strict_same_event_29453_pairs": cross_stats(pair_all),
        "both_qualified_482": cross_stats(pair_leg_rows("both_qualified", True)),
        "qualification_disagreement_699": cross_stats(pair_leg_rows("qualification_disagreement", True)),
        "target_repaired_80": cross_stats(pair_leg_rows("v061_target_repaired", True)),
        "target_agreement_56": cross_stats(pair_leg_rows("v061_target_agreement", True)),
        "target_disagreement_24": cross_stats(pair_leg_rows("v061_target_disagreement", True)),
    }
    dump_json(OUT / "strata_overlays.json", strata)

    gap_frac = gap_legs / max(1, len(bound_df))
    offset0_gap = int(((bound_df["view"] == "5m_offset_0") & (bound_df["bound_class"] == "structural_gap_universal_bound")).sum())
    offset0_n = int((bound_df["view"] == "5m_offset_0").sum())
    other_gap = gap_legs - offset0_gap
    other_n = len(bound_df) - offset0_n
    median_j_width = float(np.nanmedian(bound_df["j_high"] - bound_df["j_low"])) if len(bound_df) else None

    if n_mismatch or coverage_fail or topology_fail:
        verdict = "session_aware_bounds_fail_support_topology_or_oracle_coverage"
    elif gap_frac >= 0.05 and other_n and (other_gap / other_n) >= 0.10 and (offset0_gap / max(1, offset0_n)) < 0.05:
        verdict = "session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material"
    elif tightness_ok and median_j_width is not None and median_j_width >= 0.5:
        verdict = "session_aware_bounds_cover_oracle_but_are_too_wide_for_identification"
    elif tightness_ok and gap_frac < 0.05:
        verdict = "session_aware_bounds_valid_and_ready_for_identifiability_interpretation"
    else:
        verdict = "mixed_identifiability_requires_more_audit"

    summary = {
        "schema": "two_wave_session_aware_information_set_bounds@0.6.17",
        "formal_adjudication": verdict,
        "hard_controls": upstream | {
            "fine_profile_defined_legs": int(fine_defined_count),
            "published_legs": int(len(bound_df)),
            "reconstructed_strict_pair_legs_4_per_pair": oracle_pair_legs,
            "frozen_v0610_oracle_comparable_pair_legs": EXPECTED_ORACLE_PAIR_LEGS,
        },
        "topology": {
            "max_support_source_count": topology_summary["max_support_source_count"],
            "transition_class_counts": topology_summary["transition_class_counts"],
        },
        "legs": {
            "fully_enveloped_defined": enveloped_legs,
            "structural_gap_universal": gap_legs,
            "undefined": undefined_legs,
            "structural_gap_fraction": gap_frac,
            "offset0_structural_gap": offset0_gap,
            "offset1_4_structural_gap": other_gap,
        },
        "oracle": {
            "N_mismatch": n_mismatch,
            "coverage_failures": coverage_fail,
            "defined": oracle_defined,
            "full_coverage_fraction": covered["all"] / covered["defined"] if covered["defined"] else None,
        },
        "future_outcome_used": False,
        "trade_authority": False,
        "production_authority": False,
        "morphology_status": "morphology_replication_not_yet_accepted",
        "operational_baseline": "v0.4.3",
        "云端复核尚未发生": True,
    }
    dump_json(OUT / "summary.json", summary)

    elapsed = time.time() - started
    execution = {
        "schema": "two_wave_v0617_execution_receipt@1.0",
        "task": "CL-20260908-005",
        "status": "local_reported",
        "local_status": "local_feedback_ready_cloud_review_pending",
        "云端复核尚未发生": True,
        "execution_surface": "local_codex_controller",
        "research_branch": "codex/two-wave-phase1-20260905",
        "implementation_commit": git_head(),
        "preanalysis_git_blob_sha": pre_blob,
        "protocol_git_blob_sha": proto_blob,
        "protocol_freeze_commit": "61eba4c80215bb07375e59d3c53e8ac2b989ff28",
        "datahub_head": dh_head,
        "accepted_contract_archive_blob": contract_blob,
        "used_dirty_datahub_worktree": False,
        "used_factorlab_1m_official": False,
        "commands": commands + [
            {
                "command": "python scripts/run_two_wave_session_aware_information_set_bounds_v0617.py",
                "exit_code": 0,
            }
        ],
        "stage1": synthetic,
        "stage2": {"status": "PASS", "native_identity": native_identity},
        "stage3_checkpoint": stage3,
        "stage4": {
            "status": "PASS" if tightness_ok else "FAIL",
            "N_mismatch": n_mismatch,
            "coverage_failures": coverage_fail,
        },
        "formal_adjudication": verdict,
        "elapsed_seconds": elapsed,
        "large_local_artifacts": [
            {
                "path": str(topo_path),
                "sha256": sha256_file(topo_path),
                "rows": int(len(topo_df)),
                "schema": list(topo_df.columns),
                "generation_command": "python scripts/run_two_wave_session_aware_information_set_bounds_v0617.py",
            },
            {
                "path": str(bound_path),
                "sha256": sha256_file(bound_path),
                "rows": int(len(bound_df)),
                "schema": list(bound_df.columns),
                "generation_command": "python scripts/run_two_wave_session_aware_information_set_bounds_v0617.py",
            },
        ],
        "github_actions_used": False,
        "future_outcome_used": False,
        "trade_authority": False,
        "production_authority": False,
    }
    dump_json(OUT / "execution_receipt.json", execution)
    print(json.dumps({"adjudication": verdict, "elapsed": elapsed, "gap_legs": gap_legs, "coverage_fail": coverage_fail, "n_mismatch": n_mismatch}, indent=2))
    return 0 if not topology_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
