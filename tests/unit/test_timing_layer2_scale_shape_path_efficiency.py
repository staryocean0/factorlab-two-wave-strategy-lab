from __future__ import annotations

import numpy as np
import pandas as pd

from factor_lab.market_state.timing_layer2_next_path_efficiency import build_future_efficiency_ratio
from factor_lab.market_state.timing_layer2_scale_shape_path_efficiency import (
    SCALE_SHAPE_ID,
    build_scale_shape_features,
    features_for_method,
    fit_scale_shape,
)


def _close(rows: int = 500) -> pd.Series:
    rng = np.random.default_rng(5)
    index = pd.date_range("2014-01-02", periods=rows, freq="B", tz="Asia/Shanghai")
    returns = 0.01 * rng.normal(size=rows)
    returns[200:260] *= 4.0
    return pd.Series(1000.0 * np.exp(np.cumsum(returns)), index=index)


def test_scale_and_shape_are_prefix_invariant() -> None:
    close = _close()
    full = build_scale_shape_features(close)
    prefix = build_scale_shape_features(close.iloc[:300])
    pd.testing.assert_frame_equal(full.iloc[:300], prefix)
    joined = full.dropna()
    reconstructed_mid = joined["common_scale"] - joined["shape_short"] - joined["shape_long"]
    assert reconstructed_mid.notna().all()


def test_method_feature_columns_are_frozen() -> None:
    close = _close()
    assert list(features_for_method(close, method_id="common_scale_only").columns) == ["common_scale"]
    assert list(features_for_method(close, method_id="shape_residual").columns) == ["shape_short", "shape_long"]
    assert list(features_for_method(close, method_id="scale_and_shape").columns) == [
        "common_scale",
        "shape_short",
        "shape_long",
    ]


def test_fit_has_no_strategy_authority() -> None:
    close = _close()
    target = build_future_efficiency_ratio(close, horizon_bars=16)
    fitted = fit_scale_shape(
        close,
        target,
        method_id="shape_residual",
        target_id="future_efficiency_ratio",
        train_end=close.index[280],
        calibration_end=close.index[380],
    )
    assert SCALE_SHAPE_ID.endswith("@1.0")
    assert fitted.production_authority is False
    assert fitted.runtime_feature_future_reads == 0
