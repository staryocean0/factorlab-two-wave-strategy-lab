"""v0.4.4 hierarchical candidate-construction ablation.

The frozen v0.4.3 TemporalMaturityEngine is used verbatim for local pivots.
This module only coarse-grains those confirmed local extrema into parent cycles
using the already-frozen min_cycle/max_cycle time grammar. Pair qualification,
D1 direction, information clocks and ExclusiveLedger publishing remain frozen.
No H16 structural threshold, future outcome, or trading logic is introduced.
"""
from __future__ import annotations

import copy
from collections import Counter

from .models import stable_id
from .same_scale_v04 import ExclusiveLedger, evaluate_pair
from .same_scale_v043 import MaturityConfig, TemporalMaturityEngine

SCHEMA = "two_wave_same_scale@0.4.4-hierarchical-candidate-ablation"
HIERARCHY_MODE = "first_admissible_same_phase_return_extreme_opposite"
H16_ROLE = "diagnostic_only_not_structural_gate"


class HierarchicalCycleEngine:
    """Causal parent-cycle builder over frozen v0.4.3 local pivots.

    For one active same-phase anchor A, same-phase returns before min_cycle are
    audited as subscale and ignored without re-anchoring. The first same-phase
    return C in [min_cycle, max_cycle] closes a parent cycle. Its middle point B
    is the most extreme already-confirmed opposite local pivot between A and C.
    All non-promoted local extrema retain explicit skip reasons.
    """

    def __init__(self, config=None):
        self.shape_config = config or MaturityConfig()
        self.local = TemporalMaturityEngine(self.shape_config)
        self.ledger = ExclusiveLedger()

        self.parent_pivots = []
        self.parent_cycles = []
        self.skipped_local_pivots = []
        self.hierarchy_resets = []

        self._active_anchor = None
        self._active_opposite = None
        self._active_pending = []
        self._active_parent_chain = []
        self._processed_local_pivots = 0
        self._processed_local_resets = 0
        self._skip_ids = set()
        self._promoted_ids = set()
        self._parent_by_local_id = {}

    @property
    def bars(self):
        return self.local.bars

    @property
    def local_pivots(self):
        return self.local.pivots

    @property
    def pivots(self):
        """Compatibility alias: v0.4.4 pivots are promoted parent pivots."""
        return self.parent_pivots

    @property
    def resets(self):
        """Frozen local reset stream, unchanged from v0.4.3."""
        return self.local.resets

    @property
    def pending_local_pivots(self):
        out = []
        for p in self._active_pending:
            if p["pivot_id"] not in self._promoted_ids and p["pivot_id"] not in self._skip_ids:
                out.append({
                    "source_local_pivot_id": p["pivot_id"],
                    "occurrence_bar": p["occurrence_bar"],
                    "local_confirmation_bar": p["confirmation_bar"],
                    "epoch": p["epoch"],
                    "reason": "provisional_parent_tail_not_decided",
                })
        return out

    @property
    def hierarchy_config_hash(self):
        return stable_id("hierarchy_cfg_v044", {
            "schema": SCHEMA,
            "mode": HIERARCHY_MODE,
            "underlying_v043_config_hash": self.shape_config.config_hash,
            "min_cycle_source": "MaturityConfig.min_cycle",
            "max_cycle_source": "MaturityConfig.max_cycle",
            "h16_role": H16_ROLE,
        })

    def _is_more_extreme(self, point, retained):
        if retained is None:
            return True
        if point["kind"] == "high":
            return point["price"] > retained["price"]
        return point["price"] < retained["price"]

    def _skip(self, point, reason, decision_point=None, **details):
        pid = point["pivot_id"]
        if pid in self._promoted_ids or pid in self._skip_ids:
            return
        trigger = decision_point or point
        row = {
            "source_local_pivot_id": pid,
            "kind": point["kind"],
            "occurrence_bar": point["occurrence_bar"],
            "occurrence_time": point["occurrence_time"],
            "price": point["price"],
            "local_confirmation_bar": point["confirmation_bar"],
            "local_confirmation_time": point["confirmation_time"],
            "decision_confirmation_bar": trigger["confirmation_bar"],
            "decision_confirmation_time": trigger["confirmation_time"],
            "decision_effective_information_time": trigger["effective_information_time"],
            "epoch": point["epoch"],
            "reason": reason,
            "hierarchy_mode": HIERARCHY_MODE,
            **details,
        }
        self.skipped_local_pivots.append(row)
        self._skip_ids.add(pid)

    def _promote(self, local_point, close_point, role):
        pid = local_point["pivot_id"]
        if pid in self._parent_by_local_id:
            return self._parent_by_local_id[pid]
        if pid in self._skip_ids:
            raise ValueError("a skipped local pivot cannot later be promoted")
        parent = {
            "kind": local_point["kind"],
            "occurrence_bar": local_point["occurrence_bar"],
            "occurrence_time": local_point["occurrence_time"],
            "price": local_point["price"],
            "log_price": local_point["log_price"],
            "left_censored": False,
            "confirmation_bar": close_point["confirmation_bar"],
            "confirmation_time": close_point["confirmation_time"],
            "effective_information_time": close_point["effective_information_time"],
            "confirmation_delay_bars": close_point["confirmation_bar"] - local_point["occurrence_bar"],
            "bar_end_assumed": bool(local_point.get("bar_end_assumed", False) or close_point.get("bar_end_assumed", False)),
            "epoch": local_point["epoch"],
            "confirmation_mode": "v043_local_then_parent_cycle_close",
            "source_local_pivot_id": pid,
            "local_confirmation_bar": local_point["confirmation_bar"],
            "local_confirmation_time": local_point["confirmation_time"],
            "local_effective_information_time": local_point["effective_information_time"],
            "parent_promotion_trigger_local_pivot_id": close_point["pivot_id"],
            "parent_role_at_first_promotion": role,
            "hierarchy_mode": HIERARCHY_MODE,
        }
        parent["pivot_id"] = stable_id("parent_pivot_v044", [
            self.hierarchy_config_hash, pid, close_point["pivot_id"], role,
        ])
        self.parent_pivots.append(copy.deepcopy(parent))
        self._promoted_ids.add(pid)
        self._parent_by_local_id[pid] = copy.deepcopy(parent)
        return copy.deepcopy(parent)

    def _flush_pending(self, reason, decision_point, exclude_ids=()):
        excluded = set(exclude_ids)
        for p in self._active_pending:
            if p["pivot_id"] not in excluded:
                self._skip(
                    p, reason, decision_point,
                    active_anchor_local_pivot_id=self._active_anchor["pivot_id"] if self._active_anchor else None,
                )

    def _break_parent_chain(self, reason, decision_point):
        self._flush_pending(reason, decision_point, exclude_ids=(decision_point["pivot_id"],))
        self.hierarchy_resets.append({
            "bar": decision_point["confirmation_bar"],
            "time": decision_point["confirmation_time"],
            "known_at": decision_point["effective_information_time"],
            "reason": reason,
            "previous_anchor_local_pivot_id": self._active_anchor["pivot_id"] if self._active_anchor else None,
            "new_anchor_local_pivot_id": decision_point["pivot_id"],
            "epoch": decision_point["epoch"],
        })
        self._active_anchor = decision_point
        self._active_opposite = None
        self._active_pending = [decision_point]
        self._active_parent_chain = []

    def _close_parent_cycle(self, endpoint):
        anchor = self._active_anchor
        opposite = self._active_opposite
        if anchor is None or opposite is None:
            raise ValueError("parent cycle closure requires anchor and opposite extremum")
        if not (anchor["occurrence_bar"] < opposite["occurrence_bar"] < endpoint["occurrence_bar"]):
            raise ValueError("parent cycle members must be occurrence ordered")
        if anchor["kind"] != endpoint["kind"] or anchor["kind"] == opposite["kind"]:
            raise ValueError("parent cycle must alternate phase")
        duration = endpoint["occurrence_bar"] - anchor["occurrence_bar"]
        if not self.shape_config.min_cycle <= duration <= self.shape_config.max_cycle:
            raise ValueError("parent cycle duration outside frozen time grammar")

        if self._active_parent_chain:
            promoted_anchor = self._active_parent_chain[-1]
            if promoted_anchor["source_local_pivot_id"] != anchor["pivot_id"]:
                raise ValueError("active parent chain anchor lineage mismatch")
        else:
            promoted_anchor = self._promote(anchor, endpoint, "cycle_anchor")
            self._active_parent_chain = [promoted_anchor]

        promoted_mid = self._promote(opposite, endpoint, "cycle_middle")
        promoted_end = self._promote(endpoint, endpoint, "cycle_endpoint")
        self._active_parent_chain.extend([promoted_mid, promoted_end])

        selected_ids = {anchor["pivot_id"], opposite["pivot_id"], endpoint["pivot_id"]}
        collapsed_ids = []
        for p in self._active_pending:
            if p["pivot_id"] not in selected_ids:
                collapsed_ids.append(p["pivot_id"])
                self._skip(
                    p, "subscale_local_extremum_not_promoted_on_parent_close", endpoint,
                    parent_anchor_local_pivot_id=anchor["pivot_id"],
                    parent_middle_local_pivot_id=opposite["pivot_id"],
                    parent_endpoint_local_pivot_id=endpoint["pivot_id"],
                )

        cycle = {
            "cycle_id": stable_id("parent_cycle_v044", [
                self.hierarchy_config_hash,
                promoted_anchor["pivot_id"], promoted_mid["pivot_id"], promoted_end["pivot_id"],
            ]),
            "hierarchy_mode": HIERARCHY_MODE,
            "epoch": endpoint["epoch"],
            "parent_pivot_ids": [
                promoted_anchor["pivot_id"], promoted_mid["pivot_id"], promoted_end["pivot_id"],
            ],
            "source_local_pivot_ids": [anchor["pivot_id"], opposite["pivot_id"], endpoint["pivot_id"]],
            "occurrence_bars": [
                anchor["occurrence_bar"], opposite["occurrence_bar"], endpoint["occurrence_bar"],
            ],
            "duration_bars": duration,
            "confirmation_bar": endpoint["confirmation_bar"],
            "confirmation_time": endpoint["confirmation_time"],
            "effective_information_time": endpoint["effective_information_time"],
            "collapsed_local_pivot_ids": collapsed_ids,
            "collapsed_local_pivot_count": len(collapsed_ids),
        }
        self.parent_cycles.append(copy.deepcopy(cycle))

        if len(self._active_parent_chain) >= 5:
            points = self._active_parent_chain[-5:]
            record = evaluate_pair(points, self.bars, self.shape_config)
            record["schema_version"] = SCHEMA
            record["candidate_constructor"] = HIERARCHY_MODE
            record["hierarchy_config_hash"] = self.hierarchy_config_hash
            record["local_confirmation_kernel"] = self.shape_config.confirmation_mode
            record["source_local_pivot_ids"] = [p["source_local_pivot_id"] for p in points]
            record["source_parent_cycle_ids"] = [c["cycle_id"] for c in self.parent_cycles[-2:]]
            record["collapsed_local_pivots_in_two_cycles"] = sum(
                c["collapsed_local_pivot_count"] for c in self.parent_cycles[-2:]
            )
            self.ledger.add(record)

        self._active_anchor = endpoint
        self._active_opposite = None
        self._active_pending = [endpoint]

    def _consume_local_pivot(self, point):
        if point["left_censored"]:
            self._skip(point, "left_censored_local_pivot_excluded", point)
            return
        if self._active_anchor is None:
            self._active_anchor = point
            self._active_opposite = None
            self._active_pending = [point]
            self._active_parent_chain = []
            return
        if point["epoch"] != self._active_anchor["epoch"]:
            self._flush_pending("local_epoch_changed_before_parent_close", point)
            self._active_anchor = point
            self._active_opposite = None
            self._active_pending = [point]
            self._active_parent_chain = []
            return

        self._active_pending.append(point)
        if point["kind"] != self._active_anchor["kind"]:
            if self._is_more_extreme(point, self._active_opposite):
                if self._active_opposite is not None:
                    self._skip(
                        self._active_opposite,
                        "opposite_extreme_replaced_before_parent_close",
                        point,
                        replaced_by_local_pivot_id=point["pivot_id"],
                    )
                self._active_opposite = point
            else:
                self._skip(
                    point,
                    "non_extreme_opposite_subscale",
                    point,
                    retained_opposite_local_pivot_id=self._active_opposite["pivot_id"],
                )
            return

        span = point["occurrence_bar"] - self._active_anchor["occurrence_bar"]
        if span < self.shape_config.min_cycle:
            self._skip(
                point,
                "same_phase_return_before_min_cycle",
                point,
                active_anchor_local_pivot_id=self._active_anchor["pivot_id"],
                span_bars=span,
                min_cycle=self.shape_config.min_cycle,
            )
            return
        if span > self.shape_config.max_cycle:
            self._break_parent_chain("parent_cycle_exceeded_max_cycle", point)
            return
        if self._active_opposite is None:
            self._break_parent_chain("same_phase_return_without_opposite", point)
            return
        self._close_parent_cycle(point)

    def _consume_new_local_resets(self):
        for reset in self.local.resets[self._processed_local_resets:]:
            if self._active_pending:
                decision = {
                    **self._active_pending[-1],
                    "confirmation_bar": reset["bar"],
                    "confirmation_time": reset["time"],
                    "effective_information_time": reset["known_at"],
                }
                self._flush_pending("local_epoch_reset_before_parent_close", decision)
            self.hierarchy_resets.append({
                "bar": reset["bar"],
                "time": reset["time"],
                "known_at": reset["known_at"],
                "reason": "local_v043_epoch_reset",
                "previous_anchor_local_pivot_id": self._active_anchor["pivot_id"] if self._active_anchor else None,
                "new_anchor_local_pivot_id": None,
                "epoch": None,
            })
            self._active_anchor = None
            self._active_opposite = None
            self._active_pending = []
            self._active_parent_chain = []
        self._processed_local_resets = len(self.local.resets)

    def update(self, supplied):
        before = len(self.ledger.records)
        self.local.update(supplied)
        self._consume_new_local_resets()
        for point in self.local.pivots[self._processed_local_pivots:]:
            self._consume_local_pivot(copy.deepcopy(point))
        self._processed_local_pivots = len(self.local.pivots)
        return copy.deepcopy(self.ledger.records[before:])


def hierarchy_reason_counts(engine):
    """Small audit helper used by the runner without changing research logic."""
    return dict(Counter(row["reason"] for row in engine.skipped_local_pivots))
