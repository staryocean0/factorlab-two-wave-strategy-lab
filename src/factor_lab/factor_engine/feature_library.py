"""Feature-library primitives below the governed factor lifecycle.

The feature library records reusable, computable fields.  Factors can cite
features, but factor effectiveness still belongs to strategy-bound evidence.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Final, Literal, Self, cast

from factor_lab.core.errors import ConflictError, NotFoundError, ValidationError
from factor_lab.core.settings import get_data_home

FeatureUsage = Literal["production", "training", "diagnostic", "label"]
FeatureStatus = Literal["draft", "active", "deprecated", "blocked"]
FactorResearchState = Literal[
    "ResearchFactor",
    "CandidateFactor",
    "EffectiveFactor",
    "AdmittedFactor",
]

VALID_FEATURE_USAGES: Final[frozenset[str]] = frozenset(
    {"production", "training", "diagnostic", "label"}
)
VALID_FEATURE_STATUSES: Final[frozenset[str]] = frozenset(
    {"draft", "active", "deprecated", "blocked"}
)
VALID_FACTOR_RESEARCH_STATES: Final[frozenset[str]] = frozenset(
    {"ResearchFactor", "CandidateFactor", "EffectiveFactor", "AdmittedFactor"}
)
POSITIVE_EVIDENCE_VERDICTS: Final[frozenset[str]] = frozenset(
    {"candidate_ready", "effective_in_context", "promising_in_context"}
)
POSITIVE_FAMILY_GOVERNANCE_VERDICTS: Final[frozenset[str]] = frozenset(
    {
        "family_governance_passed",
        "family_representative_ready",
        "strategy_adapter_ready",
    }
)


def _string_list(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return tuple(str(item) for item in value)
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return (str(value),)


def _object_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in cast(dict[object, object], value).items()}


def _require_non_empty_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValidationError(f"{field_name} is required")


def _require_non_empty_tuple(value: tuple[str, ...], field_name: str) -> None:
    if not value or any(not item.strip() for item in value):
        raise ValidationError(f"{field_name} is required")


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    """Project-level reusable feature specification."""

    feature_id: str
    chinese_name: str
    english_name: str
    formula: str
    data_sources: tuple[str, ...]
    frequency: str
    realtime_available: bool
    lookahead_risk: bool
    available_at: str
    usages: tuple[FeatureUsage, ...]
    applicable_scope: str
    disabled_boundaries: tuple[str, ...]
    evidence_status: str
    status: FeatureStatus = "active"
    feature_version: str = "1.0"
    provenance: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty_text(self.feature_id, "feature_id")
        _require_non_empty_text(self.chinese_name, "chinese_name")
        _require_non_empty_text(self.english_name, "english_name")
        _require_non_empty_text(self.formula, "formula")
        _require_non_empty_tuple(self.data_sources, "data_sources")
        _require_non_empty_text(self.frequency, "frequency")
        _require_non_empty_text(self.available_at, "available_at")
        _require_non_empty_tuple(cast(tuple[str, ...], self.usages), "usages")
        _require_non_empty_text(self.applicable_scope, "applicable_scope")
        _require_non_empty_tuple(self.disabled_boundaries, "disabled_boundaries")
        _require_non_empty_text(self.evidence_status, "evidence_status")
        if self.status not in VALID_FEATURE_STATUSES:
            raise ValidationError(f"Unsupported feature status: {self.status}")
        invalid = [usage for usage in self.usages if usage not in VALID_FEATURE_USAGES]
        if invalid:
            raise ValidationError(f"Unsupported feature usage: {', '.join(invalid)}")
        if self.lookahead_risk and "production" in self.usages:
            raise ValidationError(
                "lookahead-risk features cannot declare production usage"
            )

    @property
    def is_label_feature(self) -> bool:
        return "label" in self.usages

    def assert_production_eligible(self) -> None:
        if not self.realtime_available:
            raise ValidationError(
                f"Feature {self.feature_id} is not available at production "
                "inference time"
            )
        if self.lookahead_risk:
            raise ValidationError(
                f"Feature {self.feature_id} has lookahead risk and cannot be "
                "used for production inference"
            )
        if self.is_label_feature:
            raise ValidationError(
                f"Feature {self.feature_id} is a label feature and cannot be "
                "used for production inference"
            )
        if "production" not in self.usages:
            raise ValidationError(
                f"Feature {self.feature_id} is not marked for production usage"
            )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["data_sources"] = list(self.data_sources)
        payload["usages"] = list(self.usages)
        payload["disabled_boundaries"] = list(self.disabled_boundaries)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        return cls(
            feature_id=str(payload.get("feature_id", "")),
            chinese_name=str(payload.get("chinese_name", "")),
            english_name=str(payload.get("english_name", "")),
            formula=str(payload.get("formula", "")),
            data_sources=_string_list(payload.get("data_sources")),
            frequency=str(payload.get("frequency", "")),
            realtime_available=bool(payload.get("realtime_available", False)),
            lookahead_risk=bool(payload.get("lookahead_risk", False)),
            available_at=str(payload.get("available_at", "")),
            usages=cast(tuple[FeatureUsage, ...], _string_list(payload.get("usages"))),
            applicable_scope=str(payload.get("applicable_scope", "")),
            disabled_boundaries=_string_list(payload.get("disabled_boundaries")),
            evidence_status=str(payload.get("evidence_status", "")),
            status=cast(FeatureStatus, str(payload.get("status", "active"))),
            feature_version=str(payload.get("feature_version", "1.0")),
            provenance=_object_dict(payload.get("provenance")),
            metadata=_object_dict(payload.get("metadata")),
        )


class FeatureLibrary:
    """In-memory registry for project-level feature specifications."""

    def __init__(self, specs: tuple[FeatureSpec, ...] | None = None) -> None:
        self._specs: dict[str, FeatureSpec] = {}
        for spec in specs or ():
            self.register(spec)

    def register(self, spec: FeatureSpec) -> FeatureSpec:
        existing = self._specs.get(spec.feature_id)
        if existing is not None and existing != spec:
            raise ConflictError(f"FeatureSpec already exists: {spec.feature_id}")
        self._specs[spec.feature_id] = spec
        return spec

    def get(self, feature_id: str) -> FeatureSpec:
        spec = self._specs.get(feature_id)
        if spec is None:
            raise NotFoundError(f"FeatureSpec not found: {feature_id}")
        return spec

    def get_exact(self, feature_id: str, feature_version: str) -> FeatureSpec:
        """Resolve one feature only when the requested version is exact."""

        spec = self.get(feature_id)
        if spec.feature_version != feature_version:
            raise ValidationError(
                f"FeatureSpec version mismatch for {feature_id}: "
                f"requested {feature_version}, registered {spec.feature_version}"
            )
        return spec

    def list(
        self,
        usage: FeatureUsage | None = None,
        frequency: str | None = None,
        realtime_available: bool | None = None,
    ) -> tuple[FeatureSpec, ...]:
        specs = tuple(self._specs.values())
        if usage is not None:
            specs = tuple(spec for spec in specs if usage in spec.usages)
        if frequency is not None:
            specs = tuple(spec for spec in specs if spec.frequency == frequency)
        if realtime_available is not None:
            specs = tuple(
                spec
                for spec in specs
                if spec.realtime_available is realtime_available
            )
        return specs

    def to_records(self) -> list[dict[str, object]]:
        return [spec.to_dict() for spec in self.list()]

    def export_snapshot_records(
        self,
        refs: tuple[tuple[str, str], ...],
    ) -> list[dict[str, object]]:
        """Export a deterministic, exact-version FeatureSpec snapshot."""

        unique_refs = sorted(set(refs))
        return [
            self.get_exact(feature_id, feature_version).to_dict()
            for feature_id, feature_version in unique_refs
        ]

    @classmethod
    def from_records(cls, records: list[dict[str, object]]) -> Self:
        return cls(tuple(FeatureSpec.from_dict(record) for record in records))


class FeatureLibraryRegistry:
    """Persistent FeatureSpec registry under FACTOR_LAB_HOME."""

    def __init__(self) -> None:
        self._library = FeatureLibrary()
        self._loaded_path: Path | None = None

    @staticmethod
    def registry_path() -> Path:
        directory = get_data_home() / "feature_library"
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "feature_specs.json"

    def reset(self) -> None:
        self._library = FeatureLibrary()
        self._loaded_path = None

    def _load(self) -> None:
        path = self.registry_path()
        if self._loaded_path == path:
            return
        self._loaded_path = path
        self._library = FeatureLibrary()
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValidationError("feature_specs registry payload must be a list")
        records: list[dict[str, object]] = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValidationError("feature_specs registry must contain objects")
            records.append(cast(dict[str, object], item))
        self._library = FeatureLibrary.from_records(records)

    def _persist(self) -> None:
        path = self.registry_path()
        path.write_text(
            json.dumps(
                self._library.to_records(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    def register(self, spec: FeatureSpec) -> FeatureSpec:
        self._load()
        registered = self._library.register(spec)
        self._persist()
        return registered

    def get(self, feature_id: str) -> FeatureSpec:
        self._load()
        return self._library.get(feature_id)

    def get_exact(self, feature_id: str, feature_version: str) -> FeatureSpec:
        self._load()
        return self._library.get_exact(feature_id, feature_version)

    def list(
        self,
        usage: FeatureUsage | None = None,
        frequency: str | None = None,
        realtime_available: bool | None = None,
        status: FeatureStatus | None = None,
    ) -> tuple[FeatureSpec, ...]:
        self._load()
        specs = self._library.list(
            usage=usage,
            frequency=frequency,
            realtime_available=realtime_available,
        )
        if status is not None:
            specs = tuple(spec for spec in specs if spec.status == status)
        return specs

    def export_records(self) -> list[dict[str, object]]:
        self._load()
        return self._library.to_records()

    def export_snapshot_records(
        self,
        refs: tuple[tuple[str, str], ...],
    ) -> list[dict[str, object]]:
        self._load()
        return self._library.export_snapshot_records(refs)


@dataclass(frozen=True, slots=True)
class FeatureMaterializationRecord:
    """Auditable computed output for one FeatureSpec.

    The record stores where a computed feature snapshot lives.  It does not
    prescribe the compute engine or embed feature values in the registry.
    """

    materialization_id: str
    feature_id: str
    as_of: str
    field_name: str
    storage_uri: str
    row_count: int
    content_hash: str
    computed_at: str
    compute_version: str
    source_feature_version: str
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty_text(self.materialization_id, "materialization_id")
        _require_non_empty_text(self.feature_id, "feature_id")
        _require_non_empty_text(self.as_of, "as_of")
        _require_non_empty_text(self.field_name, "field_name")
        _require_non_empty_text(self.storage_uri, "storage_uri")
        if self.row_count < 0:
            raise ValidationError("row_count must be non-negative")
        _require_non_empty_text(self.content_hash, "content_hash")
        _require_non_empty_text(self.computed_at, "computed_at")
        _require_non_empty_text(self.compute_version, "compute_version")
        _require_non_empty_text(self.source_feature_version, "source_feature_version")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        return cls(
            materialization_id=str(payload.get("materialization_id", "")),
            feature_id=str(payload.get("feature_id", "")),
            as_of=str(payload.get("as_of", "")),
            field_name=str(payload.get("field_name", "")),
            storage_uri=str(payload.get("storage_uri", "")),
            row_count=int(payload.get("row_count", 0)),
            content_hash=str(payload.get("content_hash", "")),
            computed_at=str(payload.get("computed_at", "")),
            compute_version=str(payload.get("compute_version", "")),
            source_feature_version=str(payload.get("source_feature_version", "")),
            metadata=_object_dict(payload.get("metadata")),
        )


class FeatureMaterializationRegistry:
    """Persistent registry of computed FeatureSpec outputs."""

    def __init__(self) -> None:
        self._records: dict[str, FeatureMaterializationRecord] = {}
        self._loaded_path: Path | None = None

    @staticmethod
    def registry_path() -> Path:
        directory = get_data_home() / "feature_library"
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "feature_materializations.json"

    def reset(self) -> None:
        self._records = {}
        self._loaded_path = None

    def _load(self) -> None:
        path = self.registry_path()
        if self._loaded_path == path:
            return
        self._loaded_path = path
        self._records = {}
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValidationError("feature_materializations payload must be a list")
        for item in payload:
            if not isinstance(item, dict):
                raise ValidationError(
                    "feature_materializations registry must contain objects"
                )
            record = FeatureMaterializationRecord.from_dict(
                cast(dict[str, object], item)
            )
            self._records[record.materialization_id] = record

    def _persist(self) -> None:
        path = self.registry_path()
        payload = [record.to_dict() for record in self.list()]
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def register(
        self,
        record: FeatureMaterializationRecord,
        *,
        feature_registry: FeatureLibraryRegistry,
    ) -> FeatureMaterializationRecord:
        feature = feature_registry.get(record.feature_id)
        if feature.feature_version != record.source_feature_version:
            raise ValidationError(
                "source_feature_version must match registered FeatureSpec version"
            )
        self._load()
        existing = self._records.get(record.materialization_id)
        if existing is not None and existing != record:
            raise ConflictError(
                f"Feature materialization already exists: {record.materialization_id}"
            )
        self._records[record.materialization_id] = record
        self._persist()
        return record

    def list(
        self,
        feature_id: str | None = None,
        as_of: str | None = None,
    ) -> tuple[FeatureMaterializationRecord, ...]:
        self._load()
        records = tuple(self._records.values())
        if feature_id is not None:
            records = tuple(
                record for record in records if record.feature_id == feature_id
            )
        if as_of is not None:
            records = tuple(record for record in records if record.as_of == as_of)
        return records

    def export_records(self) -> list[dict[str, object]]:
        return [record.to_dict() for record in self.list()]


@dataclass(frozen=True, slots=True)
class ExternalClaimedFactor:
    """External claimed signal/factor that cites reusable FeatureSpec records."""

    external_factor_id: str
    source_refs: tuple[str, ...]
    original_definition: str
    claimed_market: str
    claimed_frequency: str
    feature_refs: tuple[str, ...] = ()
    validated_in_project: bool = False
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["source_refs"] = list(self.source_refs)
        payload["feature_refs"] = list(self.feature_refs)
        return payload


@dataclass(frozen=True, slots=True)
class InternalResearchFactor:
    """Internal factor asset before or during governed lifecycle promotion."""

    internal_factor_id: str
    name: str
    state: FactorResearchState
    rationale: str
    feature_refs: tuple[str, ...] = ()
    source_external_factor_id: str = ""
    evidence_refs: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.state not in VALID_FACTOR_RESEARCH_STATES:
            raise ValidationError(f"Unsupported factor research state: {self.state}")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["feature_refs"] = list(self.feature_refs)
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload


@dataclass(frozen=True, slots=True)
class StrategyFeatureSet:
    """Strategy-scoped feature usage split."""

    strategy_id: str
    production_feature_ids: tuple[str, ...] = ()
    training_feature_ids: tuple[str, ...] = ()
    diagnostic_feature_ids: tuple[str, ...] = ()
    label_feature_ids: tuple[str, ...] = ()

    def validate_production_features(self, library: FeatureLibrary) -> None:
        for feature_id in self.production_feature_ids:
            library.get(feature_id).assert_production_eligible()

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        for key, value in payload.items():
            if isinstance(value, tuple):
                payload[key] = list(value)
        return payload


@dataclass(frozen=True, slots=True)
class StrategyFactorEvidence:
    """Strategy-bound evidence for a feature or factor claim."""

    evidence_id: str
    strategy_id: str
    factor_ref: str
    feature_refs: tuple[str, ...]
    universe: str
    frequency: str
    prediction_target: str
    usage_mode: str
    validation_method: str
    walk_forward_result: dict[str, object]
    robustness_result: dict[str, object]
    validity_verdict: str
    failure_boundaries: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty_text(self.evidence_id, "evidence_id")
        _require_non_empty_text(self.strategy_id, "strategy_id")
        _require_non_empty_text(self.factor_ref, "factor_ref")
        _require_non_empty_tuple(self.feature_refs, "feature_refs")
        _require_non_empty_text(self.universe, "universe")
        _require_non_empty_text(self.frequency, "frequency")
        _require_non_empty_text(self.prediction_target, "prediction_target")
        _require_non_empty_text(self.usage_mode, "usage_mode")
        _require_non_empty_text(self.validation_method, "validation_method")
        _require_non_empty_text(self.validity_verdict, "validity_verdict")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["feature_refs"] = list(self.feature_refs)
        payload["failure_boundaries"] = list(self.failure_boundaries)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        return cls(
            evidence_id=str(payload.get("evidence_id", "")),
            strategy_id=str(payload.get("strategy_id", "")),
            factor_ref=str(payload.get("factor_ref", "")),
            feature_refs=_string_list(payload.get("feature_refs")),
            universe=str(payload.get("universe", "")),
            frequency=str(payload.get("frequency", "")),
            prediction_target=str(payload.get("prediction_target", "")),
            usage_mode=str(payload.get("usage_mode", "")),
            validation_method=str(payload.get("validation_method", "")),
            walk_forward_result=_object_dict(payload.get("walk_forward_result")),
            robustness_result=_object_dict(payload.get("robustness_result")),
            validity_verdict=str(payload.get("validity_verdict", "")),
            failure_boundaries=_string_list(payload.get("failure_boundaries")),
        )


class StrategyFactorEvidenceRegistry:
    """Persistent strategy-bound evidence registry."""

    def __init__(self) -> None:
        self._records: dict[str, StrategyFactorEvidence] = {}
        self._loaded_path: Path | None = None

    @staticmethod
    def registry_path() -> Path:
        directory = get_data_home() / "feature_library"
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "strategy_factor_evidence.json"

    def reset(self) -> None:
        self._records = {}
        self._loaded_path = None

    def _load(self) -> None:
        path = self.registry_path()
        if self._loaded_path == path:
            return
        self._loaded_path = path
        self._records = {}
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValidationError("strategy_factor_evidence payload must be a list")
        for item in payload:
            if not isinstance(item, dict):
                raise ValidationError(
                    "strategy_factor_evidence registry must contain objects"
                )
            record = StrategyFactorEvidence.from_dict(cast(dict[str, object], item))
            self._records[record.evidence_id] = record

    def _persist(self) -> None:
        path = self.registry_path()
        payload = [record.to_dict() for record in self.list()]
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def register(
        self,
        record: StrategyFactorEvidence,
        *,
        feature_registry: FeatureLibraryRegistry,
    ) -> StrategyFactorEvidence:
        for feature_id in record.feature_refs:
            feature_registry.get(feature_id)
        self._load()
        existing = self._records.get(record.evidence_id)
        if existing is not None and existing != record:
            raise ConflictError(
                f"Strategy factor evidence already exists: {record.evidence_id}"
            )
        self._records[record.evidence_id] = record
        self._persist()
        return record

    def list(
        self,
        strategy_id: str | None = None,
        feature_id: str | None = None,
        factor_ref: str | None = None,
    ) -> tuple[StrategyFactorEvidence, ...]:
        self._load()
        records = tuple(self._records.values())
        if strategy_id is not None:
            records = tuple(
                record for record in records if record.strategy_id == strategy_id
            )
        if feature_id is not None:
            records = tuple(
                record for record in records if feature_id in record.feature_refs
            )
        if factor_ref is not None:
            records = tuple(
                record for record in records if record.factor_ref == factor_ref
            )
        return records

    def export_records(self) -> list[dict[str, object]]:
        return [record.to_dict() for record in self.list()]


@dataclass(frozen=True, slots=True)
class FactorFamilyGovernanceRecord:
    """Strategy-context governance for a factor/feature family.

    This record is the mandatory bridge between a broad feature/factor family
    search and the strategy-specific factor evidence used by downstream
    candidate review.
    """

    governance_id: str
    strategy_id: str
    factor_ref: str
    feature_refs: tuple[str, ...]
    family_id: str
    family_role: str
    strategy_context: str
    variant_policy: str
    selection_method: str
    validation_method: str
    walk_forward_result: dict[str, object]
    redundancy_result: dict[str, object]
    representative_feature_refs: tuple[str, ...]
    governance_verdict: str
    failure_boundaries: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty_text(self.governance_id, "governance_id")
        _require_non_empty_text(self.strategy_id, "strategy_id")
        _require_non_empty_text(self.factor_ref, "factor_ref")
        _require_non_empty_tuple(self.feature_refs, "feature_refs")
        _require_non_empty_text(self.family_id, "family_id")
        _require_non_empty_text(self.family_role, "family_role")
        _require_non_empty_text(self.strategy_context, "strategy_context")
        _require_non_empty_text(self.variant_policy, "variant_policy")
        _require_non_empty_text(self.selection_method, "selection_method")
        _require_non_empty_text(self.validation_method, "validation_method")
        _require_non_empty_tuple(
            self.representative_feature_refs,
            "representative_feature_refs",
        )
        _require_non_empty_text(self.governance_verdict, "governance_verdict")
        missing_representatives = set(self.representative_feature_refs) - set(
            self.feature_refs
        )
        if missing_representatives:
            raise ValidationError(
                "representative_feature_refs must be a subset of feature_refs"
            )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["feature_refs"] = list(self.feature_refs)
        payload["representative_feature_refs"] = list(
            self.representative_feature_refs
        )
        payload["failure_boundaries"] = list(self.failure_boundaries)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        return cls(
            governance_id=str(payload.get("governance_id", "")),
            strategy_id=str(payload.get("strategy_id", "")),
            factor_ref=str(payload.get("factor_ref", "")),
            feature_refs=_string_list(payload.get("feature_refs")),
            family_id=str(payload.get("family_id", "")),
            family_role=str(payload.get("family_role", "")),
            strategy_context=str(payload.get("strategy_context", "")),
            variant_policy=str(payload.get("variant_policy", "")),
            selection_method=str(payload.get("selection_method", "")),
            validation_method=str(payload.get("validation_method", "")),
            walk_forward_result=_object_dict(payload.get("walk_forward_result")),
            redundancy_result=_object_dict(payload.get("redundancy_result")),
            representative_feature_refs=_string_list(
                payload.get("representative_feature_refs")
            ),
            governance_verdict=str(payload.get("governance_verdict", "")),
            failure_boundaries=_string_list(payload.get("failure_boundaries")),
            metadata=_object_dict(payload.get("metadata")),
        )


class FactorFamilyGovernanceRegistry:
    """Persistent registry for strategy-context factor family governance."""

    def __init__(self) -> None:
        self._records: dict[str, FactorFamilyGovernanceRecord] = {}
        self._loaded_path: Path | None = None

    @staticmethod
    def registry_path() -> Path:
        directory = get_data_home() / "feature_library"
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "factor_family_governance.json"

    def reset(self) -> None:
        self._records = {}
        self._loaded_path = None

    def _load(self) -> None:
        path = self.registry_path()
        if self._loaded_path == path:
            return
        self._loaded_path = path
        self._records = {}
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValidationError("factor_family_governance payload must be a list")
        for item in payload:
            if not isinstance(item, dict):
                raise ValidationError(
                    "factor_family_governance registry must contain objects"
                )
            record = FactorFamilyGovernanceRecord.from_dict(
                cast(dict[str, object], item)
            )
            self._records[record.governance_id] = record

    def _persist(self) -> None:
        path = self.registry_path()
        payload = [record.to_dict() for record in self.list()]
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def register(
        self,
        record: FactorFamilyGovernanceRecord,
        *,
        feature_registry: FeatureLibraryRegistry,
    ) -> FactorFamilyGovernanceRecord:
        for feature_id in set(record.feature_refs) | set(
            record.representative_feature_refs
        ):
            feature_registry.get(feature_id)
        self._load()
        existing = self._records.get(record.governance_id)
        if existing is not None and existing != record:
            raise ConflictError(
                f"Factor family governance already exists: {record.governance_id}"
            )
        self._records[record.governance_id] = record
        self._persist()
        return record

    def list(
        self,
        strategy_id: str | None = None,
        feature_id: str | None = None,
        factor_ref: str | None = None,
        family_id: str | None = None,
    ) -> tuple[FactorFamilyGovernanceRecord, ...]:
        self._load()
        records = tuple(self._records.values())
        if strategy_id is not None:
            records = tuple(
                record for record in records if record.strategy_id == strategy_id
            )
        if feature_id is not None:
            records = tuple(
                record for record in records if feature_id in record.feature_refs
            )
        if factor_ref is not None:
            records = tuple(
                record for record in records if record.factor_ref == factor_ref
            )
        if family_id is not None:
            records = tuple(record for record in records if record.family_id == family_id)
        return records

    def export_records(self) -> list[dict[str, object]]:
        return [record.to_dict() for record in self.list()]


@dataclass(frozen=True, slots=True)
class FeatureFactorReadinessReport:
    """Read-only audit before a feature/factor can enter candidate review."""

    strategy_id: str
    factor_ref: str
    feature_ids: tuple[str, ...]
    as_of: str
    production_required: bool
    family_governance_required: bool
    readiness: str
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    materialization_ids: tuple[str, ...]
    family_governance_ids: tuple[str, ...]
    next_actions: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        for key, value in payload.items():
            if isinstance(value, tuple):
                payload[key] = list(value)
        return payload


@dataclass(frozen=True, slots=True)
class CandidateReviewPackage:
    """Review package artifact for downstream CandidateFactor governance."""

    package_id: str
    strategy_id: str
    factor_ref: str
    feature_ids: tuple[str, ...]
    as_of: str
    readiness: str
    evidence_ids: tuple[str, ...]
    materialization_ids: tuple[str, ...]
    family_governance_required: bool = True
    family_governance_ids: tuple[str, ...] = ()
    review_status: str = "pending_review"
    promotion_scope: str = "candidate_review_only"
    creates_candidate_factor: bool = False
    creates_effective_factor: bool = False
    creates_admitted_factor: bool = False
    notes: str = ""
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty_text(self.package_id, "package_id")
        _require_non_empty_text(self.strategy_id, "strategy_id")
        _require_non_empty_text(self.factor_ref, "factor_ref")
        _require_non_empty_tuple(self.feature_ids, "feature_ids")
        _require_non_empty_text(self.readiness, "readiness")
        _require_non_empty_tuple(self.evidence_ids, "evidence_ids")
        _require_non_empty_tuple(self.materialization_ids, "materialization_ids")
        if self.family_governance_required:
            _require_non_empty_tuple(
                self.family_governance_ids,
                "family_governance_ids",
            )
        if self.readiness != "ready_for_candidate_review":
            raise ValidationError("candidate review package requires ready readiness")
        if (
            self.creates_candidate_factor
            or self.creates_effective_factor
            or self.creates_admitted_factor
        ):
            raise ValidationError("review packages must not create factor assets")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        for key, value in payload.items():
            if isinstance(value, tuple):
                payload[key] = list(value)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        return cls(
            package_id=str(payload.get("package_id", "")),
            strategy_id=str(payload.get("strategy_id", "")),
            factor_ref=str(payload.get("factor_ref", "")),
            feature_ids=_string_list(payload.get("feature_ids")),
            as_of=str(payload.get("as_of", "")),
            readiness=str(payload.get("readiness", "")),
            evidence_ids=_string_list(payload.get("evidence_ids")),
            materialization_ids=_string_list(payload.get("materialization_ids")),
            family_governance_required=bool(
                payload.get("family_governance_required", False)
            ),
            family_governance_ids=_string_list(
                payload.get("family_governance_ids")
            ),
            review_status=str(payload.get("review_status", "pending_review")),
            promotion_scope=str(
                payload.get("promotion_scope", "candidate_review_only")
            ),
            creates_candidate_factor=bool(
                payload.get("creates_candidate_factor", False)
            ),
            creates_effective_factor=bool(
                payload.get("creates_effective_factor", False)
            ),
            creates_admitted_factor=bool(
                payload.get("creates_admitted_factor", False)
            ),
            notes=str(payload.get("notes", "")),
            metadata=_object_dict(payload.get("metadata")),
        )


def assess_feature_factor_readiness(
    *,
    strategy_id: str,
    factor_ref: str,
    feature_ids: tuple[str, ...],
    feature_registry: FeatureLibraryRegistry,
    materialization_registry: FeatureMaterializationRegistry,
    evidence_registry: StrategyFactorEvidenceRegistry,
    family_governance_registry: FactorFamilyGovernanceRegistry | None = None,
    as_of: str = "",
    production_required: bool = False,
    family_governance_required: bool = True,
) -> FeatureFactorReadinessReport:
    """Audit whether registered assets are ready for candidate review."""

    _require_non_empty_text(strategy_id, "strategy_id")
    _require_non_empty_text(factor_ref, "factor_ref")
    _require_non_empty_tuple(feature_ids, "feature_ids")

    blockers: list[str] = []
    warnings: list[str] = []
    evidence_ids: set[str] = set()
    materialization_ids: set[str] = set()
    family_governance_ids: set[str] = set()

    for feature_id in feature_ids:
        feature = feature_registry.get(feature_id)
        if feature.status != "active":
            blockers.append(
                f"Feature {feature_id} status is {feature.status}, not active"
            )
        if production_required:
            try:
                feature.assert_production_eligible()
            except ValidationError as exc:
                blockers.append(str(exc))

        materializations = materialization_registry.list(
            feature_id=feature_id,
            as_of=as_of or None,
        )
        if not materializations:
            suffix = f" as_of {as_of}" if as_of else ""
            blockers.append(f"Feature {feature_id} has no materialization{suffix}")
        else:
            materialization_ids.update(
                record.materialization_id for record in materializations
            )

        evidence = evidence_registry.list(
            strategy_id=strategy_id,
            feature_id=feature_id,
            factor_ref=factor_ref,
        )
        if not evidence:
            blockers.append(
                f"Feature {feature_id} has no strategy-bound evidence for "
                f"{strategy_id}/{factor_ref}"
            )
            continue
        evidence_ids.update(record.evidence_id for record in evidence)
        if not any(
            record.validity_verdict in POSITIVE_EVIDENCE_VERDICTS
            for record in evidence
        ):
            blockers.append(
                f"Feature {feature_id} has no positive strategy-bound verdict"
            )
        if len({record.validity_verdict for record in evidence}) > 1:
            warnings.append(
                f"Feature {feature_id} has mixed evidence verdicts in this context"
            )

        if family_governance_required:
            if family_governance_registry is None:
                blockers.append("Factor family governance registry is required")
                continue
            governance = family_governance_registry.list(
                strategy_id=strategy_id,
                feature_id=feature_id,
                factor_ref=factor_ref,
            )
            if not governance:
                blockers.append(
                    f"Feature {feature_id} has no factor-family governance for "
                    f"{strategy_id}/{factor_ref}"
                )
                continue
            family_governance_ids.update(record.governance_id for record in governance)
            if not any(
                record.governance_verdict in POSITIVE_FAMILY_GOVERNANCE_VERDICTS
                for record in governance
            ):
                blockers.append(
                    f"Feature {feature_id} has no positive factor-family governance"
                )
            if len({record.governance_verdict for record in governance}) > 1:
                warnings.append(
                    f"Feature {feature_id} has mixed family governance verdicts "
                    "in this context"
                )

    readiness = "ready_for_candidate_review" if not blockers else "blocked"
    next_actions = (
        (
            "Create CandidateFactor review package from the referenced evidence "
            "and factor-family governance; do not claim EffectiveFactor until "
            "validation governance approves it."
        ),
    )
    if blockers:
        next_actions = tuple(
            f"Resolve blocker: {blocker}" for blocker in blockers
        )

    return FeatureFactorReadinessReport(
        strategy_id=strategy_id,
        factor_ref=factor_ref,
        feature_ids=feature_ids,
        as_of=as_of,
        production_required=production_required,
        family_governance_required=family_governance_required,
        readiness=readiness,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        evidence_ids=tuple(sorted(evidence_ids)),
        materialization_ids=tuple(sorted(materialization_ids)),
        family_governance_ids=tuple(sorted(family_governance_ids)),
        next_actions=next_actions,
    )


def build_candidate_review_package(
    *,
    package_id: str,
    readiness_report: FeatureFactorReadinessReport,
    notes: str = "",
    metadata: dict[str, object] | None = None,
) -> CandidateReviewPackage:
    """Build a non-promoting review artifact from a ready readiness report."""

    if readiness_report.readiness != "ready_for_candidate_review":
        raise ValidationError("cannot build candidate review package from blockers")
    return CandidateReviewPackage(
        package_id=package_id,
        strategy_id=readiness_report.strategy_id,
        factor_ref=readiness_report.factor_ref,
        feature_ids=readiness_report.feature_ids,
        as_of=readiness_report.as_of,
        readiness=readiness_report.readiness,
        evidence_ids=readiness_report.evidence_ids,
        materialization_ids=readiness_report.materialization_ids,
        family_governance_required=readiness_report.family_governance_required,
        family_governance_ids=readiness_report.family_governance_ids,
        notes=notes,
        metadata=metadata or {},
    )


class CandidateReviewPackageRegistry:
    """Persistent review-package artifact registry."""

    def __init__(self) -> None:
        self._records: dict[str, CandidateReviewPackage] = {}
        self._loaded_path: Path | None = None

    @staticmethod
    def registry_path() -> Path:
        directory = get_data_home() / "feature_library"
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "candidate_review_packages.json"

    def reset(self) -> None:
        self._records = {}
        self._loaded_path = None

    def _load(self) -> None:
        path = self.registry_path()
        if self._loaded_path == path:
            return
        self._loaded_path = path
        self._records = {}
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValidationError("candidate_review_packages payload must be a list")
        for item in payload:
            if not isinstance(item, dict):
                raise ValidationError(
                    "candidate_review_packages registry must contain objects"
                )
            record = CandidateReviewPackage.from_dict(cast(dict[str, object], item))
            self._records[record.package_id] = record

    def _persist(self) -> None:
        path = self.registry_path()
        payload = [record.to_dict() for record in self.list()]
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def register(self, package: CandidateReviewPackage) -> CandidateReviewPackage:
        self._load()
        existing = self._records.get(package.package_id)
        if existing is not None and existing != package:
            raise ConflictError(
                f"Candidate review package already exists: {package.package_id}"
            )
        self._records[package.package_id] = package
        self._persist()
        return package

    def list(
        self,
        strategy_id: str | None = None,
        factor_ref: str | None = None,
    ) -> tuple[CandidateReviewPackage, ...]:
        self._load()
        records = tuple(self._records.values())
        if strategy_id is not None:
            records = tuple(
                record for record in records if record.strategy_id == strategy_id
            )
        if factor_ref is not None:
            records = tuple(
                record for record in records if record.factor_ref == factor_ref
            )
        return records

    def export_records(self) -> list[dict[str, object]]:
        return [record.to_dict() for record in self.list()]


feature_library_registry = FeatureLibraryRegistry()
feature_materialization_registry = FeatureMaterializationRegistry()
strategy_factor_evidence_registry = StrategyFactorEvidenceRegistry()
factor_family_governance_registry = FactorFamilyGovernanceRegistry()
candidate_review_package_registry = CandidateReviewPackageRegistry()
