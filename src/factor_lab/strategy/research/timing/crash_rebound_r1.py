# pyright: reportAny=false
"""Research-only crash-rebound candidate pending four-layer requalification."""

from __future__ import annotations

from typing import Final

from factor_lab.market_state.timing_crash_rebound_long_ema_h4_routing_r1 import (
    BASE_WIDTH_MULTIPLIER,
    CONSTRUCTION_ID,
    EMA_HALF_LIFE,
    FROZEN_BOUNDARIES,
    K_GRID,
)

SCHEMA_ID: Final[str] = "market_state_crash_rebound_current_best@2.1"
RESEARCH_ID: Final[str] = "market_state_lat_k_slope_rebound_controlled_battle_2021_2026_r1"
CURRENT_BEST_CANDIDATE_ID: Final[str] = "rebound_3level"
FOUR_LAYER_ROLE: Final[str] = "layer3_strategy_research"
LIFECYCLE: Final[str] = "research_pending_requalification"

FIELD_LABELS_ZH: Final[dict[str, str]] = {
    "axis_ema_h4": "入场动量轴（4棒半衰期）",
    "k_grid": "三档K网格",
    "frozen_boundaries": "冻结分位边界",
    "account_long": "做多账户",
    "current_best_candidate_id": "历史当前最优候选",
}


def current_best_contract() -> dict[str, object]:
    """Return the preserved formula under reset research-only authority."""

    return {
        "schema_id": SCHEMA_ID,
        "research_id": RESEARCH_ID,
        "current_best_candidate_id": CURRENT_BEST_CANDIDATE_ID,
        "four_layer_role": FOUR_LAYER_ROLE,
        "lifecycle": LIFECYCLE,
        "replaceable_by_layer2_measurement": True,
        "long_term_foundation": False,
        "scientific_status": (
            "historical challenge evidence preserved; current infrastructure "
            "requalification pending; research candidate only"
        ),
        "formula": {
            "axis": f"ema_h4 = log(open).diff().ewm(halflife={EMA_HALF_LIFE}).mean().shift(1)",
            "k_grid": list(K_GRID),
            "frozen_boundaries": [float(v) for v in FROZEN_BOUNDARIES],
            "mapping": "high axis value → small K; scale=K/1.5 on the entry upper rail",
            "entry": "close > middle + width × K/1.5",
            "exit": "close < middle",
            "construction_id": CONSTRUCTION_ID,
            "base_width_multiplier": BASE_WIDTH_MULTIPLIER,
        },
        "evidence_chain": {
            "dev_combo_gate": {
                "delta_net": 0.18047254437251592,
                "delta_sharpe": 0.01277707682909357,
                "positive_year_share": 0.6666666666666666,
            },
            "single_bucket_fresh_2021_2026": {
                "delta_net": 0.052672,
                "delta_sharpe": 0.015255,
                "positive_years": "6/6",
            },
            "combo_battle_2021_2026": {
                "delta_net": 0.457333,
                "delta_sharpe": 0.485458,
                "verdict": "champion_dethroned",
            },
            "controlled_battle_2021_2026": {
                "delta_net": 0.4659,
                "delta_sharpe": 0.4477,
                "verdict": "controlled_champion_dethroned",
            },
        },
        "frozen_pins": {
            "second_bucket": "B_path_eff_w8（上涨桶三档路由，已锁定）",
            "third_bucket": "width_k1p0（做空桶恒K=1.0，已锁定）",
            "priority": "crash_rebound > paper_up > ols_down > residual(always_zero)",
            "t_plus_one": "frozen signed T+1 state machine",
            "costs": "buy 1bp, sell 6bp",
            "data_boundary": "2021-2026 consumed under the predecessor workflow",
        },
        "authority": {
            "research_authority": True,
            "registered_use_authority": False,
            "parameter_authority": False,
            "routing_authority": False,
            "architecture_lock_authority": False,
            "paper_trading_authority": False,
            "live_trading_authority": False,
            "production_authority": False,
            "fresh_oos": False,
        },
        "field_labels_zh": FIELD_LABELS_ZH,
    }


__all__ = [
    "CURRENT_BEST_CANDIDATE_ID",
    "FIELD_LABELS_ZH",
    "FOUR_LAYER_ROLE",
    "LIFECYCLE",
    "RESEARCH_ID",
    "SCHEMA_ID",
    "current_best_contract",
]
