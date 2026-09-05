"""Contracts for immutable group-correlation time-series products."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Final

from factor_lab.core.errors import ValidationError

GROUP_CORRELATION_SCHEMA_VERSION: Final[str] = "group_correlation_timeseries@1.0"
GROUP_CORRELATION_MANIFEST_SCHEMA_VERSION: Final[str] = (
    "group_correlation_timeseries_manifest@1.0"
)
INDEX_CONSTRUCTION_CONSUMER_CONTRACT: Final[str] = (
    "cn_a_custom_industry_index_construction_grade.v1"
)
INDEX_CONSTRUCTION_CAPABILITY: Final[str] = (
    "offline_fixed_version_custom_industry_index_construction"
)

FIELD_LABELS_ZH: Final[dict[str, str]] = {
    "universe_id": "群体标识",
    "universe_version": "群体版本",
    "observation_date": "观察日期",
    "observation_time": "观察完成时间",
    "available_at": "数据可用时间",
    "actionable_from": "最早可执行交易日",
    "lookback_window": "回看交易日数",
    "metric_id": "群体相关属性",
    "raw_value": "原始属性值",
    "eligible_asset_count": "合格股票数",
    "pair_count_total": "理论股票对数",
    "pair_count_evaluated": "已计算股票对数",
    "pair_count_skipped": "跳过股票对数",
    "pit_grade": "PIT用途等级",
    "production_authority": "生产路由权限",
}


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValidationError(f"{field_name} is required")


@dataclass(frozen=True, slots=True)
class GroupUniverseIdentity:
    universe_id: str
    universe_version: str
    pit_grade: str
    membership_semantics: str
    single_stock_authorized: bool = False
    strict_first_release_pit: bool = False
    production_authority: bool = False
    metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        _require_text(self.universe_id, "universe_id")
        _require_text(self.universe_version, "universe_version")
        _require_text(self.pit_grade, "pit_grade")
        _require_text(self.membership_semantics, "membership_semantics")
        if self.single_stock_authorized:
            raise ValidationError("group universe cannot authorize single-stock use")
        if self.production_authority:
            raise ValidationError("research universe cannot claim production authority")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["metadata"] = dict(self.metadata or {})
        return payload


@dataclass(frozen=True, slots=True)
class GroupCorrelationSourceIdentity:
    dataset_version: str
    dataset_hash: str
    view: str = "qfq_canonical"
    frequency: str = "1d"

    def __post_init__(self) -> None:
        _require_text(self.dataset_version, "dataset_version")
        _require_text(self.dataset_hash, "dataset_hash")
        if self.view != "qfq_canonical":
            raise ValidationError("group correlation requires qfq_canonical bars")
        if self.frequency != "1d":
            raise ValidationError("group correlation v1 requires 1d bars")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GroupCorrelationConfig:
    windows: tuple[int, ...] = (20, 60, 120)
    min_coverage_ratio: float = 0.80
    estimator_version: str = "fisher_pairwise_psd_v1"
    compute_backend: str = "cpu"
    parallel_workers: int = 1

    def __post_init__(self) -> None:
        if not self.windows or any(window < 3 for window in self.windows):
            raise ValidationError("windows must contain values of at least 3")
        if tuple(sorted(set(self.windows))) != self.windows:
            raise ValidationError("windows must be unique and ascending")
        if not 0.0 < self.min_coverage_ratio <= 1.0:
            raise ValidationError("min_coverage_ratio must be in (0, 1]")
        if self.compute_backend not in {"cpu", "cupy"}:
            raise ValidationError("compute_backend must be cpu or cupy")
        if not 1 <= self.parallel_workers <= 8:
            raise ValidationError("parallel_workers must be in 1..8")
        _require_text(self.estimator_version, "estimator_version")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["windows"] = list(self.windows)
        return payload


__all__ = [
    "FIELD_LABELS_ZH",
    "GROUP_CORRELATION_MANIFEST_SCHEMA_VERSION",
    "GROUP_CORRELATION_SCHEMA_VERSION",
    "GroupCorrelationConfig",
    "GroupCorrelationSourceIdentity",
    "GroupUniverseIdentity",
    "INDEX_CONSTRUCTION_CAPABILITY",
    "INDEX_CONSTRUCTION_CONSUMER_CONTRACT",
]
