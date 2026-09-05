"""CloudRidge index infrastructure utilities."""

from __future__ import annotations

from factor_lab.cloudridge.attributes import (
    ATTRIBUTE_MA_WINDOWS,
    ATTRIBUTE_WINDOWS,
    CloudRidgeAttributeSpec,
    build_attribute_dictionary,
    build_cloudridge_attribute_bundle,
    build_cloudridge_attribute_ma_panel,
    build_cloudridge_attribute_panel,
    load_cloudridge_daily_panel,
)
from factor_lab.cloudridge.paper_kernel import (
    PAPER_KERNEL_ANNUALIZATION,
    PAPER_KERNEL_EMPIRICAL_WARMUP_DAYS,
    PAPER_KERNEL_SPAN_DAYS,
    PAPER_KERNEL_VOLATILITY_SPAN,
    PAPER_KERNEL_VOLATILITY_TARGET,
    build_paper_kernel_panel,
    paper_kernel_return_column_name,
    paper_kernel_signal_column_name,
)

__all__ = [
    "ATTRIBUTE_MA_WINDOWS",
    "ATTRIBUTE_WINDOWS",
    "CloudRidgeAttributeSpec",
    "PAPER_KERNEL_ANNUALIZATION",
    "PAPER_KERNEL_EMPIRICAL_WARMUP_DAYS",
    "PAPER_KERNEL_SPAN_DAYS",
    "PAPER_KERNEL_VOLATILITY_SPAN",
    "PAPER_KERNEL_VOLATILITY_TARGET",
    "build_attribute_dictionary",
    "build_cloudridge_attribute_bundle",
    "build_cloudridge_attribute_ma_panel",
    "build_cloudridge_attribute_panel",
    "build_paper_kernel_panel",
    "load_cloudridge_daily_panel",
    "paper_kernel_return_column_name",
    "paper_kernel_signal_column_name",
]
