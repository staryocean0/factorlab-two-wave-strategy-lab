"""FactorLab acceptance bindings for the 2026-09-01 DataHub gap deliveries."""

# Exact external path-to-digest bindings are intentionally kept on single lines.
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from factor_lab.core.errors import ValidationError

DATAHUB_ROOT: Final = Path("/home/starryocean/桌面/量化/unified_datahub")
KLINE_CONSUMER_CONTRACT: Final = "factorlab_on_demand_kline_intervals.v1"
KLINE_INTERVALS: Final = ("2m", "3m", "10m", "20m")
KLINE_MINUTES: Final = {"2m": 2, "3m": 3, "10m": 10, "20m": 20}
KLINE_PRODUCTS: Final = {interval: f"bars_cn_a_{interval}_raw_pit_offset_0" for interval in KLINE_INTERVALS}
KLINE_ACCEPTANCE_SNAPSHOT: Final = "bars_cn_a_1m_raw_canonical_4ceca170a851"
KLINE_AGGREGATION_CONTRACT: Final = "cn_a_on_demand_kline_offset_0.v1"

MO_BUNDLE_VERSION: Final = "factorlab_csi1000_multi_carrier_v2p1_research_bundle_20250901_20260825_ready_v1_20260831"
MO_BUNDLE_ROOT: Final = Path(f"/datahub/cold/runtime/live/lake/factorlab_csi1000_v2p1_research_bundle/dataset_version={MO_BUNDLE_VERSION}")
MO_BUNDLE_DATASET_HASH: Final = "8d3ae4b1f87340b169395d4edd1463983ef4391ccf12a3abd48e0259623a829a"
MO_BBO_DATASET_VERSION: Final = "factorlab_csi1000_v2p1_mo_bbo_20250901_20260825_v1_20260831"
MO_BBO_DATASET_HASH: Final = "2b250de7cf47e416551903c5bc07744334884ef2bb198b54d1329b8d0eeca8b9"
MO_BBO_RECORD_COUNT: Final = 556_911_166
ETF_OPTION_CONTRACT_UNIT: Final = 10_000
ETF_OPTION_FEE_RMB_PER_CONTRACT_SIDE: Final = 4.5

KLINE_UPSTREAM_HASHES: Final = {
    "src/datahub/core/services/history/on_demand_klines.py": "ee80a0e61bf53a59a765b823404822ec71903f267af14d0832640f32e260dbea",
    "src/datahub/api/routes/on_demand_klines.py": "d09441575fc1adc7cf2d708025246a0e3c96033479a81e464b0f09a252d004a5",
    "scripts/query_on_demand_klines.py": "1d94edf850f5074072e332f4c500328ba1f6b279eeed6059a6f3d7bb1d29ddd5",
    "scripts/validate_on_demand_klines.py": "4f68bc15952168a373547bad1192af24ea6ba4b2f9070d7c2899aa7197577019",
    "tests/unit/history/test_on_demand_klines.py": "530ce6159ebd88aa26f0d950bfbacce8545f2d1a362fe3939c5f49eb2defb57f",
    "tests/integration/api/test_on_demand_kline_route.py": "db904910902e12965d6350f398cf4e31d99e3fd2184328bd324c49e1f0c0ccbb",
    "docs/products/on-demand-kline-intervals.md": "dc9c80c03c938d1259b7f92bf9371b196963ba646b64ad0a7e9aa06ae5895360",
    "docs/modules/history/on-demand-kline-intervals-whitepaper.md": "75c79ff44d71ac15617f07fe9bffc24642bd0f82f790df07b6894d5f5c8f5c5a",
    "docs/modules/history/on-demand-kline-intervals-workflow.md": "055113fe1c992463a5e92497488bee217171cf0cd41f35ad976df0a12f6ac8ab",
    "config/reliability/consumer_contracts/factorlab_on_demand_kline_intervals.v1.json": "3e4797ffc7178ac1bbef1c630e51238b1b354c51b5fed0585dc335e215301f16",
    "config/reliability/dataset_contracts/factorlab_on_demand_kline_intervals.v1.json": "2789b7406f0dfcb0b84fcd0ddfc07bd31cf9a10019cfa4b5b20ee89c690136f9",
    "evidence/factorlab_on_demand_klines_20260831/acceptance/primary_acceptance.json": "9af940f835d8d096c73f4dfd25f0a6a6bc65c2139f3ff18561d441d72976fb38",
    "evidence/factorlab_on_demand_klines_20260831/acceptance/quality_report.json": "a44c8e83924c5b29af969405012d143e483baf0ee5111c454b6b8efc1b1d3237",
    "evidence/factorlab_on_demand_klines_20260831/acceptance/test_report.json": "0b0b26cfbb2776618880c02175725b1160be3590b1f29001026a44091e997ae0",
}

MO_UPSTREAM_HASHES: Final = {
    "docs/planning/factorlab_csi1000_v2p1_mo_orderbook_onboarding_20260831.md": "34420290e336f8c9a06d0d6a341f10ece949662683bec8dcace883c5365eee5e",
    "config/reliability/consumer_contracts/factorlab_csi1000_multi_carrier_v2p1_research.v1.json": "f72f21e3be50c6fd6601e57c87936421ffd90adce7d40d6c95e2116562835c11",
    "config/reliability/dataset_contracts/factorlab_csi1000_v2p1_products.v1.json": "903e26bbd242b9321f7413557f70a26291b9aca0efa9f871608b814c6b9bb927",
    "config/reliability/source_contracts/factorlab_csi1000_v2p1_sources.v1.json": "ce017b3fc43b620684343f96c6933305bb5cf241076f257d2a0730575e9b4751",
    "config/reliability/transformation_contracts/factorlab_csi1000_v2p1_transforms.v1.json": "50436c092327f5eb9065d3f8d11e5de2f5d0055bcad831d4eb7575e335775635",
    "scripts/factorlab_csi1000_v2p1.py": "8718eeee6dc3a343ee0a3b3c5da54f0171cc9f6bc8b3a41453e7ed2fa9d7132c",
    "scripts/promote_factorlab_csi1000_v2p1.py": "8cbbbbe5b59d0f3fbff60fa34390730312bee5e9cd84468e5e9ae8b1d9dd894f",
    "tests/unit/history/test_csi1000_v2p1_mo.py": "94c77ce1c3a5c997ca7b0bc061f1f1a5ee6183cf24b3dd74fc21086dd3dff822",
    "tests/unit/scripts/test_promote_factorlab_csi1000_v2p1.py": "1b4a1d6d24f418a29a0c0f3f70c9f30cca159ebb80e2a05bde5738220291d88f",
    "evidence/factorlab_csi1000_v2p1_20260831/datahub_completion_report.json": "768548127793964dc086e4903c16d42fdf6e8319fe1c086c5564c7aa0b12d6ff",
    "evidence/factorlab_csi1000_v2p1_20260831/promotion_receipt.json": "86a8a8a37f1b89958373daa7103b9b2b59966285bd80296a4471cfb14eee7817",
    "evidence/factorlab_csi1000_v2p1_20260831/primary_acceptance.json": "34ec053919e023f557295586ddfdb62a587921842e5a1999931e4d334148d626",
    "evidence/factorlab_csi1000_v2p1_20260831/determinism_report.json": "b62a3bd9480f5c7703baed2c73bc4b66890a7d01eedea3dd1cb6c3bcaa867560",
    "evidence/factorlab_csi1000_v2p1_20260831/test_report.json": "2de31c9570ec38825d22c6b84969ee814c90307f7d4f8dcde54869a245dd81f6",
}

MO_BUNDLE_FILE_HASHES: Final = {
    "manifest.json": "f45ee91da01541b3db92664a0139f134ef47609aed460a5c085be30ff54675d4",
    "factorlab_handoff.json": "c1f349424e4c5fa5244d6af89e2ab2e931c5a8bb5f826a6ab683f02fe7c1fe40",
    "certification_report.json": "dc5370196369834ecaca7d211ef1b5cfdc08941ad95c0219501d716b4db18785",
    "primary_acceptance.json": "34ec053919e023f557295586ddfdb62a587921842e5a1999931e4d334148d626",
    "components/mo_bbo/candidate_manifest.json": "7dd4753184fe515b20a4a8f54f17cf551791149146762870efac06c5ba8a9f68",
    "components/partial_impact/candidate_manifest.json": "4f05f481d5570d6886e692975535abb3928365ef0061804d2c2012fc8aaa7760",
}


@dataclass(frozen=True, slots=True)
class KlineDeliveryBinding:
    consumer_contract: str
    intervals: tuple[str, ...]
    product_ids: tuple[str, ...]
    acceptance_snapshot: str
    aggregation_contract: str
    upstream_file_count: int
    runtime_or_backtest_input_ready: bool
    production_authority: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MoDeliveryBinding:
    bundle_version: str
    bundle_dataset_hash: str
    mo_bbo_dataset_version: str
    mo_bbo_dataset_hash: str
    mo_bbo_record_count: int
    continuous_quote_change_bbo_ready: bool
    l1_quote_change_ofi_ready: bool
    bounded_l1_marketable_execution_ready: bool
    partial_impact_ready: bool
    true_order_event_ofi_ready: bool
    true_counterfactual_impact_ready: bool
    historical_market_replay_only: bool
    production_authority: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BoundedL1MarketableFill:
    side: str
    order_units: int
    execution_price: float
    displayed_opposite_size: int
    displayed_depth_participation: float
    premium_cash: float
    fixed_fee_rmb: float
    true_counterfactual_impact_claim: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ETFOptionTradeCost:
    quote_price_per_etf_unit: float
    contract_count: int
    transaction_side_count: int
    contract_unit: int
    premium_cash_rmb: float
    trading_fee_rmb: float
    exercise_or_assignment_fee_included: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValidationError(f"expected JSON object: {path}")
    return payload


def _validate_hashes(root: Path, expected: Mapping[str, str]) -> None:
    for relative, digest in expected.items():
        path = root / relative
        if not path.is_file():
            raise ValidationError(f"DataHub acceptance input missing: {path}")
        if _sha256(path) != digest:
            raise ValidationError(f"DataHub acceptance input drifted: {path}")


def validate_on_demand_kline_binding(
    datahub_root: Path = DATAHUB_ROOT,
) -> KlineDeliveryBinding:
    root = datahub_root.resolve()
    _validate_hashes(root, KLINE_UPSTREAM_HASHES)
    contract = _json(root / "config/reliability/consumer_contracts/factorlab_on_demand_kline_intervals.v1.json")
    primary = _json(root / "evidence/factorlab_on_demand_klines_20260831/acceptance/primary_acceptance.json")
    quality = _json(root / "evidence/factorlab_on_demand_klines_20260831/acceptance/quality_report.json")
    test_report = _json(root / "evidence/factorlab_on_demand_klines_20260831/acceptance/test_report.json")
    binding = contract.get("product_binding")
    query = contract.get("query_contract")
    if not isinstance(binding, dict) or not isinstance(query, dict):
        raise ValidationError("DataHub K-line contract shape drifted")
    if (
        contract.get("consumer_contract_id") != KLINE_CONSUMER_CONTRACT
        or binding.get("product_ids") != list(KLINE_PRODUCTS.values())
        or binding.get("source_snapshot_required") is not True
        or binding.get("latest_alias_allowed") is not False
        or binding.get("aggregation_contract_version") != KLINE_AGGREGATION_CONTRACT
        or query.get("default_completeness_policy") != "fail"
        or contract.get("current_serving_authority") is not True
        or contract.get("production_granted") is not False
        or "25m" not in list(contract.get("out_of_scope") or [])
    ):
        raise ValidationError("DataHub K-line serving contract drifted")
    checks = quality.get("checks")
    if (
        primary.get("decision") != "PASS"
        or primary.get("data_ready") is not True
        or primary.get("evidence_ready") is not True
        or primary.get("artifact_ready") is not True
        or primary.get("production_granted") is not False
        or quality.get("passed") is not True
        or not isinstance(checks, dict)
        or not all(value is True for value in checks.values())
        or test_report.get("passed") is not True
        or test_report.get("exit_code") != 0
    ):
        raise ValidationError("DataHub K-line acceptance evidence failed")
    return KlineDeliveryBinding(
        consumer_contract=KLINE_CONSUMER_CONTRACT,
        intervals=KLINE_INTERVALS,
        product_ids=tuple(KLINE_PRODUCTS.values()),
        acceptance_snapshot=KLINE_ACCEPTANCE_SNAPSHOT,
        aggregation_contract=KLINE_AGGREGATION_CONTRACT,
        upstream_file_count=len(KLINE_UPSTREAM_HASHES),
        runtime_or_backtest_input_ready=True,
        production_authority=False,
    )


def _moment(value: object) -> datetime:
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"invalid K-line timestamp: {value}") from exc


def validate_on_demand_kline_payload(
    payload: Mapping[str, object],
    *,
    interval: str,
    source_snapshot: str,
) -> dict[str, object]:
    if interval not in KLINE_INTERVALS:
        raise ValidationError(f"unsupported formal K-line interval: {interval}")
    product_id = KLINE_PRODUCTS[interval]
    items = payload.get("items")
    receipt = payload.get("query_receipt")
    if payload.get("product_id") != product_id or not isinstance(items, list):
        raise ValidationError("DataHub K-line payload identity drifted")
    if not isinstance(receipt, dict):
        raise ValidationError("DataHub K-line query receipt missing")
    query = receipt.get("query_parameters")
    if not isinstance(query, dict):
        raise ValidationError("DataHub K-line normalized query missing")
    if (
        receipt.get("product_id") != product_id
        or receipt.get("source_snapshot") != source_snapshot
        or receipt.get("aggregation_contract_version") != KLINE_AGGREGATION_CONTRACT
        or query.get("consumer_contract") != KLINE_CONSUMER_CONTRACT
        or query.get("completeness_policy") != "fail"
        or query.get("offset") != "offset_0"
        or query.get("price_space") != "raw"
        or receipt.get("incomplete_bar_count") != 0
        or receipt.get("returned_row_count") != len(items)
    ):
        raise ValidationError("DataHub K-line receipt is not fail-closed")
    as_of = _moment(query.get("as_of"))
    expected = KLINE_MINUTES[interval]
    for item in items:
        if not isinstance(item, dict):
            raise ValidationError("DataHub K-line item must be an object")
        start = _moment(item.get("bar_start_time"))
        end = _moment(item.get("bar_end_time"))
        available = _moment(item.get("available_at"))
        start_hm = start.strftime("%H:%M")
        end_hm = end.strftime("%H:%M")
        if (
            item.get("product_id") != product_id
            or item.get("interval") != interval
            or item.get("offset") != "offset_0"
            or item.get("alignment") != "offset_0"
            or item.get("source_snapshot") != source_snapshot
            or item.get("is_complete") is not True
            or item.get("source_bar_count") != expected
            or item.get("expected_source_bar_count") != expected
            or start.date() != end.date()
            or start_hm < "13:00" < end_hm
            or end > as_of
            or available > as_of
        ):
            raise ValidationError("DataHub K-line item violated causal completeness")
    return {
        "status": "passed",
        "interval": interval,
        "product_id": product_id,
        "row_count": len(items),
        "content_sha256": receipt.get("content_sha256"),
    }


def compute_l1_quote_change_ofi(events: pd.DataFrame) -> pd.DataFrame:
    """Compute causal top-of-book OFI from consecutive quote-change states.

    This is the standard L1 BBO event imbalance. It is intentionally not named
    order-message OFI because the source has no add/cancel/order-id taxonomy.
    """

    required = {
        "instrument_id",
        "trading_day",
        "session_phase",
        "market_observed_at",
        "source_sequence",
        "is_checkpoint",
        "quote_change_semantics_proven",
        "depth_status",
        "bid_price_1",
        "ask_price_1",
        "bid_size_1",
        "ask_size_1",
    }
    if missing := sorted(required.difference(events.columns)):
        raise ValidationError(f"MO L1 OFI input missing columns: {missing}")
    frame = events.copy()
    frame["market_observed_at"] = pd.to_datetime(frame["market_observed_at"], errors="raise", utc=True, format="mixed")
    for column in ("bid_price_1", "ask_price_1", "bid_size_1", "ask_size_1"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    keys = ["instrument_id", "trading_day", "session_phase"]
    frame = frame.sort_values([*keys, "market_observed_at", "source_sequence"], kind="mergesort").reset_index(drop=True)
    grouped = frame.groupby(keys, sort=False, dropna=False)
    previous = {
        column: grouped[column].shift(1)
        for column in (
            "bid_price_1",
            "ask_price_1",
            "bid_size_1",
            "ask_size_1",
            "depth_status",
        )
    }
    valid = (
        previous["bid_price_1"].notna()
        & ~frame["is_checkpoint"].astype(bool)
        & frame["quote_change_semantics_proven"].astype(bool)
        & frame["depth_status"].eq("two_sided")
        & previous["depth_status"].eq("two_sided")
        & frame["bid_price_1"].gt(0.0)
        & frame["ask_price_1"].ge(frame["bid_price_1"])
        & frame["bid_size_1"].gt(0.0)
        & frame["ask_size_1"].gt(0.0)
    )
    bid_new = frame["bid_price_1"].to_numpy(float)
    ask_new = frame["ask_price_1"].to_numpy(float)
    bid_size_new = frame["bid_size_1"].to_numpy(float)
    ask_size_new = frame["ask_size_1"].to_numpy(float)
    bid_old = previous["bid_price_1"].to_numpy(float)
    ask_old = previous["ask_price_1"].to_numpy(float)
    bid_size_old = previous["bid_size_1"].to_numpy(float)
    ask_size_old = previous["ask_size_1"].to_numpy(float)
    ofi = (
        np.where(bid_new >= bid_old, bid_size_new, 0.0)
        - np.where(bid_new <= bid_old, bid_size_old, 0.0)
        - np.where(ask_new <= ask_old, ask_size_new, 0.0)
        + np.where(ask_new >= ask_old, ask_size_old, 0.0)
    )
    frame["l1_quote_change_ofi"] = np.where(valid.to_numpy(), ofi, np.nan)
    frame["l1_quote_change_ofi_valid"] = valid.to_numpy()
    frame["ofi_measurement_kind"] = "l1_bbo_quote_change_ofi"
    frame["true_order_event_ofi_claim"] = False
    return frame


def price_bounded_l1_marketable_fill(
    *,
    side: str,
    order_units: int,
    bid_price_1: float,
    ask_price_1: float,
    bid_size_1: int,
    ask_size_1: int,
    contract_multiplier: int = 100,
    fee_rmb_per_contract_side: float = 14.0,
) -> BoundedL1MarketableFill:
    """Price a marketable MO order only when visible L1 covers the whole order."""

    if side not in {"buy", "sell"} or order_units < 1:
        raise ValidationError("bounded L1 fill needs buy/sell and positive units")
    if (
        not 0.0 < bid_price_1 <= ask_price_1
        or bid_size_1 < 1
        or ask_size_1 < 1
        or contract_multiplier != 100
        or fee_rmb_per_contract_side < 0.0
    ):
        raise ValidationError("bounded L1 fill received an invalid MO quote")
    displayed = ask_size_1 if side == "buy" else bid_size_1
    if order_units > displayed:
        raise ValidationError("MO order exceeds displayed opposite-side L1 depth")
    price = ask_price_1 if side == "buy" else bid_price_1
    return BoundedL1MarketableFill(
        side=side,
        order_units=order_units,
        execution_price=float(price),
        displayed_opposite_size=int(displayed),
        displayed_depth_participation=float(order_units / displayed),
        premium_cash=float(price * contract_multiplier * order_units),
        fixed_fee_rmb=float(fee_rmb_per_contract_side * order_units),
    )


def price_etf_option_trade_cost(
    *,
    quote_price_per_etf_unit: float,
    contract_count: int,
    transaction_side_count: int = 1,
) -> ETFOptionTradeCost:
    """Apply the user-authorized ETF-option contract unit and trading fee."""

    if quote_price_per_etf_unit <= 0.0 or contract_count < 1:
        raise ValidationError("ETF option cost needs positive quote and contracts")
    if transaction_side_count not in {1, 2}:
        raise ValidationError("ETF option transaction side count must be one or two")
    return ETFOptionTradeCost(
        quote_price_per_etf_unit=float(quote_price_per_etf_unit),
        contract_count=int(contract_count),
        transaction_side_count=int(transaction_side_count),
        contract_unit=ETF_OPTION_CONTRACT_UNIT,
        premium_cash_rmb=float(quote_price_per_etf_unit * ETF_OPTION_CONTRACT_UNIT * contract_count),
        trading_fee_rmb=float(ETF_OPTION_FEE_RMB_PER_CONTRACT_SIDE * contract_count * transaction_side_count),
    )


def build_on_demand_kline_cli_command(
    *,
    datahub_root: Path,
    source_snapshot: str,
    symbol: str,
    instrument_type: str,
    interval: str,
    start_time: str,
    end_time: str,
    as_of: str,
) -> tuple[str, ...]:
    if interval not in KLINE_INTERVALS:
        raise ValidationError(f"unsupported formal K-line interval: {interval}")
    root = datahub_root.resolve()
    return (
        str(root / ".venv/bin/python"),
        str(root / "scripts/query_on_demand_klines.py"),
        "--source-snapshot",
        source_snapshot,
        "--symbol",
        symbol,
        "--instrument-type",
        instrument_type,
        "--interval",
        interval,
        "--start-time",
        start_time,
        "--end-time",
        end_time,
        "--as-of",
        as_of,
        "--completeness-policy",
        "fail",
        "--consumer-contract",
        KLINE_CONSUMER_CONTRACT,
    )


def _component(manifest: Mapping[str, object], role: str) -> Mapping[str, object]:
    components = manifest.get("components")
    if not isinstance(components, list):
        raise ValidationError("MO bundle components missing")
    matches = [item for item in components if isinstance(item, dict) and item.get("role") == role]
    if len(matches) != 1:
        raise ValidationError(f"MO bundle component identity drifted: {role}")
    return matches[0]


def _first_parquet(root: Path, candidate: Mapping[str, object], *, role: str | None = None) -> Path:
    files = candidate.get("files")
    if not isinstance(files, list):
        raise ValidationError("MO candidate file ledger missing")
    rows = [item for item in files if isinstance(item, dict) and (role is None or item.get("role") == role)]
    if not rows:
        raise ValidationError("MO candidate has no sample parquet")
    return root / str(rows[0]["path"])


def validate_mo_quote_change_binding(
    datahub_root: Path = DATAHUB_ROOT,
    bundle_root: Path = MO_BUNDLE_ROOT,
) -> MoDeliveryBinding:
    datahub = datahub_root.resolve()
    bundle = bundle_root.resolve()
    _validate_hashes(datahub, MO_UPSTREAM_HASHES)
    _validate_hashes(bundle, MO_BUNDLE_FILE_HASHES)
    manifest = _json(bundle / "manifest.json")
    handoff = _json(bundle / "factorlab_handoff.json")
    certification = _json(bundle / "certification_report.json")
    acceptance = _json(bundle / "primary_acceptance.json")
    bbo_component = _component(manifest, "mo_bbo")
    impact_component = _component(manifest, "partial_impact")
    if (
        manifest.get("state") != "READY"
        or manifest.get("dataset_version") != MO_BUNDLE_VERSION
        or manifest.get("dataset_hash") != MO_BUNDLE_DATASET_HASH
        or manifest.get("production_granted") is not False
        or bbo_component.get("dataset_version") != MO_BBO_DATASET_VERSION
        or bbo_component.get("dataset_hash") != MO_BBO_DATASET_HASH
        or bbo_component.get("record_count") != MO_BBO_RECORD_COUNT
        or certification.get("capability_decision") != "granted_research_only"
        or certification.get("fixed_version_only") is not True
        or certification.get("latest_alias_allowed") is not False
        or certification.get("production_granted") is not False
        or acceptance.get("decision") != "PASS_FACTORLAB_CSI1000_V2P1_PRIMARY"
        or acceptance.get("production_granted") is not False
        or handoff.get("time_authority") != "historical_market_replay"
        or handoff.get("receipt_exact_pit") is not False
        or handoff.get("production_granted") is not False
    ):
        raise ValidationError("DataHub MO bundle authority drifted")
    bbo_root = bundle / str(bbo_component["relative_root"])
    impact_root = bundle / str(impact_component["relative_root"])
    bbo_candidate = _json(bbo_root / "candidate_manifest.json")
    impact_candidate = _json(impact_root / "candidate_manifest.json")
    if (
        bbo_candidate.get("depth_mode") != "top_of_book_only"
        or bbo_candidate.get("carrier_type") != "index_option"
        or bbo_candidate.get("dataset_hash") != MO_BBO_DATASET_HASH
        or bbo_candidate.get("record_count") != MO_BBO_RECORD_COUNT
    ):
        raise ValidationError("DataHub MO BBO candidate drifted")
    bbo_path = _first_parquet(bbo_root, bbo_candidate)
    impact_path = _first_parquet(impact_root, impact_candidate, role="post_trade_response")
    bbo_fields = set(pq.ParquetFile(bbo_path).schema_arrow.names)
    required_bbo = {
        "event_id",
        "instrument_id",
        "market_observed_at",
        "valid_from",
        "valid_until",
        "bid_price_1",
        "ask_price_1",
        "bid_size_1",
        "ask_size_1",
        "depth_mode",
        "quote_change_semantics_proven",
        "source_sequence",
    }
    if not required_bbo.issubset(bbo_fields):
        raise ValidationError("DataHub MO BBO schema is incomplete")
    impact_file = pq.ParquetFile(impact_path)
    impact_fields = set(impact_file.schema_arrow.names)
    required_impact = {
        "direction_status",
        "impact_status",
        "true_counterfactual_impact_ready",
    }
    if not required_impact.issubset(impact_fields):
        raise ValidationError("DataHub MO impact schema is incomplete")
    sample = impact_file.read_row_group(0, columns=sorted(required_impact)).slice(0, 128).to_pylist()
    if not sample or any(
        row["direction_status"] != "trade_direction_unidentified"
        or row["impact_status"] != "partially_identified"
        or row["true_counterfactual_impact_ready"] is not False
        for row in sample
    ):
        raise ValidationError("DataHub MO residual impact boundary drifted")
    if {"aggressor_side", "order_event_type", "true_ofi"}.intersection(bbo_fields):
        raise ValidationError("MO quote-change state cannot silently claim order-event semantics")
    return MoDeliveryBinding(
        bundle_version=MO_BUNDLE_VERSION,
        bundle_dataset_hash=MO_BUNDLE_DATASET_HASH,
        mo_bbo_dataset_version=MO_BBO_DATASET_VERSION,
        mo_bbo_dataset_hash=MO_BBO_DATASET_HASH,
        mo_bbo_record_count=MO_BBO_RECORD_COUNT,
        continuous_quote_change_bbo_ready=True,
        l1_quote_change_ofi_ready=True,
        bounded_l1_marketable_execution_ready=True,
        partial_impact_ready=True,
        true_order_event_ofi_ready=False,
        true_counterfactual_impact_ready=False,
        historical_market_replay_only=True,
        production_authority=False,
    )


__all__ = [
    "DATAHUB_ROOT",
    "ETF_OPTION_CONTRACT_UNIT",
    "ETF_OPTION_FEE_RMB_PER_CONTRACT_SIDE",
    "ETFOptionTradeCost",
    "KLINE_ACCEPTANCE_SNAPSHOT",
    "KLINE_CONSUMER_CONTRACT",
    "KLINE_INTERVALS",
    "KLINE_PRODUCTS",
    "MO_BUNDLE_ROOT",
    "KlineDeliveryBinding",
    "BoundedL1MarketableFill",
    "MoDeliveryBinding",
    "build_on_demand_kline_cli_command",
    "compute_l1_quote_change_ofi",
    "price_bounded_l1_marketable_fill",
    "price_etf_option_trade_cost",
    "validate_mo_quote_change_binding",
    "validate_on_demand_kline_binding",
    "validate_on_demand_kline_payload",
]
