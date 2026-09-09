"""Isolated temporal two-wave grammar and append-only exclusive ownership.

No trading, future returns, centered smoothing or source-C1 mutation. See the
pre-result v0.4 protocol. Unknown tail ownership is explicitly provisional.
"""
from __future__ import annotations

import copy
import math
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime

import numpy as np

from .candidate_v02 import CandidateConfig, fit_geometry_v02
from .engine import Engine
from .models import Config, stable_id

SCHEMA = "two_wave_same_scale@0.4.0"


@dataclass(frozen=True)
class ScaleGrammar:
    reversal_run: int = 3
    min_leg: int = 4
    min_cycle: int = 12
    max_cycle: int = 48
    max_pair: int = 96
    max_unfinished_leg: int = 48
    max_period_ratio: float = 2.0
    max_corresponding_leg_ratio: float = 2.0
    max_amplitude_ratio: float = 2.0
    min_leg_er: float = .5
    max_step_share: float = .5
    max_flat_share: float = .5
    max_sessions: int = 3
    max_calendar_days: float = 7.0
    max_confirmation_delay: int = 8
    amplitude_floor: float = 1e-8
    drift: float = .5
    phase_step: float = .15
    opposite_step: float = .05

    def __post_init__(self):
        integers = ("reversal_run", "min_leg", "min_cycle", "max_cycle", "max_pair",
                    "max_unfinished_leg", "max_sessions", "max_confirmation_delay")
        for name, val in asdict(self).items():
            if isinstance(val, bool) or not isinstance(val, (float, int)) or not math.isfinite(val) or val <= 0:
                raise ValueError(f"{name} must be finite and positive")
            if name in integers and not isinstance(val, int):
                raise ValueError(f"{name} must be integer")
        if self.min_cycle < 2*self.min_leg or self.max_cycle < self.min_cycle or self.max_pair < 2*self.min_cycle:
            raise ValueError("inconsistent duration bounds")
        if min(self.max_period_ratio, self.max_corresponding_leg_ratio, self.max_amplitude_ratio) < 1:
            raise ValueError("ratios must be >= 1")
        if max(self.min_leg_er, self.max_step_share, self.max_flat_share) > 1:
            raise ValueError("shares cannot exceed one")
        if self.opposite_step >= self.phase_step:
            raise ValueError("opposite tolerance must be smaller than clear step")

    @property
    def config_hash(self):
        return stable_id("grammar", {"schema": SCHEMA, **asdict(self)})


def _ratio(a, b):
    return max(a, b)/min(a, b) if min(a, b) > 0 else None


def scale_audit(points: list[dict], bars: list[dict], confirmation_bar: int,
                config: ScaleGrammar | None = None) -> dict:
    """Eligibility of five actual pivots; no pivot is constructed by this fit."""
    c = config or ScaleGrammar()
    if len(points) != 5:
        raise ValueError("exactly five pivots required")
    idx = [p["occurrence_bar"] for p in points]
    if not all(isinstance(i, int) and not isinstance(i, bool) for i in idx):
        raise ValueError("integer occurrence positions required")
    if idx[0] < 0 or idx[-1] >= len(bars) or any(a >= b for a, b in zip(idx, idx[1:])):
        raise ValueError("ordered positions within available bars required")
    if any(p["kind"] not in ("high", "low") for p in points) or any(a["kind"] == b["kind"] for a, b in zip(points, points[1:])):
        raise ValueError("alternating high/low required")
    if confirmation_bar < idx[-1] or confirmation_bar >= len(bars):
        raise ValueError("confirmation outside available bars")
    if any(p["confirmation_bar"] > confirmation_bar or p["confirmation_bar"] < p["occurrence_bar"] for p in points):
        raise ValueError("all source pivots must already be confirmed")
    x = [float(p["log_price"]) for p in points]
    if not all(math.isfinite(v) for v in x):
        raise ValueError("finite prices required")
    if any(not math.isclose(x[j], bars[i]["log_close"], abs_tol=1e-10, rel_tol=0) for j, i in enumerate(idx)):
        raise ValueError("pivot prices do not match source closes")
    if any((x[j+1]-x[j]) * (1 if points[j]["kind"] == "low" else -1) <= 0 for j in range(4)):
        raise ValueError("pivots are not actual alternating price reversals")
    legs = np.diff(idx).tolist()
    periods = [idx[2]-idx[0], idx[4]-idx[2]]
    amplitudes = []
    for j in (0, 2):
        weight = (idx[j+1]-idx[j])/(idx[j+2]-idx[j])
        amplitudes.append(abs(x[j+1] - (x[j]*(1-weight)+x[j+2]*weight)))
    er, step, flat = [], [], []
    for a, b in zip(idx, idx[1:]):
        path = np.array([v["log_close"] for v in bars[a:b+1]], float)
        delta = np.abs(np.diff(path)); length = float(delta.sum())
        er.append(abs(float(path[-1]-path[0]))/length if length else 0.)
        step.append(float(delta.max())/length if length else 1.)
        flat.append(float(np.mean(delta <= 1e-12)))
    sessions = len({str(b.get("trading_day", b["timestamp"][:10]))[:10] for b in bars[idx[0]:idx[-1]+1]})
    wall_days = (datetime.fromisoformat(bars[idx[-1]]["timestamp"]) - datetime.fromisoformat(bars[idx[0]]["timestamp"])).total_seconds()/86400
    delay = confirmation_bar-idx[-1]
    ratios = [_ratio(legs[0], legs[2]), _ratio(legs[1], legs[3])]
    pr, ar = _ratio(*periods), _ratio(*amplitudes)
    tests = {
        "short_leg": min(legs) < c.min_leg,
        "cycle_duration": min(periods) < c.min_cycle or max(periods) > c.max_cycle,
        "pair_duration": idx[-1]-idx[0] > c.max_pair,
        "period_asymmetry": pr is None or pr > c.max_period_ratio,
        "leg_time_asymmetry": any(v is None or v > c.max_corresponding_leg_ratio for v in ratios),
        "amplitude_degenerate": min(amplitudes) <= c.amplitude_floor,
        "amplitude_asymmetry": ar is None or ar > c.max_amplitude_ratio,
        "internal_backtracking": min(er) < c.min_leg_er,
        "single_bar_dominance": max(step) > c.max_step_share,
        "long_exact_plateau": max(flat) > c.max_flat_share,
        "too_many_sessions": sessions > c.max_sessions,
        "calendar_span": wall_days > c.max_calendar_days,
        "late_confirmation": delay > c.max_confirmation_delay,
    }
    reasons = [k for k, v in tests.items() if v]
    return {"scale_eligible": not reasons, "scale_rejection_reasons": reasons,
            "leg_bars": legs, "cycle_bars": periods, "pair_bars": idx[-1]-idx[0],
            "period_ratio": pr, "corresponding_leg_ratios": ratios,
            "cycle_chord_amplitudes": amplitudes, "amplitude_ratio": ar,
            "leg_er": er, "single_step_path_shares": step, "exact_flat_shares": flat,
            "observed_sessions": sessions, "calendar_days": wall_days,
            "confirmation_delay_bars": delay, "grammar_hash": c.config_hash}


def phase_direction(points: list[dict], audit: dict, config: ScaleGrammar | None = None) -> dict:
    """A neutral third displacement need not veto two clear same-phase steps."""
    c = config or ScaleGrammar()
    width = float(np.mean(audit["cycle_chord_amplitudes"]))
    if width <= c.amplitude_floor:
        return {"direction": "uncertain", "direction_reasons": ["amplitude_degenerate"],
                "phase_steps": None, "net_drift": None}
    x = [p["log_price"] for p in points]
    steps = np.array([x[2]-x[0], x[4]-x[2], x[3]-x[1]])/width
    net = float((x[4]-x[0])/width)
    spans = [float(np.ptp(x[::2])/width), float(abs(x[3]-x[1])/width)]
    conflict = (steps[0]*steps[1] < 0 and min(abs(steps[0]), abs(steps[1])) > c.phase_step)
    majority = steps[0]+steps[1]
    conflict |= majority*steps[2] < 0 and min(abs(majority), abs(steps[2])) > c.phase_step
    label, reasons = "uncertain", []
    if abs(net) > c.drift:
        oriented = steps*(1 if net > 0 else -1)
        if min(oriented) >= -c.opposite_step and np.sum(oriented > c.phase_step) >= 2:
            label = "uptrend" if net > 0 else "downtrend"
        else:
            reasons.append("opposed_or_insufficient_phase_steps")
    elif max(spans) <= c.drift and not conflict:
        label = "range"
    else:
        reasons.append("mixed_or_large_phase_migration")
    return {"direction": label, "direction_reasons": reasons,
            "phase_steps": steps.tolist(), "net_drift": net,
            "phase_spans": spans, "phase_conflict": bool(conflict)}


class ExclusiveLedger:
    """First-confirmed full pair wins; uncertain direction gets equal treatment.

    Geometric bar ownership is (start,end], with an explicitly retrospective
    known_at. Only the unfinished tail can change when more data arrives.
    """
    def __init__(self):
        self.candidates: list[dict] = []
        self.segments: list[dict] = []
        self._end = 0
        self._last_confirmation = -1

    def offer(self, record: dict) -> dict:
        r = copy.deepcopy(record)
        if r["confirmation_bar"] < self._last_confirmation:
            raise ValueError("candidates must be offered in confirmation order")
        self._last_confirmation = r["confirmation_bar"]
        start, end = r["start_bar"]+1, r["end_bar"]+1
        if end <= start or end > r["confirmation_bar"]+1:
            raise ValueError("invalid complete occurrence interval")
        r["selected"] = bool(r["scale_eligible"] and start >= self._end)
        r["ownership_rejection"] = ("overlap_with_prior_published_pair" if r["scale_eligible"] and start < self._end else None)
        self.candidates.append(copy.deepcopy(r))
        if r["selected"]:
            self.segments.append({"start": start, "stop": end,
                "label": r["direction"], "record_id": r["record_id"],
                "anchor_bar": r["start_bar"], "known_at_bar": r["confirmation_bar"],
                "effective_information_time": r.get("effective_information_time"),
                "provisional": False, "retrospective_only": True})
            self._end = end
        return copy.deepcopy(r)

    def partition(self, n: int) -> list[dict]:
        if n < self._end:
            raise ValueError("partition cutoff is before published occurrences")
        out, pos = [], 0
        for s in self.segments:
            if s["known_at_bar"] >= n:
                raise ValueError("partition cutoff must include confirmation")
            if s["start"] > pos:
                out.append({"start": pos, "stop": s["start"], "label": "uncovered",
                            "known_at_bar": s["known_at_bar"], "provisional": False,
                            "retrospective_only": True})
            out.append(copy.deepcopy(s)); pos = s["stop"]
        if pos < n:
            out.append({"start": pos, "stop": n, "label": "pending_or_uncovered",
                        "known_at_bar": None, "provisional": True, "retrospective_only": True})
        return out


def gate_c1(record: dict, points: list[dict], bars: list[dict], config: ScaleGrammar | None = None) -> dict:
    a = scale_audit(points, bars, record["confirmation_bar"], config)
    return {**copy.deepcopy(record), **a, "schema_version": SCHEMA, "operator": "C2G",
            "record_id": stable_id("C2G", [record["direction_record_id"], a["grammar_hash"]]),
            "direction": record["direction_classification"], "source_C1_id": record["direction_record_id"],
            "five_occurrence_bars": [p["occurrence_bar"] for p in points], "trade_authority": False}


class TimeStructureEngine:
    """D0: raw extremes + three strict opposite closes, with stale-leg reset."""
    def __init__(self, timeframe: str = "5m_offset_0", config: ScaleGrammar | None = None):
        self.config = config or ScaleGrammar()
        self.timeframe = timeframe
        self.scale_id = stable_id("D0_scale", [timeframe, SCHEMA, self.config.config_hash])
        self._clock = Engine(Config(timeframe=timeframe))
        self.bars = self._clock.bars
        self.pivots: list[dict] = []
        self.resets: list[dict] = []
        self.ledger = ExclusiveLedger()
        self._chain: list[dict] = []
        self._direction: str | None = None
        self._candidate: dict | None = None
        self._seed: dict | None = None
        self._anchor = 0
        self._run = 0

    @property
    def records(self):
        return self.ledger.candidates

    def _point(self, bar: dict, kind: str) -> dict:
        return {"kind": kind, "occurrence_bar": bar["bar_index"],
                "occurrence_time": bar["timestamp"], "price": bar["close"],
                "log_price": bar["log_close"]}

    def update(self, supplied: dict) -> list[dict]:
        bar, dt, available = self._clock._normalize(supplied)
        if "trading_day" in supplied:
            bar["trading_day"] = supplied["trading_day"]
        self._clock._last_dt = dt
        self._clock._availability = max(self._clock._availability, available) if self._clock._availability else available
        self.bars.append(bar)
        t, x = bar["bar_index"], bar["log_close"]
        if self._seed is None or t-self._anchor > self.config.max_unfinished_leg:
            if self._seed is not None:
                self.resets.append({"bar": t, "reason": "stale_unfinished_leg",
                                    "last_anchor": self._anchor, "no_pivot_manufactured": True})
            self._seed, self._anchor = bar, t
            self._direction, self._candidate, self._run, self._chain = None, None, 0, []
            return []
        if self._direction is None:
            if x == self._seed["log_close"]:
                return []
            self._direction = "up" if x > self._seed["log_close"] else "down"
            p = self._point(self._seed, "low" if self._direction == "up" else "high")
            p.update({"left_censored": True, "confirmation_bar": t,
                      "confirmation_time": bar["timestamp"],
                      "effective_information_time": self._clock._availability.isoformat()})
            p["pivot_id"] = stable_id("D0_pivot", [self.scale_id, p])
            self.pivots.append(p)
            self._candidate = self._point(bar, "high" if self._direction == "up" else "low")
            return []
        sign = 1 if self._direction == "up" else -1
        if sign*(x-self._candidate["log_price"]) > 0:
            self._candidate = self._point(bar, self._candidate["kind"])
        change = x-self.bars[t-1]["log_close"]
        self._run = self._run+1 if sign*change < 0 else 0
        if self._run < self.config.reversal_run:
            return []
        p = copy.deepcopy(self._candidate)
        p.update({"left_censored": False, "confirmation_bar": t,
                  "confirmation_time": bar["timestamp"],
                  "effective_information_time": self._clock._availability.isoformat()})
        p["pivot_id"] = stable_id("D0_pivot", [self.scale_id, p])
        self.pivots.append(p); self._chain.append(p)
        self._anchor = p["occurrence_bar"]
        self._direction = "down" if sign == 1 else "up"
        after = self.bars[p["occurrence_bar"]+1:t+1]
        new = min(after, key=lambda b: sign*b["log_close"])
        self._candidate = self._point(new, "low" if sign == 1 else "high")
        self._run = 0
        if len(self._chain) < 5:
            return []
        pts = self._chain[-5:]
        # Consecutive confirmed extrema must be actual alternating price turns.
        if any((pts[j+1]["log_price"]-pts[j]["log_price"])*(1 if pts[j]["kind"] == "low" else -1) <= 0 for j in range(4)):
            raise ArithmeticError("D0 violated raw-turn ordering")
        audit = scale_audit(pts, self.bars, t, self.config)
        direction = phase_direction(pts, audit, self.config)
        g = fit_geometry_v02(pts, self.bars, CandidateConfig(timeframe=self.timeframe))
        r = {"schema_version": SCHEMA, "operator": "D0", "timeframe": self.timeframe,
             "scale_id": self.scale_id, "grammar_hash": self.config.config_hash,
             "start_bar": pts[0]["occurrence_bar"], "end_bar": pts[-1]["occurrence_bar"],
             "five_occurrence_bars": [q["occurrence_bar"] for q in pts],
             "pivot_ids": [q["pivot_id"] for q in pts],
             "cycle_ids": [stable_id("D0_cycle", [q["pivot_id"] for q in pts[i:i+3]]) for i in (0, 2)],
             "phase": pts[0]["kind"], "confirmation_bar": t,
             "confirmation_time": bar["timestamp"], "effective_information_time": self._clock._availability.isoformat(),
             "channel_classification_A": g["classification"],
             "channel_rejection_reasons_A": g["rejection_reasons"],
             "channel_accepted_by_A": g["valid"] and not g["rejection_reasons"],
             "D": g["D"], "E": g["E"], "geometry": g,
             "trade_authority": False, "human_reference": False, "future_outcome_used": False,
             **audit, **direction}
        r["record_id"] = stable_id("D0_pair", [self.scale_id, r["pivot_ids"]])
        return [self.ledger.offer(r)]


def summarize_ledger(ledger: ExclusiveLedger, n: int) -> dict:
    rows = ledger.candidates
    picked = [r for r in rows if r["selected"]]
    def quantiles(values):
        if not values:
            return None
        return dict(zip(("min", "p50", "p90", "max"), map(float, np.quantile(values, [0, .5, .9, 1]))))
    partition = ledger.partition(n)
    assert sum(s["stop"]-s["start"] for s in partition) == n
    assert all(a["stop"] == b["start"] for a, b in zip(partition, partition[1:]))
    return {"candidates": len(rows), "eligible_before_ownership": sum(r["scale_eligible"] for r in rows),
            "selected_pairs": len(picked), "direction_counts": dict(Counter(r["direction"] for r in picked)),
            "rejections": dict(Counter(k for r in rows for k in r["scale_rejection_reasons"])),
            "overlap_suppressed": sum(bool(r["ownership_rejection"]) for r in rows),
            "selected_span_bars": quantiles([r["pair_bars"] for r in picked]),
            "selected_delay_bars": quantiles([r["confirmation_delay_bars"] for r in picked]),
            "owned_bars": sum(r["end_bar"]-r["start_bar"] for r in picked),
            "total_bars": n, "full_partition_rows": len(partition),
            "max_published_ownership_multiplicity": 1 if picked else 0,
            "not_accuracy": True, "morphology_accepted": False}
