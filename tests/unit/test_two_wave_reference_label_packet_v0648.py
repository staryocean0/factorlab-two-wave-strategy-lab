import pandas as pd
import pytest

from factor_lab.visual_structure.two_wave.reference_label_packet_v0648 import (
    CASES_PER_YEAR_PER_STRATUM,
    CONTROL_EXCLUSION_BARS,
    LOOKBACK_BARS,
    YEARS,
    blinded_case_id,
    public_manifest,
    sampling_commitment,
    select_blinded_cases,
    stable_rank,
)


def _frame():
    # 300 bars/year is ample for the frozen 20+20 sample in this synthetic unit test.
    rows = []
    for year in YEARS:
        start = pd.Timestamp(f"{year}-01-05 09:31", tz="Asia/Shanghai").tz_convert("UTC")
        for i in range(300):
            rows.append({
                "timestamp": start + pd.Timedelta(minutes=5 * i),
                "trading_day": f"{year}-01-05",
            })
    return pd.DataFrame(rows)


def _candidate_cutoffs():
    # Put candidates well beyond each year's first 96 bars and sufficiently sparse
    # that controls remain abundant.
    out = []
    for year_index, _ in enumerate(YEARS):
        base = year_index * 300
        out.extend(base + 100 + 4 * i for i in range(35))
    return out


def test_frozen_packet_has_exact_year_stratum_counts_and_blinded_public_surface():
    frame = _frame()
    candidates = _candidate_cutoffs()
    cases = select_blinded_cases(frame, candidates)
    assert len(cases) == len(YEARS) * 2 * CASES_PER_YEAR_PER_STRATUM
    for year in YEARS:
        assert sum(c.year == year and c.stratum == "candidate" for c in cases) == CASES_PER_YEAR_PER_STRATUM
        assert sum(c.year == year and c.stratum == "control" for c in cases) == CASES_PER_YEAR_PER_STRATUM

    public = public_manifest(cases)
    assert set(public[0]) == {"case_id", "chart_file"}
    public_text = str(public).lower()
    for forbidden in ("candidate", "control", "year", "timestamp", "direction", "qualified"):
        assert forbidden not in public_text


def test_controls_exclude_candidate_confirmation_in_preceding_frozen_window():
    frame = _frame()
    candidate_set = set(_candidate_cutoffs())
    cases = select_blinded_cases(frame, candidate_set)
    for case in cases:
        assert case.cutoff_bar >= LOOKBACK_BARS - 1
        if case.stratum == "control":
            start = max(0, case.cutoff_bar - CONTROL_EXCLUSION_BARS + 1)
            assert not any(i in candidate_set for i in range(start, case.cutoff_bar + 1))


def test_sampling_and_case_ids_are_deterministic_but_stratum_changes_rank():
    stamp = pd.Timestamp("2018-06-01 10:30", tz="Asia/Shanghai").tz_convert("UTC")
    assert blinded_case_id(stamp) == blinded_case_id(stamp)
    assert stable_rank("candidate", 2018, stamp) != stable_rank("control", 2018, stamp)

    frame = _frame()
    first = select_blinded_cases(frame, _candidate_cutoffs())
    second = select_blinded_cases(frame, _candidate_cutoffs())
    assert [x.hidden_record() for x in first] == [x.hidden_record() for x in second]
    assert sampling_commitment(first) == sampling_commitment(second)


def test_invalid_inputs_fail_closed():
    frame = _frame()
    with pytest.raises(ValueError):
        stable_rank("unknown", 2018, frame.iloc[100]["timestamp"])
    with pytest.raises(ValueError):
        select_blinded_cases(frame.iloc[:50], [])
    with pytest.raises(ValueError):
        select_blinded_cases(frame, [-1])
