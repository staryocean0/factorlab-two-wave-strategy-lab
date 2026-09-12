from types import SimpleNamespace

from factor_lab.visual_structure.two_wave.semantic_bridge_counteroffensive_v0700 import (
    frozen_decision,
    human_support_cells,
    infer_human_kinds,
    summarize_cases,
)


def test_human_support_cells_are_ordered_and_cover_anchors():
    h = [10, 20, 30, 40, 50]
    cells = human_support_cells(h, 0, 95)
    assert len(cells) == 5
    for anchor, (lo, hi) in zip(h, cells):
        assert lo <= anchor <= hi
    assert all(a[1] < b[0] for a, b in zip(cells, cells[1:]))


def test_infer_human_kinds_from_price_sequence():
    closes = [100.0] * 100
    for i, v in zip([10, 20, 30, 40, 50], [1, 3, 2, 4, 1.5]):
        closes[i] = v
    assert infer_human_kinds([10, 20, 30, 40, 50], closes) == ["low", "high", "low", "high", "low"]


def _row(layers):
    return {
        **{f"L{i}": layers[i] for i in range(6)},
        "raw_anchor_exact": [True] * 5,
        "L4_hits": [layers[4]] * 5,
        "L5_hits": [layers[5]] * 5,
        "common_scale_level_count": 1 if layers[1] else 0,
        "exact_tuple_match_count": 1 if layers[2] else 0,
        "tuple_birth_match_count": 1 if layers[3] else 0,
        "nearest_common_scale_ridge_distance": [0, 0, 0, 0, 0] if layers[1] else [None] * 5,
    }


def test_frozen_decision_localizes_exact_tuple_break():
    rows = [_row([True, True, False, False, False, False]) for _ in range(11)]
    out = frozen_decision(summarize_cases(rows))
    assert out["primary_category"] == "v0700_ridge_infrastructure_salvage_supported_exact_tuple_objectization_breaks_semantic_bridge"
    assert out["component_retention_map"]["tcss_extrema_ridge_infrastructure"].startswith("retain")
    assert out["component_retention_map"]["exact_ridge_five_tuple_objectization"] == "requires_reconstruction_or_revalidation"


def test_frozen_decision_preserves_projection_when_eight_cases_pass():
    rows = [_row([True] * 6) for _ in range(8)] + [_row([True, True, True, True, True, False]) for _ in range(3)]
    out = frozen_decision(summarize_cases(rows))
    assert out["primary_category"] == "v0700_structural_identity_and_projection_salvaged_semantic_completion_or_qualification_bridge_remains"


def test_frozen_decision_localizes_raw_projection_when_filtered_passes_raw_fails():
    rows = [_row([True, True, True, True, True, False]) for _ in range(11)]
    out = frozen_decision(summarize_cases(rows))
    assert out["primary_category"] == "v0700_filtered_identity_salvaged_raw_projection_breaks_semantic_bridge"
