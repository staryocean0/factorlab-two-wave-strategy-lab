"""V59 research prototype for crash, rebound, and renewed-crash handoff.

Each steep W12/W24 decline is an independent pulse.  The current pulse loses
cash authority when a close breaks the prior bar's high after the complete
fast family no longer qualifies.  A later decline must create a fresh
qualification edge and therefore a new channel; it never resumes the previous
frozen channel.
"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from factor_lab.strategy.services.risk_off_v58_short_volatility_confirmation import (
    ShortVolatilityConfirmationSpec,
)
from factor_lab.strategy.services.risk_off_v59_large_channel_parent import (
    V59LargeChannelParentSpec,
    build_v59_large_channel_parent,
    v59_large_channel_formula_contract,
)
from factor_lab.strategy.services.risk_off_v59_multiscale_middle_v56 import (
    W72_SPEC,
    V59MultiscaleMiddleV56Spec,
)

V59_CRASH_REBOUND_HANDOFF_SPEC = replace(
    V59LargeChannelParentSpec(),
    parent_promotion_enabled=False,
    fast_family_reset_release_enabled=True,
    fast_family_reset_release_mode="prior_high_break",
)


def build_v59_crash_rebound_handoff(
    causal_ohlc: pd.DataFrame,
    *,
    base_spec: V59MultiscaleMiddleV56Spec = V59MultiscaleMiddleV56Spec(),
    w72_spec: ShortVolatilityConfirmationSpec = W72_SPEC,
    w72_recovery_width_fraction: float = 1.0,
) -> pd.DataFrame:
    """Build the parameter-free family-reset handoff architecture."""

    output = build_v59_large_channel_parent(
        causal_ohlc,
        V59_CRASH_REBOUND_HANDOFF_SPEC,
        base_spec=base_spec,
        w72_spec=w72_spec,
        w72_recovery_width_fraction=w72_recovery_width_fraction,
    )
    output["strategy_version"] = "V59_crash_rebound_handoff_prototype"
    output["research_authority"] = True
    output["production_authority"] = False
    output.attrs["formula_contract"] = v59_crash_rebound_handoff_contract()
    return output


def v59_crash_rebound_handoff_contract() -> dict[str, object]:
    """Return the causal state-machine and K-line mapping contract."""

    contract = v59_large_channel_formula_contract(V59_CRASH_REBOUND_HANDOFF_SPEC)
    contract.update(
        {
            "schema_id": "risk_off_v59_crash_rebound_handoff@1.0",
            "strategy_version": "V59_crash_rebound_handoff_prototype",
            "state_machine": {
                "neutral_to_crash_cash": ("fresh W12 or W24 high-slope qualification edge; decision at close, cash on next bar"),
                "crash_cash_to_rebound_release": (
                    "first close above the prior bar high after all W12 and W24 qualifications reset, "
                    "or the frozen channel boundary breaks; long on next bar"
                ),
                "rebound_release_to_renewed_crash": (
                    "a later fresh W12/W24 high-slope qualification edge builds a new independent channel"
                ),
                "old_channel_resume_allowed": False,
                "numeric_exit_parameter_added": False,
            },
            "authority": {
                "research_authority": True,
                "production_authority": False,
            },
        }
    )
    return contract
