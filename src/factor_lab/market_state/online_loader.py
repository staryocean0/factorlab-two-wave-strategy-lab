"""Physical loader boundary for causal online market-state manifests."""

from __future__ import annotations

from collections.abc import Mapping

from factor_lab.market_state.contracts import OnlineMarketStateManifest
from factor_lab.market_state.contracts_a2 import (
    A2_ONLINE_MANIFEST_SCHEMA_ID,
    OnlineMarketStateManifestA2,
)


class OnlineMarketStateLoader:
    """Load only manifests that are safe for online/backtest feature use."""

    def load_manifest(
        self,
        payload: Mapping[str, object],
        *,
        usage: str,
    ) -> OnlineMarketStateManifest | OnlineMarketStateManifestA2:
        if payload.get("schema_id") == A2_ONLINE_MANIFEST_SCHEMA_ID:
            manifest = OnlineMarketStateManifestA2.from_dict(payload)
        else:
            manifest = OnlineMarketStateManifest.from_dict(payload)
        manifest.assert_usage(usage)
        return manifest


__all__ = ["OnlineMarketStateLoader"]
