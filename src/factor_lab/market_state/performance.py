"""Frozen A2 performance budget derived from the formal A1 baseline."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Final

from factor_lab.core.errors import ValidationError

A2_PERFORMANCE_BUDGET_VERSION: Final[str] = "market_state_a2_budget@1.0"


@dataclass(frozen=True, slots=True)
class PerformanceBudgetA2:
    """Measured, normalized guardrails rather than guessed absolute limits."""

    version: str = A2_PERFORMANCE_BUDGET_VERSION
    a1_elapsed_seconds: float = 24.84055082598934
    a1_input_rows: int = 4487
    a1_output_rows: int = 296142
    a1_peak_rss_platform_units: int = 675648
    a1_output_bytes: int = 8009035
    minimum_a1_relative_output_throughput: float = 0.40
    maximum_a1_relative_rss_per_output_row: float = 4.0
    maximum_a1_relative_bytes_per_output_row: float = 4.0
    minimum_rows_for_enforcement: int = 4000

    def __post_init__(self) -> None:
        if self.version != A2_PERFORMANCE_BUDGET_VERSION:
            raise ValidationError("unsupported A2 performance budget version")
        if min(
            self.a1_elapsed_seconds,
            self.a1_input_rows,
            self.a1_output_rows,
            self.a1_peak_rss_platform_units,
            self.a1_output_bytes,
            self.minimum_a1_relative_output_throughput,
            self.maximum_a1_relative_rss_per_output_row,
            self.maximum_a1_relative_bytes_per_output_row,
        ) <= 0:
            raise ValidationError("A2 performance budget values must be positive")

    @property
    def minimum_output_rows_per_second(self) -> float:
        baseline = self.a1_output_rows / self.a1_elapsed_seconds
        return baseline * self.minimum_a1_relative_output_throughput

    @property
    def maximum_rss_per_million_output_rows(self) -> float:
        baseline = self.a1_peak_rss_platform_units / self.a1_output_rows * 1_000_000
        return baseline * self.maximum_a1_relative_rss_per_output_row

    @property
    def maximum_bytes_per_output_row(self) -> float:
        baseline = self.a1_output_bytes / self.a1_output_rows
        return baseline * self.maximum_a1_relative_bytes_per_output_row

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "minimum_output_rows_per_second": self.minimum_output_rows_per_second,
            "maximum_rss_per_million_output_rows": self.maximum_rss_per_million_output_rows,
            "maximum_bytes_per_output_row": self.maximum_bytes_per_output_row,
            "derivation": "formal A1 bundle market-state-a1-df9dd78dfbf6e6f7",
            "field_labels_zh": {
                "minimum_output_rows_per_second": "最低输出行吞吐",
                "maximum_rss_per_million_output_rows": "每百万输出行最大峰值内存平台单位",
                "maximum_bytes_per_output_row": "每输出行最大产物字节",
            },
        }

    def evaluate(
        self,
        *,
        input_rows: int,
        output_rows: int,
        elapsed_seconds: float,
        peak_rss_platform_units: int,
        output_bytes: int,
    ) -> dict[str, object]:
        if input_rows < 0 or output_rows <= 0 or elapsed_seconds <= 0.0:
            raise ValidationError("invalid A2 performance measurement")
        output_rate = output_rows / elapsed_seconds
        rss_per_million = peak_rss_platform_units / output_rows * 1_000_000
        bytes_per_row = output_bytes / output_rows
        enforced = input_rows >= self.minimum_rows_for_enforcement
        checks = {
            "output_throughput": output_rate >= self.minimum_output_rows_per_second,
            "rss_per_output_row": rss_per_million
            <= self.maximum_rss_per_million_output_rows,
            "bytes_per_output_row": bytes_per_row <= self.maximum_bytes_per_output_row,
        }
        passed = all(checks.values()) if enforced else True
        return {
            "schema_id": "market_state_performance_evaluation@1.0",
            "budget_version": self.version,
            "enforced": enforced,
            "passed": passed,
            "checks": checks,
            "measurements": {
                "input_rows": input_rows,
                "output_rows": output_rows,
                "elapsed_seconds": elapsed_seconds,
                "output_rows_per_second": output_rate,
                "peak_rss_platform_units": peak_rss_platform_units,
                "rss_per_million_output_rows": rss_per_million,
                "output_bytes": output_bytes,
                "bytes_per_output_row": bytes_per_row,
            },
            "limits": {
                "minimum_output_rows_per_second": self.minimum_output_rows_per_second,
                "maximum_rss_per_million_output_rows": self.maximum_rss_per_million_output_rows,
                "maximum_bytes_per_output_row": self.maximum_bytes_per_output_row,
            },
            "field_labels_zh": {
                "passed": "冻结性能预算是否通过",
                "checks": "分项性能门",
                "measurements": "实测性能",
            },
        }


def assert_performance_budget_passed(evaluation: dict[str, object]) -> None:
    if evaluation.get("passed") is not True:
        checks_raw = evaluation.get("checks")
        checks = checks_raw if isinstance(checks_raw, dict) else {}
        failed = [
            key
            for key, value in checks.items()
            if value is not True
        ]
        raise ValidationError(f"A2 frozen performance budget failed: {failed}")
    measurements = evaluation.get("measurements")
    if not isinstance(measurements, dict) or any(
        not math.isfinite(float(value))
        for value in measurements.values()
        if isinstance(value, (int, float))
    ):
        raise ValidationError("A2 performance measurements must be finite")


__all__ = [
    "A2_PERFORMANCE_BUDGET_VERSION",
    "PerformanceBudgetA2",
    "assert_performance_budget_passed",
]
