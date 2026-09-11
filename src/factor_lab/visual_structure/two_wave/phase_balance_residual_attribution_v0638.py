"""Read-only v0.6.38 attribution helpers for phase-balanced W1."""
from __future__ import annotations


def exact_pair(pair: tuple[str, str]) -> bool:
    return str(pair[0]) == str(pair[1])


def phase_balance_transition(v0635_pair: tuple[str, str], v0637_pair: tuple[str, str]) -> str:
    old_exact = exact_pair(v0635_pair)
    new_exact = exact_pair(v0637_pair)
    if old_exact and new_exact:
        return "both_exact"
    if not old_exact and new_exact:
        return "phase_balance_repaired_v0635_nonexact"
    if old_exact and not new_exact:
        return "phase_balance_harmed_v0635_exact"
    return "both_nonexact"


def semantic_class(v0625_pair: tuple[str, str], v0637_pair: tuple[str, str]) -> str:
    old_exact = exact_pair(v0625_pair)
    new_exact = exact_pair(v0637_pair)
    if old_exact and not new_exact:
        return "introduced_harm"
    if not old_exact and new_exact:
        return "repaired_old_nonexact"
    if not old_exact and not new_exact:
        return "persistent_nonexact"
    raise ValueError("one-sided changed pair unexpectedly remains exact under both versions")


def rescue_origin(v0625_label: str, v0635_label: str, v0637_label: str) -> str:
    old = str(v0625_label)
    plain = str(v0635_label)
    balanced = str(v0637_label)
    if old != "uncertain" or balanced != "range":
        raise ValueError("v0.6.37 changed side must be Uncertain -> Range")
    if plain == "range":
        return "shared_bar_equal_and_phase_balanced_rescue"
    if plain == "uncertain":
        return "phase_balanced_only_rescue"
    raise ValueError("v0.6.35 must preserve v0.6.25 decisive states")
