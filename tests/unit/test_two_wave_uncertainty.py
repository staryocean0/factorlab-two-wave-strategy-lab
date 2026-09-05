"""Synthetic implementation tests; these fixtures are never market references."""

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import pytest

from factor_lab.visual_structure.two_wave.annotations import SCHEMA_VERSION, evaluate_annotations
from factor_lab.visual_structure.two_wave.models import Config
from factor_lab.visual_structure.two_wave.uncertainty import (
    RESAMPLES,
    build_calendar_blocks,
    evaluate_block_bootstrap,
    shared_block_weights,
)


def calendar_window(identity, start, end, product="product", scale="scale"):
    return {"window_id": identity, "product_id": product, "scale_id": scale, "start_time": start, "end_time": end}


def fixture_run(product="product", count=6, mode="offline"):
    bars, references, windows, structures = [], [], [], []
    for i in range(count):
        stamp = datetime(2015, 1, 5, 1, 35, tzinfo=UTC) + timedelta(days=i * 3)
        for j in range(10):
            bars.append({"timestamp": (stamp + timedelta(minutes=j * 5)).isoformat()})
        start = i * 10
        points = [start + p for p in (0, 2, 4, 6, 8)]
        label = ("range", "uptrend", "downtrend")[i % 3]
        references.append({
            "annotation_id": f"a{i}", "kind": "structure", "phase": "low", "pivot_indices": points,
            "visible_cutoff": start + 9, "label": label,
        })
        structures.append({
            "structure_id": f"s{i}", "phase": "low", "pivot_indices": list(points),
            "confirmation_bar": start + 9, "classification": label if i % 2 == 0 else "uncertain",
        })
        windows.append({"start_index": start, "end_index": start + 9, "visible_cutoff": start + 9, "fully_reviewed": True})
    return {
        "product_id": product, "bars": bars,
        "export": {"config_hash": product, "config": {"timeframe": product}, "scale_id": "scale", "structures": structures},
        "annotations": {
            "schema_version": SCHEMA_VERSION, "reviewer": "human_a", "reference_mode": mode,
            "config_id": product, "timeframe": product, "scale_id": "scale", "annotations": references, "review_windows": windows,
        },
    }


def test_transitive_overlap_merges_across_products_and_year_boundary():
    plan = build_calendar_blocks([
        calendar_window("a", "2015-12-28", "2015-12-31", "5m"),
        calendar_window("b", "2015-12-31", "2016-01-03", "15m"),
        calendar_window("c", "2016-01-03", "2016-01-06", "60m"),
        calendar_window("d", "2016-01-08", "2016-01-09", "5m"),
    ])
    assert plan["block_count"] == 2
    assert len({plan["window_to_block"][key] for key in ("a", "b", "c")}) == 1
    assert plan["blocks"][0]["year_count"] == 2
    assert plan["blocks"][0]["product_count"] == 3


def test_shared_shanghai_calendar_date_even_when_utc_day_differs():
    plan = build_calendar_blocks([
        calendar_window("a", "2015-01-04T17:00:00+00:00", "2015-01-04T18:00:00+00:00"),
        calendar_window("b", "2015-01-05T04:00:00+00:00", "2015-01-05T06:00:00+00:00", "other"),
    ])
    assert plan["block_count"] == 1
    assert plan["blocks"][0]["start_day"] == "2015-01-05"
    with pytest.raises(ValueError, match="timezone-aware"):
        build_calendar_blocks([calendar_window("bad", "2015-01-05T01:00:00", "2015-01-05T06:00:00")])


def test_joint_signature_preserves_every_product_year_block_margin():
    windows = []
    for i in range(6):
        day = f"2015-01-{i * 3 + 1:02d}"
        windows.extend([calendar_window(f"a{i}", day, day, "a"), calendar_window(f"b{i}", day, day, "b")])
    # Additional product-only blocks are in a separate participation signature.
    windows.extend(calendar_window(f"solo{i}", f"2016-02-{i * 3 + 1:02d}", f"2016-02-{i * 3 + 1:02d}", "a") for i in range(6))
    plan = build_calendar_blocks(windows)
    weights, strata = shared_block_weights(plan["blocks"])
    assert weights.shape == (RESAMPLES, 12)
    assert len(strata) == 2
    assert np.array_equal(weights, shared_block_weights(plan["blocks"])[0])
    for product, year, expected in (("a", 2015, 6), ("b", 2015, 6), ("a", 2016, 6)):
        indices = [i for i, block in enumerate(plan["blocks"]) if any(p[0] == product and p[3] == year for p in block["participation"])]
        assert np.all(weights[:, indices].sum(axis=1) == expected)
    # Shared 2015 blocks have exactly one weight; no independent product draws.
    shared_a = [i for i, block in enumerate(plan["blocks"]) if any(p[0] == "a" and p[3] == 2015 for p in block["participation"])]
    shared_b = [i for i, block in enumerate(plan["blocks"]) if any(p[0] == "b" and p[3] == 2015 for p in block["participation"])]
    assert np.array_equal(weights[:, shared_a], weights[:, shared_b])


def test_independent_labels_are_required_and_modes_remain_separate():
    run = fixture_run()
    run["annotations"]["annotations"] = []
    run["annotations"]["review_windows"][0]["fully_reviewed"] = False
    result = evaluate_block_bootstrap([run])
    assert result["status"] == "morphology_replication_not_yet_accepted"
    for mode in result["modes"].values():
        assert all(value is None for value in mode["pooled"]["structure"]["confidence_intervals_95"].values())
    assert result["modes"]["offline"]["declared_window_plan"]["block_count"] == 6
    assert result["modes"]["offline"]["complete_reviewed_window_plan"]["block_count"] == 5
    assert result["modes"]["online"]["complete_reviewed_window_plan"]["block_count"] == 0


def test_small_number_of_blocks_does_not_get_false_precision():
    result = evaluate_block_bootstrap([fixture_run(count=2)])["modes"]["offline"]["pooled"]["structure"]
    assert result["point_estimates"]["precision"] == 1
    assert result["ci_status"] == "withheld"
    assert "sparse_joint_product_scale_year_participation_stratum" in result["ci_withheld_reasons"]
    assert all(value is None for value in result["confidence_intervals_95"].values())


def test_existing_matcher_point_metrics_and_full_bootstrap_are_reproducible():
    run = fixture_run()
    before = deepcopy(run)
    existing = evaluate_annotations(run["export"], run["annotations"])["modes"]["offline"]["structure"]
    first, second = evaluate_block_bootstrap([run]), evaluate_block_bootstrap([run])
    assert first == second
    assert run == before
    result = first["modes"]["offline"]["pooled"]["structure"]
    assert result["ci_status"] == "computed"
    assert result["confidence_intervals_95"]["precision"] == [1, 1]
    assert result["valid_resamples"]["macro_f1"] == RESAMPLES
    for key, value in result["point_estimates"].items():
        assert value == pytest.approx(existing[key])
    assert first["modes"]["offline"]["global_matching_equals_block_annual_count_sum"]
    assert result["accepted"] is False


def test_common_products_do_not_inflate_independent_block_count():
    result = evaluate_block_bootstrap([fixture_run("a"), fixture_run("b")])["modes"]["offline"]
    assert result["pooled"]["structure"]["counts"]["reference_observation_count"] == 12
    assert result["pooled"]["structure"]["calendar_block_count"] == 6
    assert result["sampling_strata"][0]["block_count"] == 6
    first, second = [row["kinds"]["structure"] for row in result["by_product_year"]]
    assert first["confidence_intervals_95"] == second["confidence_intervals_95"]


def test_online_confirmation_is_not_backfilled_and_no_offline_label_pooling():
    run = fixture_run(mode="online")
    run["export"]["structures"][0]["confirmation_bar"] = 10
    result = evaluate_block_bootstrap([run])["modes"]
    assert result["online"]["pooled"]["structure"]["counts"]["missed_count"] == 1
    assert result["offline"]["pooled"]["structure"]["counts"]["reference_observation_count"] == 0


def test_reference_duplication_requires_reconciliation():
    run = fixture_run()
    duplicate = dict(run["annotations"]["annotations"][0], annotation_id="duplicate")
    run["annotations"]["annotations"].append(duplicate)
    with pytest.raises(ValueError, match="Duplicate reference geometry"):
        evaluate_block_bootstrap([run])


@pytest.mark.parametrize("provenance", [
    {"source_type": "algorithm"}, {"source_type": "synthetic"},
    {"blinded_to_algorithm": False}, {"independent_of_other_reviewer": False},
])
@pytest.mark.parametrize("level", ["document", "reference", "window"])
def test_explicit_nonindependence_cannot_be_overridden_by_human_reviewer_name(provenance, level):
    run = fixture_run()
    target = run["annotations"]
    if level != "document":
        target = target["annotations" if level == "reference" else "review_windows"][0]
    target["provenance"] = provenance
    with pytest.raises(ValueError, match="nonindependent"):
        evaluate_block_bootstrap([run])


def test_unsupported_information_availability_clock_and_future_exposure_are_rejected():
    run = fixture_run(mode="online")
    run["annotations"]["provenance"] = {"online_clock": "information_available_time"}
    with pytest.raises(ValueError, match="Unsupported online_clock"):
        evaluate_block_bootstrap([run])
    run["annotations"]["provenance"] = {"future_exposed": True, "online_clock": "bar_end"}
    with pytest.raises(ValueError, match="future_exposed"):
        evaluate_block_bootstrap([run])


@pytest.mark.parametrize("changes", [{"fully_reviewed": "false"}, {"fully_reviewed": 1}, {"complete_reviewed": False}])
def test_incomplete_or_malformed_review_declarations_do_not_create_precision_scope(changes):
    run = fixture_run()
    run["annotations"]["review_windows"][0].update(changes)
    with pytest.raises(ValueError, match="review declarations"):
        evaluate_block_bootstrap([run])


def test_undefined_resample_denominators_are_not_dropped():
    run = fixture_run()
    run["export"]["structures"] = run["export"]["structures"][:1]
    result = evaluate_block_bootstrap([run])["modes"]["offline"]["pooled"]["structure"]
    assert result["point_estimates"]["precision"] == 1
    assert result["confidence_intervals_95"]["precision"] is None
    assert result["valid_resamples"]["precision"] < RESAMPLES
    assert result["confidence_intervals_95"]["recall"] is not None


def test_cross_block_matching_differences_withhold_interval_instead_of_redefining_match():
    run = fixture_run()
    # Move a prediction's final extremum into the next core while preserving the
    # frozen +/-2 tolerance. Global matching succeeds, block-local matching cannot.
    run["export"]["structures"][0]["pivot_indices"][-1] = 10
    result = evaluate_block_bootstrap([run])["modes"]["offline"]
    assert not result["global_matching_equals_block_annual_count_sum"]
    assert result["pooled"]["structure"]["point_estimates"]["recall"] == 1
    assert result["pooled"]["structure"]["confidence_intervals_95"]["recall"] is None
    assert "global_matching_not_additive_across_block_or_annual_boundaries" in result["pooled"]["structure"]["ci_withheld_reasons"]


def test_cli_loader_preserves_product_mapping_and_accepts_empty_reconciliation(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[2] / "scripts/evaluate_two_wave_reference_uncertainty.py"
    spec = spec_from_file_location("two_wave_reference_cli_test", path)
    cli = module_from_spec(spec)
    spec.loader.exec_module(cli)
    config = Config(timeframe="synthetic_product")
    run_dir = tmp_path / config.timeframe / "reversal_0.01"
    run_dir.mkdir(parents=True)
    metadata = {"config": config.to_dict(), "config_hash": config.config_hash, "scale_id": config.scale_id}
    (run_dir / "config.json").write_text(json.dumps(metadata))
    (run_dir / "summary.json").write_text(json.dumps({**metadata, "bars": 1, "pivots": 0, "cycles": 0, "structures": 0, "events": 0}))
    for kind in ("pivots", "cycles", "structures", "events"):
        (run_dir / f"{kind}.jsonl").write_text("")
    monkeypatch.setattr(cli, "load_development_bars", lambda *args, **kwargs: (
        [{"timestamp": "2015-01-05T01:35:00+00:00"}],
        {"view_id": config.timeframe, "export_frequency": "5m", "sha256": "synthetic_fixture"},
    ))
    annotation_path = tmp_path / "reference.json"
    doc = {"schema_version": SCHEMA_VERSION, "annotations": [], "review_windows": []}
    annotation_path.write_text(json.dumps({"schema_version": "two_wave_annotation_reconciliation@1.0", "adjudicated_reference": doc}))
    run, audit = cli.load_reference_run(run_dir, annotation_path, tmp_path, tmp_path / "manifest.json")
    assert run["product_id"] == "synthetic_product|actual_export_frequency=5m"
    assert audit["processed_bar_rows"] == 1
    assert evaluate_block_bootstrap([run])["modes"]["offline"]["pooled"]["structure"]["confidence_intervals_95"]["recall"] is None
    doc.update(config_id="foreign", timeframe="foreign_product", scale_id="foreign_scale")
    annotation_path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="different product/config/scale"):
        cli.load_reference_run(run_dir, annotation_path, tmp_path, tmp_path / "manifest.json")
