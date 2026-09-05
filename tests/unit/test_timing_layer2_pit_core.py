# pyright: reportAny=false, reportArgumentType=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.core_kline_attribute_pool import (
    NEW_CORE_NUMERIC_COLUMNS,
    _rolling_direction_metrics,
    _signed_efficiency,
    _signed_ols_t,
    annual_core_extensions,
)
from factor_lab.market_state.lat_kline_attribute_atlas import (
    _rolling_efficiency,
    _rolling_trend,
)
from factor_lab.market_state.timing_layer2_pit_core import (
    PIT_HORIZON_COLUMNS,
    PITCoreBinding,
    build_pit_core_measurements,
    reduce_pit_core_geometry_and_direction_by_year,
)


def _bars(rows: int = 260) -> pd.DataFrame:
    index = np.arange(rows, dtype=float)
    log_close = 4.5 + 0.001 * index + 0.015 * np.sin(index / 9.0)
    close = np.exp(log_close)
    timestamp = pd.bdate_range("2020-01-02", periods=rows, tz="Asia/Shanghai") + pd.Timedelta(hours=15)
    open_ = close * np.exp(0.001 * np.sin(index / 5.0))
    high = np.maximum(open_, close) * 1.004
    low = np.minimum(open_, close) * 0.996
    return pd.DataFrame(
        {
            "timestamp": timestamp,
            "trading_day": timestamp.strftime("%Y-%m-%d"),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
        }
    )


def _binding() -> PITCoreBinding:
    return PITCoreBinding(
        carrier_id="000852.SH",
        view_id="daily_proxy_close_1430",
        bars_per_day=1,
        source_id="datahub_history_bars",
        source_version="cn_a_session_wall_clock_offset_v1",
        source_receipt_sha256="b" * 64,
    )


def test_pointwise_provider_reuses_every_frozen_horizon_formula_exactly() -> None:
    bars = _bars()
    result = build_pit_core_measurements(bars, binding=_binding())
    log_close = np.log(bars["close"].to_numpy(float))
    returns = np.diff(log_close)

    for days in (2, 4, 8, 16):
        expected_efficiency = _rolling_efficiency(log_close, days)
        expected_t_abs, expected_r2 = _rolling_trend(log_close, days)
        expected_signed_efficiency = _signed_efficiency(log_close, days)
        expected_signed_t = _signed_ols_t(log_close, days)
        expected_direction = _rolling_direction_metrics(returns, days)
        np.testing.assert_allclose(
            result[f"efficiency_ratio_{days}d"].iloc[days:],
            expected_efficiency,
            rtol=0.0,
            atol=0.0,
        )
        np.testing.assert_allclose(
            result[f"ols_slope_t_abs_{days}d"].iloc[days - 1 :],
            expected_t_abs,
            rtol=0.0,
            atol=0.0,
        )
        np.testing.assert_allclose(
            result[f"ols_r2_{days}d"].iloc[days - 1 :],
            expected_r2,
            rtol=0.0,
            atol=0.0,
        )
        np.testing.assert_allclose(
            result[f"signed_efficiency_ratio_{days}d"].iloc[days:],
            expected_signed_efficiency,
            rtol=0.0,
            atol=0.0,
        )
        if days == 2:
            assert len(expected_signed_t) == 0
            assert result[f"ols_slope_t_signed_{days}d"].isna().all()
        else:
            np.testing.assert_allclose(
                result[f"ols_slope_t_signed_{days}d"].iloc[days - 1 :],
                expected_signed_t,
                rtol=0.0,
                atol=0.0,
            )
        for source, prefix in (
            ("bdci", "bdci_score"),
            ("bci", "bci_imbalance"),
            ("wbi", "wbi_score"),
            ("dii", "dii_score"),
        ):
            np.testing.assert_allclose(
                result[f"{prefix}_{days}d"].iloc[days:],
                expected_direction[source],
                rtol=0.0,
                atol=0.0,
            )
    assert set(PIT_HORIZON_COLUMNS).issubset(result.columns)


def test_annual_reducer_matches_30_existing_core_extension_fields_exactly() -> None:
    bars = _bars()
    measurements = build_pit_core_measurements(bars, binding=_binding())
    reduced = reduce_pit_core_geometry_and_direction_by_year(measurements)
    expected = annual_core_extensions(
        bars,
        carrier="000852.SH",
        years=(2020,),
        bars_per_day=1,
    )
    comparable = tuple(NEW_CORE_NUMERIC_COLUMNS[:-2])
    assert len(comparable) == 30
    np.testing.assert_allclose(
        reduced.loc[0, list(comparable)].to_numpy(float),
        expected.loc[0, list(comparable)].to_numpy(float),
        rtol=0.0,
        atol=1e-15,
    )


def test_prefix_invariance_and_continuity_segment_reset() -> None:
    bars = _bars()
    full = build_pit_core_measurements(bars, binding=_binding())
    prefix = build_pit_core_measurements(bars.iloc[:180], binding=_binding())
    pd.testing.assert_frame_equal(
        full.loc[:179, list(PIT_HORIZON_COLUMNS)].reset_index(drop=True),
        prefix[list(PIT_HORIZON_COLUMNS)].reset_index(drop=True),
    )

    segmented = bars.copy()
    segmented["continuity_segment_id"] = np.where(np.arange(len(segmented)) < 130, "a", "b")
    reset = build_pit_core_measurements(segmented, binding=_binding())
    assert reset.loc[130:131, "signed_efficiency_ratio_2d"].isna().all()
    assert np.isfinite(reset.loc[132, "signed_efficiency_ratio_2d"])


def test_contract_is_measurement_only_and_defers_annual_only_fields() -> None:
    result = build_pit_core_measurements(_bars(), binding=_binding())
    contract = result.attrs["timing_layer_contract"]
    assert contract["local_resampling"] is False
    assert contract["annual_only_fields_deferred"] == [
        "no_buffer_reversal_rate",
        "bipower_jump_share",
    ]
    assert contract["routing_authority"] is False
    assert contract["production_authority"] is False
    lowered = {str(column).lower() for column in result.columns}
    assert not any(token in column for column in lowered for token in ("position", "claim", "action", "selected_"))


def test_provider_rejects_naive_or_invalid_bars_and_bad_binding() -> None:
    naive = _bars()
    naive["timestamp"] = pd.DatetimeIndex(naive["timestamp"]).tz_localize(None)
    with pytest.raises(ValidationError, match="timezone-aware"):
        build_pit_core_measurements(naive, binding=_binding())
    invalid = _bars()
    invalid.loc[0, "low"] = invalid.loc[0, "high"] * 2.0
    with pytest.raises(ValidationError, match="geometry"):
        build_pit_core_measurements(invalid, binding=_binding())
    with pytest.raises(ValidationError, match="bars_per_day"):
        PITCoreBinding(
            carrier_id="x",
            view_id="daily",
            bars_per_day=0,
            source_id="x",
            source_version="x",
            source_receipt_sha256="b" * 64,
        )
