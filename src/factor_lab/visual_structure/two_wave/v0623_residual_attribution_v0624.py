"""Pure audit helpers for v0.6.24 residual direction attribution.

No recognizer rule is changed here.  These helpers classify pair-level changes
from D1 to v0.6.23 and summarize already-computed single-view rescue support.
"""
from __future__ import annotations

from typing import Mapping, Sequence

DECISIVE = frozenset({"range", "uptrend", "downtrend"})
VALID = DECISIVE | {"uncertain"}


def pair_transition_category(d1_main: str, d1_other: str, cand_main: str, cand_other: str) -> str:
    labels = (d1_main, d1_other, cand_main, cand_other)
    if any(str(x) not in VALID for x in labels):
        raise ValueError("unsupported direction label")
    d1_exact = d1_main == d1_other
    candidate_exact = cand_main == cand_other
    if d1_exact and candidate_exact:
        return "retained_exact"
    if d1_exact and not candidate_exact:
        return "introduced_harm"
    if not d1_exact and candidate_exact:
        return "repaired_old_nonexact"
    return "persistent_nonexact"


def rescue_topology(main_rescued: bool, other_rescued: bool) -> str:
    if main_rescued and other_rescued:
        return "both_rescued"
    if main_rescued:
        return "main_only_rescued"
    if other_rescued:
        return "other_only_rescued"
    return "neither_rescued"


def d1_pair_topology(main_label: str, other_label: str) -> str:
    if main_label not in VALID or other_label not in VALID:
        raise ValueError("unsupported D1 label")
    mu = main_label == "uncertain"
    ou = other_label == "uncertain"
    if mu and ou:
        return "both_uncertain"
    if mu:
        return "main_uncertain_other_decisive"
    if ou:
        return "main_decisive_other_uncertain"
    return "both_decisive"


def consensus_margin_and_span(
    support_states: Mapping[str, str],
    support_scores: Mapping[str, float],
    consensus_state: str,
) -> dict:
    state = str(consensus_state)
    if state not in DECISIVE:
        raise ValueError("decisive consensus state required")
    if not support_states or set(map(str, support_states.values())) != {state}:
        raise ValueError("all support states must equal consensus state")
    if set(support_states) != set(support_scores):
        raise ValueError("support state/score keys must match")
    scores = [float(support_scores[k]) for k in support_states]
    if state == "uptrend":
        margin = min(scores) - 0.50
    elif state == "downtrend":
        margin = -0.50 - max(scores)
    else:
        margin = 0.15 - max(abs(x) for x in scores)
    if margin < -1e-12:
        raise ValueError("consensus score is inconsistent with frozen state boundary")
    return {
        "consensus_margin_to_frozen_boundary": max(0.0, margin),
        "support_score_span": max(scores) - min(scores),
    }
