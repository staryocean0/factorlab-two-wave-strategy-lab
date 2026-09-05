"""Repo-native base factor universe catalog.

The catalog is an intentionally curated starting universe.  It classifies the
factor space before individual factors are promoted into the normal
FactorSpec -> Candidate -> ValidationClaim -> EffectiveFactor lifecycle.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Final

from factor_lab.core.errors import NotFoundError, ValidationError
from factor_lab.core.source_universe import PRICE_VOLUME_SOURCE_FAMILY
from factor_lab.factor_engine.dsl import factor_spec_from_dsl
from factor_lab.factor_engine.models.factor_spec import FactorSpec
from factor_lab.factor_engine.repositories.spec_registry import spec_registry

BASE_FACTOR_UNIVERSE_VERSION: Final[str] = "base_factor_universe@0.1"
_OHLCV_FIELDS: Final[frozenset[str]] = frozenset(
    {"open", "high", "low", "close", "volume"}
)


@dataclass(frozen=True, slots=True)
class BaseFactorDefinition:
    factor_id: str
    name: str
    description: str
    category: str
    subcategory: str
    data_family: str
    required_fields: tuple[str, ...]
    construction_method: str
    horizon: str
    economic_rationale: str
    purpose: str
    neutralization_hint: str
    dsl_expression: str | None = None
    reference_families: tuple[str, ...] = ()
    tags: dict[str, str] = field(default_factory=dict)

    @property
    def seedable(self) -> bool:
        return self.dsl_expression is not None and set(self.required_fields).issubset(
            _OHLCV_FIELDS
        )

    @property
    def factor_spec_version(self) -> str:
        return f"fac_base_{self.factor_id}@1.0"

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["seedable"] = self.seedable
        payload["factor_spec_version"] = self.factor_spec_version
        payload["universe_version"] = BASE_FACTOR_UNIVERSE_VERSION
        payload["tags"] = {
            **self.tags,
            "base_factor_id": self.factor_id,
            "universe_category": self.category,
            "data_family": self.data_family,
            "purpose": self.purpose,
            "horizon": self.horizon,
        }
        return payload

    def to_factor_spec(self) -> FactorSpec:
        if not self.seedable or self.dsl_expression is None:
            raise ValidationError(
                f"Base factor is not seedable as a FactorSpec yet: {self.factor_id}"
            )
        spec = factor_spec_from_dsl(
            expression=self.dsl_expression,
            name=self.name,
            spec_version=self.factor_spec_version,
            source_family=PRICE_VOLUME_SOURCE_FAMILY,
        )
        spec.description = self.description
        spec.tags = {
            **spec.tags,
            **self.tags,
            "library": "base_factor_universe",
            "universe_version": BASE_FACTOR_UNIVERSE_VERSION,
            "base_factor_id": self.factor_id,
            "universe_category": self.category,
            "subcategory": self.subcategory,
            "data_family": self.data_family,
            "construction_method": self.construction_method,
            "horizon": self.horizon,
            "economic_rationale": self.economic_rationale,
            "purpose": self.purpose,
            "seedable": "true",
        }
        spec.parameters = {
            **spec.parameters,
            "base_factor_id": self.factor_id,
            "base_factor_category": self.category,
            "base_factor_subcategory": self.subcategory,
            "neutralization_hint": self.neutralization_hint,
            "reference_families": list(self.reference_families),
        }
        return spec


def _tags(style: str = "other", role: str = "alpha_signal") -> dict[str, str]:
    return {"style": style, "role": role, "source_family": PRICE_VOLUME_SOURCE_FAMILY}


BASE_FACTOR_DEFINITIONS: Final[tuple[BaseFactorDefinition, ...]] = (
    # Industry/reference factors.  These need industry membership and group-level
    # transforms, so they are cataloged now and become seedable when the data model
    # exposes industry panels to the factor engine.
    BaseFactorDefinition(
        factor_id="industry_dummy",
        name="industry_dummy",
        description=(
            "One-hot industry exposure used for neutralization and attribution."
        ),
        category="industry",
        subcategory="exposure",
        data_family="industry",
        required_fields=("industry_code",),
        construction_method="raw_exposure",
        horizon="cross_sectional",
        economic_rationale="structural",
        purpose="risk_exposure",
        neutralization_hint="industry",
        reference_families=("Barra-style industry exposure",),
        tags={"style": "industry", "role": "risk_exposure"},
    ),
    BaseFactorDefinition(
        factor_id="industry_return_5d",
        name="industry_return_5d",
        description="Five-day industry basket return for sector-relative context.",
        category="industry",
        subcategory="industry_momentum",
        data_family="industry+price_volume",
        required_fields=("industry_code", "close"),
        construction_method="group_aggregate",
        horizon="short",
        economic_rationale="structural",
        purpose="regime_feature",
        neutralization_hint="industry",
        reference_families=("industry relative strength",),
        tags={"style": "industry", "role": "regime_feature"},
    ),
    BaseFactorDefinition(
        factor_id="industry_return_20d",
        name="industry_return_20d",
        description="Twenty-day industry basket return for sector trend context.",
        category="industry",
        subcategory="industry_momentum",
        data_family="industry+price_volume",
        required_fields=("industry_code", "close"),
        construction_method="group_aggregate",
        horizon="medium",
        economic_rationale="structural",
        purpose="regime_feature",
        neutralization_hint="industry",
        reference_families=("industry relative strength",),
        tags={"style": "industry", "role": "regime_feature"},
    ),
    BaseFactorDefinition(
        factor_id="industry_relative_momentum_20d",
        name="industry_relative_momentum_20d",
        description="Stock momentum minus its industry momentum over twenty days.",
        category="industry",
        subcategory="industry_relative_alpha",
        data_family="industry+price_volume",
        required_fields=("industry_code", "close"),
        construction_method="group_neutralized_formula",
        horizon="medium",
        economic_rationale="behavioral",
        purpose="alpha_signal",
        neutralization_hint="industry",
        reference_families=("industry-neutral momentum",),
        tags={"style": "momentum", "role": "alpha_signal"},
    ),
    BaseFactorDefinition(
        factor_id="industry_relative_volume_20d",
        name="industry_relative_volume_20d",
        description="Stock volume intensity relative to its industry over twenty days.",
        category="industry",
        subcategory="industry_relative_liquidity",
        data_family="industry+price_volume",
        required_fields=("industry_code", "volume"),
        construction_method="group_neutralized_formula",
        horizon="medium",
        economic_rationale="technical",
        purpose="regime_feature",
        neutralization_hint="industry",
        reference_families=("industry volume participation",),
        tags={"style": "liquidity", "role": "regime_feature"},
    ),
    BaseFactorDefinition(
        factor_id="industry_neutralized_return_20d",
        name="industry_neutralized_return_20d",
        description="Twenty-day return residual after industry demeaning.",
        category="industry",
        subcategory="industry_neutralized_return",
        data_family="industry+price_volume",
        required_fields=("industry_code", "close"),
        construction_method="group_neutralized_formula",
        horizon="medium",
        economic_rationale="behavioral",
        purpose="alpha_signal",
        neutralization_hint="industry",
        reference_families=("industry neutral residual",),
        tags={"style": "reversal", "role": "alpha_signal"},
    ),
    # Size/reference factors.
    BaseFactorDefinition(
        factor_id="log_market_cap",
        name="log_market_cap",
        description="Natural log market capitalization exposure.",
        category="size",
        subcategory="size_exposure",
        data_family="market_cap",
        required_fields=("market_cap",),
        construction_method="raw_exposure",
        horizon="cross_sectional",
        economic_rationale="risk_premium",
        purpose="risk_exposure",
        neutralization_hint="size",
        reference_families=("Fama-French size", "Barra size"),
        tags={"style": "size", "role": "risk_exposure"},
    ),
    BaseFactorDefinition(
        factor_id="market_cap_rank",
        name="market_cap_rank",
        description="Cross-sectional rank of market capitalization.",
        category="size",
        subcategory="size_rank",
        data_family="market_cap",
        required_fields=("market_cap",),
        construction_method="cross_sectional_rank",
        horizon="cross_sectional",
        economic_rationale="risk_premium",
        purpose="risk_exposure",
        neutralization_hint="size",
        reference_families=("Fama-French size",),
        tags={"style": "size", "role": "risk_exposure"},
    ),
    BaseFactorDefinition(
        factor_id="float_market_cap_rank",
        name="float_market_cap_rank",
        description="Cross-sectional rank of float-adjusted market capitalization.",
        category="size",
        subcategory="float_size_rank",
        data_family="market_cap",
        required_fields=("float_market_cap",),
        construction_method="cross_sectional_rank",
        horizon="cross_sectional",
        economic_rationale="risk_premium",
        purpose="risk_exposure",
        neutralization_hint="size",
        reference_families=("Barra size",),
        tags={"style": "size", "role": "risk_exposure"},
    ),
    BaseFactorDefinition(
        factor_id="small_size_score",
        name="small_size_score",
        description="Small-cap score, usually inverse ranked market capitalization.",
        category="size",
        subcategory="small_size",
        data_family="market_cap",
        required_fields=("market_cap",),
        construction_method="cross_sectional_rank",
        horizon="cross_sectional",
        economic_rationale="risk_premium",
        purpose="alpha_signal",
        neutralization_hint="size_optional",
        reference_families=("Fama-French SMB",),
        tags={"style": "size", "role": "alpha_signal"},
    ),
    BaseFactorDefinition(
        factor_id="large_size_score",
        name="large_size_score",
        description="Large-cap score for stability or benchmark exposure control.",
        category="size",
        subcategory="large_size",
        data_family="market_cap",
        required_fields=("market_cap",),
        construction_method="cross_sectional_rank",
        horizon="cross_sectional",
        economic_rationale="structural",
        purpose="risk_exposure",
        neutralization_hint="size",
        reference_families=("benchmark size exposure",),
        tags={"style": "size", "role": "risk_exposure"},
    ),
    BaseFactorDefinition(
        factor_id="size_bucket",
        name="size_bucket",
        description=(
            "Discrete market-cap bucket for stratified validation and attribution."
        ),
        category="size",
        subcategory="size_bucket",
        data_family="market_cap",
        required_fields=("market_cap",),
        construction_method="bucket",
        horizon="cross_sectional",
        economic_rationale="structural",
        purpose="neutralization_control",
        neutralization_hint="size",
        reference_families=("size-sorted portfolios",),
        tags={"style": "size", "role": "neutralization_control"},
    ),
    # Style factors from OHLCV where possible.
    BaseFactorDefinition(
        "momentum_5d",
        "momentum_5d",
        "Five-day close-to-close momentum.",
        "style",
        "momentum",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "short",
        "behavioral",
        "alpha_signal",
        "industry,size optional",
        "close / delay(close, 5) - 1",
        ("Qlib Alpha158-style rolling returns",),
        _tags("momentum"),
    ),
    BaseFactorDefinition(
        "momentum_20d",
        "momentum_20d",
        "Twenty-day close-to-close momentum.",
        "style",
        "momentum",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "behavioral",
        "alpha_signal",
        "industry,size optional",
        "close / delay(close, 20) - 1",
        ("Qlib Alpha158-style rolling returns",),
        _tags("momentum"),
    ),
    BaseFactorDefinition(
        "momentum_60d",
        "momentum_60d",
        "Sixty-day close-to-close momentum.",
        "style",
        "momentum",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "behavioral",
        "alpha_signal",
        "industry,size optional",
        "close / delay(close, 60) - 1",
        ("Qlib Alpha158-style rolling returns",),
        _tags("momentum"),
    ),
    BaseFactorDefinition(
        "momentum_120d",
        "momentum_120d",
        "One-hundred-twenty-day close-to-close momentum.",
        "style",
        "momentum",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "long",
        "behavioral",
        "alpha_signal",
        "industry,size optional",
        "close / delay(close, 120) - 1",
        ("medium-term momentum",),
        _tags("momentum"),
    ),
    BaseFactorDefinition(
        "reversal_1d",
        "reversal_1d",
        "Negative one-day return reversal signal.",
        "style",
        "reversal",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "short",
        "behavioral",
        "alpha_signal",
        "industry optional",
        "-(close / delay(close, 1) - 1)",
        ("short-term reversal",),
        _tags("reversal"),
    ),
    BaseFactorDefinition(
        "reversal_5d",
        "reversal_5d",
        "Negative five-day return reversal signal.",
        "style",
        "reversal",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "short",
        "behavioral",
        "alpha_signal",
        "industry optional",
        "-(close / delay(close, 5) - 1)",
        ("short-term reversal",),
        _tags("reversal"),
    ),
    BaseFactorDefinition(
        "reversal_20d",
        "reversal_20d",
        "Negative twenty-day return reversal signal.",
        "style",
        "reversal",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "behavioral",
        "alpha_signal",
        "industry optional",
        "-(close / delay(close, 20) - 1)",
        ("medium-term reversal",),
        _tags("reversal"),
    ),
    BaseFactorDefinition(
        "low_volatility_20d",
        "low_volatility_20d",
        "Negative twenty-day realized return volatility.",
        "style",
        "volatility",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "risk_premium",
        "alpha_signal",
        "industry,size optional",
        "-std(close / delay(close, 1) - 1, 20)",
        ("low volatility", "TA-Lib volatility family"),
        _tags("volatility"),
    ),
    BaseFactorDefinition(
        "low_volatility_60d",
        "low_volatility_60d",
        "Negative sixty-day realized return volatility.",
        "style",
        "volatility",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "risk_premium",
        "alpha_signal",
        "industry,size optional",
        "-std(close / delay(close, 1) - 1, 60)",
        ("low volatility",),
        _tags("volatility"),
    ),
    BaseFactorDefinition(
        "liquidity_dollar_volume_20d",
        "liquidity_dollar_volume_20d",
        "Twenty-day average dollar volume liquidity proxy.",
        "style",
        "liquidity",
        "price_volume",
        ("close", "volume"),
        "formulaic_dsl",
        "medium",
        "structural",
        "risk_exposure",
        "liquidity optional",
        "mean(close * volume, 20)",
        ("liquidity proxy",),
        _tags("liquidity", "risk_exposure"),
    ),
    BaseFactorDefinition(
        "amihud_illiquidity_20d",
        "amihud_illiquidity_20d",
        "Amihud-style absolute return divided by dollar volume.",
        "style",
        "liquidity",
        "price_volume",
        ("close", "volume"),
        "formulaic_dsl",
        "medium",
        "structural",
        "alpha_signal",
        "liquidity optional",
        "mean(abs(close / delay(close, 1) - 1) / (close * volume), 20)",
        ("Amihud illiquidity",),
        _tags("liquidity"),
    ),
    BaseFactorDefinition(
        "market_beta_60d",
        "market_beta_60d",
        "Rolling beta to benchmark market return.",
        "style",
        "beta",
        "price_volume+benchmark",
        ("close", "benchmark_close"),
        "rolling_regression",
        "medium",
        "risk_premium",
        "risk_exposure",
        "market",
        None,
        ("market beta",),
        {"style": "volatility", "role": "risk_exposure"},
    ),
    BaseFactorDefinition(
        "market_correlation_60d",
        "market_correlation_60d",
        "Rolling correlation to benchmark market return.",
        "style",
        "beta",
        "price_volume+benchmark",
        ("close", "benchmark_close"),
        "rolling_correlation",
        "medium",
        "risk_premium",
        "risk_exposure",
        "market",
        None,
        ("market model",),
        {"style": "volatility", "role": "risk_exposure"},
    ),
    BaseFactorDefinition(
        "trend_strength_20d",
        "trend_strength_20d",
        "Close relative to twenty-day mean as a trend-strength proxy.",
        "style",
        "trend",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "technical",
        "alpha_signal",
        "industry optional",
        "close / mean(close, 20) - 1",
        ("TA-Lib overlap studies",),
        _tags("momentum"),
    ),
    # Price-volume factors.
    BaseFactorDefinition(
        "return_1d",
        "return_1d",
        "One-day close-to-close return.",
        "price_volume",
        "return",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "short",
        "technical",
        "alpha_signal",
        "industry optional",
        "close / delay(close, 1) - 1",
        ("Qlib Alpha158",),
        _tags("momentum"),
    ),
    BaseFactorDefinition(
        "return_5d",
        "return_5d",
        "Five-day close-to-close return.",
        "price_volume",
        "return",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "short",
        "technical",
        "alpha_signal",
        "industry optional",
        "close / delay(close, 5) - 1",
        ("Qlib Alpha158",),
        _tags("momentum"),
    ),
    BaseFactorDefinition(
        "return_20d",
        "return_20d",
        "Twenty-day close-to-close return.",
        "price_volume",
        "return",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "technical",
        "alpha_signal",
        "industry optional",
        "close / delay(close, 20) - 1",
        ("Qlib Alpha158",),
        _tags("momentum"),
    ),
    BaseFactorDefinition(
        "open_to_close_return",
        "open_to_close_return",
        "Intraday open-to-close return.",
        "price_volume",
        "intraday",
        "price_volume",
        ("open", "close"),
        "formulaic_dsl",
        "intraday",
        "technical",
        "alpha_signal",
        "industry optional",
        "close / open - 1",
        ("price transform",),
        _tags("reversal"),
    ),
    BaseFactorDefinition(
        "overnight_gap",
        "overnight_gap",
        "Open relative to previous close.",
        "price_volume",
        "gap",
        "price_volume",
        ("open", "close"),
        "formulaic_dsl",
        "short",
        "technical",
        "alpha_signal",
        "industry optional",
        "open / delay(close, 1) - 1",
        ("gap / overnight effect",),
        _tags("event"),
    ),
    BaseFactorDefinition(
        "intraday_range",
        "intraday_range",
        "High-low range scaled by close.",
        "price_volume",
        "range",
        "price_volume",
        ("high", "low", "close"),
        "formulaic_dsl",
        "short",
        "technical",
        "regime_feature",
        "volatility optional",
        "(high - low) / close",
        ("TA-Lib volatility family",),
        _tags("volatility", "regime_feature"),
    ),
    BaseFactorDefinition(
        "close_location_value",
        "close_location_value",
        "Close location within the daily high-low range.",
        "price_volume",
        "range",
        "price_volume",
        ("high", "low", "close"),
        "formulaic_dsl",
        "short",
        "technical",
        "alpha_signal",
        "industry optional",
        "((close - low) / (high - low)) - 0.5",
        ("price transform",),
        _tags("microstructure"),
    ),
    BaseFactorDefinition(
        "true_range_proxy_14d",
        "true_range_proxy_14d",
        "Fourteen-day average high-low range proxy.",
        "price_volume",
        "range",
        "price_volume",
        ("high", "low"),
        "formulaic_dsl",
        "short",
        "technical",
        "regime_feature",
        "volatility optional",
        "mean(high / low - 1, 14)",
        ("TA-Lib ATR proxy",),
        _tags("volatility", "regime_feature"),
    ),
    BaseFactorDefinition(
        "volume_change_5d",
        "volume_change_5d",
        "Five-day volume change.",
        "price_volume",
        "volume",
        "price_volume",
        ("volume",),
        "formulaic_dsl",
        "short",
        "technical",
        "regime_feature",
        "liquidity optional",
        "volume / delay(volume, 5) - 1",
        ("volume indicators",),
        _tags("liquidity", "regime_feature"),
    ),
    BaseFactorDefinition(
        "volume_zscore_20d",
        "volume_zscore_20d",
        "Twenty-day time-series z-score of volume.",
        "price_volume",
        "volume",
        "price_volume",
        ("volume",),
        "formulaic_dsl",
        "medium",
        "technical",
        "regime_feature",
        "liquidity optional",
        "ts_zscore(volume, 20)",
        ("Qlib rolling features",),
        _tags("liquidity", "regime_feature"),
    ),
    BaseFactorDefinition(
        "volume_price_corr_20d",
        "volume_price_corr_20d",
        "Twenty-day correlation between volume and returns.",
        "price_volume",
        "volume_price",
        "price_volume",
        ("close", "volume"),
        "formulaic_dsl",
        "medium",
        "technical",
        "alpha_signal",
        "industry optional",
        "corr(volume, close / delay(close, 1) - 1, 20)",
        ("WorldQuant-style price-volume correlation",),
        _tags("liquidity"),
    ),
    BaseFactorDefinition(
        "sma_ratio_5_20",
        "sma_ratio_5_20",
        "Five-day mean close relative to twenty-day mean close.",
        "price_volume",
        "moving_average",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "technical",
        "alpha_signal",
        "industry optional",
        "mean(close, 5) / mean(close, 20) - 1",
        ("TA-Lib overlap studies",),
        _tags("momentum"),
    ),
    BaseFactorDefinition(
        "macd_proxy_12_26",
        "macd_proxy_12_26",
        "Simple MACD-style twelve versus twenty-six day mean proxy.",
        "price_volume",
        "moving_average",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "technical",
        "alpha_signal",
        "industry optional",
        "mean(close, 12) / mean(close, 26) - 1",
        ("TA-Lib MACD family",),
        _tags("momentum"),
    ),
    BaseFactorDefinition(
        "bollinger_position_20d",
        "bollinger_position_20d",
        "Close z-score versus twenty-day rolling mean/std.",
        "price_volume",
        "bands",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "technical",
        "regime_feature",
        "volatility optional",
        "(close - mean(close, 20)) / std(close, 20)",
        ("TA-Lib Bollinger bands",),
        _tags("volatility", "regime_feature"),
    ),
    BaseFactorDefinition(
        "price_volume_pressure_20d",
        "price_volume_pressure_20d",
        "Correlation between price level and volume over twenty days.",
        "price_volume",
        "volume_price",
        "price_volume",
        ("close", "volume"),
        "formulaic_dsl",
        "medium",
        "technical",
        "alpha_signal",
        "industry optional",
        "corr(close, volume, 20)",
        ("WorldQuant-style price-volume relation",),
        _tags("liquidity"),
    ),
    BaseFactorDefinition(
        "high_low_breakout_20d",
        "high_low_breakout_20d",
        "Twenty-day time-series rank of close as breakout proxy.",
        "price_volume",
        "breakout",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "technical",
        "alpha_signal",
        "industry optional",
        "ts_rank(close, 20)",
        ("TA-Lib momentum family",),
        _tags("momentum"),
    ),
    # Generic time-series transforms.
    BaseFactorDefinition(
        "rolling_mean_return_20d",
        "rolling_mean_return_20d",
        "Twenty-day rolling mean of one-day returns.",
        "time_series",
        "rolling_return",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "technical",
        "alpha_signal",
        "industry optional",
        "mean(close / delay(close, 1) - 1, 20)",
        ("Qlib rolling features",),
        _tags("momentum"),
    ),
    BaseFactorDefinition(
        "rolling_vol_return_20d",
        "rolling_vol_return_20d",
        "Twenty-day rolling volatility of one-day returns.",
        "time_series",
        "rolling_volatility",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "risk_premium",
        "regime_feature",
        "volatility optional",
        "std(close / delay(close, 1) - 1, 20)",
        ("TA-Lib statistic functions",),
        _tags("volatility", "regime_feature"),
    ),
    BaseFactorDefinition(
        "rolling_zscore_close_20d",
        "rolling_zscore_close_20d",
        "Twenty-day time-series z-score of close.",
        "time_series",
        "rolling_zscore",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "technical",
        "regime_feature",
        "industry optional",
        "ts_zscore(close, 20)",
        ("Qlib rolling features",),
        _tags("momentum", "regime_feature"),
    ),
    BaseFactorDefinition(
        "rolling_rank_close_20d",
        "rolling_rank_close_20d",
        "Twenty-day time-series rank of close.",
        "time_series",
        "rolling_rank",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "technical",
        "alpha_signal",
        "industry optional",
        "ts_rank(close, 20)",
        ("Qlib rolling features",),
        _tags("momentum"),
    ),
    BaseFactorDefinition(
        "rolling_autocorr_return_20d",
        "rolling_autocorr_return_20d",
        "Twenty-day autocorrelation of one-day returns.",
        "time_series",
        "rolling_autocorrelation",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "medium",
        "technical",
        "regime_feature",
        "industry optional",
        "corr(close / delay(close, 1) - 1, delay(close / delay(close, 1) - 1, 1), 20)",
        ("statistic functions",),
        _tags("other", "regime_feature"),
    ),
    BaseFactorDefinition(
        "rolling_skew_return_20d",
        "rolling_skew_return_20d",
        "Twenty-day return skewness placeholder for later higher-moment support.",
        "time_series",
        "higher_moment",
        "price_volume",
        ("close",),
        "rolling_statistic",
        "medium",
        "technical",
        "regime_feature",
        "industry optional",
        None,
        ("higher moment statistics",),
        _tags("volatility", "regime_feature"),
    ),
    BaseFactorDefinition(
        "rolling_drawdown_20d",
        "rolling_drawdown_20d",
        "Twenty-day drawdown placeholder for later rolling max/min support.",
        "time_series",
        "drawdown",
        "price_volume",
        ("close",),
        "rolling_path_statistic",
        "medium",
        "behavioral",
        "alpha_signal",
        "industry optional",
        None,
        ("drawdown / path dependency",),
        _tags("reversal"),
    ),
    BaseFactorDefinition(
        "decay_linear_return_10d",
        "decay_linear_return_10d",
        "Ten-day linearly decayed return signal.",
        "time_series",
        "decay",
        "price_volume",
        ("close",),
        "formulaic_dsl",
        "short",
        "technical",
        "alpha_signal",
        "industry optional",
        "decay_linear(close / delay(close, 1) - 1, 10)",
        ("WorldQuant-style decay",),
        _tags("momentum"),
    ),
)

_DEFINITION_BY_ID: Final[dict[str, BaseFactorDefinition]] = {
    definition.factor_id: definition for definition in BASE_FACTOR_DEFINITIONS
}


def list_base_factor_definitions(
    *,
    category: str | None = None,
    data_family: str | None = None,
    purpose: str | None = None,
    seedable: bool | None = None,
) -> list[BaseFactorDefinition]:
    definitions = list(BASE_FACTOR_DEFINITIONS)
    if category:
        definitions = [item for item in definitions if item.category == category]
    if data_family:
        definitions = [item for item in definitions if item.data_family == data_family]
    if purpose:
        definitions = [item for item in definitions if item.purpose == purpose]
    if seedable is not None:
        definitions = [item for item in definitions if item.seedable is seedable]
    return definitions


def get_base_factor_definition(factor_id: str) -> BaseFactorDefinition:
    definition = _DEFINITION_BY_ID.get(factor_id)
    if definition is None:
        raise NotFoundError(f"Base factor not found: {factor_id}")
    return definition


def catalog_summary() -> dict[str, object]:
    categories: dict[str, int] = {}
    data_families: dict[str, int] = {}
    seedable_count = 0
    for definition in BASE_FACTOR_DEFINITIONS:
        categories[definition.category] = categories.get(definition.category, 0) + 1
        data_families[definition.data_family] = (
            data_families.get(definition.data_family, 0) + 1
        )
        if definition.seedable:
            seedable_count += 1
    return {
        "universe_version": BASE_FACTOR_UNIVERSE_VERSION,
        "total": len(BASE_FACTOR_DEFINITIONS),
        "seedable_total": seedable_count,
        "categories": categories,
        "data_families": data_families,
    }


async def seed_base_factor_specs(
    *,
    factor_ids: list[str],
    all_seedable: bool = False,
) -> dict[str, object]:
    if all_seedable:
        definitions = [item for item in BASE_FACTOR_DEFINITIONS if item.seedable]
    else:
        if not factor_ids:
            raise ValidationError("Provide factor_ids or set all_seedable=true")
        definitions = [
            get_base_factor_definition(factor_id) for factor_id in factor_ids
        ]

    registered: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    for definition in definitions:
        if not definition.seedable:
            skipped.append(
                {
                    "factor_id": definition.factor_id,
                    "reason": "not_seedable_until_required_fields_are_supported",
                }
            )
            continue
        spec = definition.to_factor_spec()
        existing = await spec_registry.get_factor_spec(spec.spec_version)
        if existing is None:
            existing = await spec_registry.register_factor_spec(spec)
        registered.append(existing.to_dict())
    return {
        "universe_version": BASE_FACTOR_UNIVERSE_VERSION,
        "registered_factor_specs": registered,
        "registered_total": len(registered),
        "skipped": skipped,
        "skipped_total": len(skipped),
    }
