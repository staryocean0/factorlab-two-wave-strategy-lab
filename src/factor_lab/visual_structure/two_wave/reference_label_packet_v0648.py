"""Blinded independent reference-label packet primitives for v0.6.48.

This module only constructs deterministic case membership and public case IDs.
It never computes a parent direction label and never exposes the hidden sampling
stratum to annotators.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Sequence

import pandas as pd

YEARS = tuple(range(2015, 2021))
LOOKBACK_BARS = 96
CASES_PER_YEAR_PER_STRATUM = 20
CONTROL_EXCLUSION_BARS = 12
STRATA = ("candidate", "control")


@dataclass(frozen=True)
class BlindedCase:
    case_id: str
    chart_file: str
    cutoff_bar: int
    cutoff_timestamp_utc: str
    year: int
    stratum: str

    def public_record(self) -> dict[str, str]:
        return {"case_id": self.case_id, "chart_file": self.chart_file}

    def hidden_record(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "cutoff_bar": self.cutoff_bar,
            "cutoff_timestamp_utc": self.cutoff_timestamp_utc,
            "year": self.year,
            "stratum": self.stratum,
        }


def _utc_text(value) -> str:
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        raise ValueError("case timestamps must be timezone-aware")
    return stamp.tz_convert("UTC").isoformat()


def stable_rank(stratum: str, year: int, cutoff_timestamp) -> str:
    if stratum not in STRATA:
        raise ValueError(f"unsupported stratum: {stratum}")
    if int(year) not in YEARS:
        raise ValueError(f"unsupported year: {year}")
    text = f"v0648-reference-set|{stratum}|{int(year)}|{_utc_text(cutoff_timestamp)}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def blinded_case_id(cutoff_timestamp) -> str:
    text = f"v0648-case|{_utc_text(cutoff_timestamp)}"
    return "TW-" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16].upper()


def _candidate_nearby(candidate_cutoffs: set[int], cutoff: int) -> bool:
    start = max(0, int(cutoff) - CONTROL_EXCLUSION_BARS + 1)
    return any(i in candidate_cutoffs for i in range(start, int(cutoff) + 1))


def select_blinded_cases(
    frame: pd.DataFrame,
    candidate_confirmation_bars: Iterable[int],
) -> list[BlindedCase]:
    """Select exactly 20 candidate + 20 control cutoffs per year.

    Candidate membership is based only on the supplied frozen qualification
    confirmation bars. Control cutoffs exclude a candidate confirmation in the
    preceding 12 main-view bars. No direction/prediction/outcome enters here.
    """
    required = {"timestamp", "trading_day"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"frame missing required columns: {missing}")
    if len(frame) < LOOKBACK_BARS:
        raise ValueError("frame shorter than fixed annotation lookback")

    stamps = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
    if stamps.isna().any() or stamps.duplicated().any() or not stamps.is_monotonic_increasing:
        raise ValueError("timestamps must be ordered, unique and non-null")
    years = pd.to_datetime(frame["trading_day"], errors="raise").dt.year.astype(int)
    if set(years.unique()).difference(YEARS):
        raise ValueError("rows outside frozen 2015-2020 packet period")

    candidate_cutoffs = {int(x) for x in candidate_confirmation_bars}
    if any(x < 0 or x >= len(frame) for x in candidate_cutoffs):
        raise ValueError("candidate cutoff outside supplied frame")

    pools: dict[tuple[int, str], list[int]] = {}
    for year in YEARS:
        eligible_candidate = [
            i for i in sorted(candidate_cutoffs)
            if i >= LOOKBACK_BARS - 1 and int(years.iloc[i]) == year
        ]
        eligible_control = [
            i for i in range(LOOKBACK_BARS - 1, len(frame))
            if int(years.iloc[i]) == year
            and i not in candidate_cutoffs
            and not _candidate_nearby(candidate_cutoffs, i)
        ]
        pools[(year, "candidate")] = eligible_candidate
        pools[(year, "control")] = eligible_control

    selected: list[BlindedCase] = []
    seen_ids: set[str] = set()
    for year in YEARS:
        for stratum in STRATA:
            pool = pools[(year, stratum)]
            if len(pool) < CASES_PER_YEAR_PER_STRATUM:
                raise RuntimeError(
                    f"insufficient {year} {stratum} pool: {len(pool)} < {CASES_PER_YEAR_PER_STRATUM}"
                )
            ordered = sorted(pool, key=lambda i: stable_rank(stratum, year, stamps.iloc[i]))
            for cutoff in ordered[:CASES_PER_YEAR_PER_STRATUM]:
                case_id = blinded_case_id(stamps.iloc[cutoff])
                if case_id in seen_ids:
                    raise AssertionError("blinded case-id collision")
                seen_ids.add(case_id)
                selected.append(
                    BlindedCase(
                        case_id=case_id,
                        chart_file=f"cases/{case_id}.png",
                        cutoff_bar=int(cutoff),
                        cutoff_timestamp_utc=_utc_text(stamps.iloc[cutoff]),
                        year=year,
                        stratum=stratum,
                    )
                )

    if len(selected) != len(YEARS) * len(STRATA) * CASES_PER_YEAR_PER_STRATUM:
        raise AssertionError("frozen packet size drift")
    return sorted(selected, key=lambda x: x.case_id)


def sampling_commitment(cases: Sequence[BlindedCase]) -> str:
    hidden = [case.hidden_record() for case in sorted(cases, key=lambda x: x.case_id)]
    payload = json.dumps(hidden, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def public_manifest(cases: Sequence[BlindedCase]) -> list[dict[str, str]]:
    return [case.public_record() for case in sorted(cases, key=lambda x: x.case_id)]
