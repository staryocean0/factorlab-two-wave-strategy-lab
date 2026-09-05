"""DataHub HTTP client for Factor Lab."""

from __future__ import annotations

import re
import time
from collections.abc import Mapping
from datetime import date
from typing import Any, cast
from urllib.parse import quote

import requests

from factor_lab.core.errors import ValidationError
from factor_lab.core.settings import get_datahub_api_url, get_datahub_timeout_seconds

_PATH_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,255}$")
_CUSTOM_INDUSTRY_CONSUMER_CONTRACT = (
    "cn_a_custom_industry_index_construction_grade.v1"
)
_CUSTOM_INDUSTRY_CAPABILITY = (
    "offline_fixed_version_custom_industry_index_construction"
)


def _path_identifier(value: str, *, field: str) -> str:
    """Return one validated, percent-encoded DataHub path segment."""

    normalized = value.strip()
    if not _PATH_IDENTIFIER_RE.fullmatch(normalized):
        raise ValidationError(
            f"{field} must contain only letters, numbers, '.', '_' or '-'"
        )
    return quote(normalized, safe="")


class DataHubClientError(Exception):
    """DataHub API error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class DataHubClient:
    """Thin HTTP client for DataHub data consumption.

    Configuration:
        DATAHUB_API_URL: Base URL without /api/v1 suffix.
            Defaults to http://127.0.0.1:8400 in development/test.
        DATAHUB_TIMEOUT_SECONDS: Request timeout in seconds (default: 30.0)

    Usage:
        client = DataHubClient()
        bars = client.get_history_bars(symbols=["000001"], market="cn_a", ...)
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        *,
        _test_client: Any = None,
    ) -> None:
        self._test_client = _test_client
        if _test_client is not None:
            self._base_url = ""
            self._api_prefix = "/api/v1"
            self._timeout_seconds = timeout_seconds or 30.0
            return
        try:
            resolved_base_url = base_url or get_datahub_api_url()
            resolved_timeout_seconds = (
                timeout_seconds
                if timeout_seconds is not None
                else get_datahub_timeout_seconds()
            )
        except RuntimeError as exc:
            raise DataHubClientError(str(exc)) from exc

        normalized = resolved_base_url.strip().rstrip("/")
        if not normalized:
            raise DataHubClientError("DATAHUB_API_URL is required for DataHub client")
        self._base_url = normalized
        self._api_prefix = "/api/v1"
        self._timeout_seconds = float(resolved_timeout_seconds)

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds

    def _url(self, path: str) -> str:
        if path.startswith(self._api_prefix):
            return f"{self._base_url}{path}"
        return f"{self._base_url}{self._api_prefix}{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | list[tuple[str, str]] | None = None,
        json: dict[str, object] | None = None,
        retry_count: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> dict[str, object]:
        if self._test_client is not None:
            return self._request_via_test_client(method, path, params=params, json=json)

        last_error: Exception | None = None
        for attempt in range(retry_count):
            try:
                response = requests.request(
                    method=method.upper(),
                    url=self._url(path),
                    params=params,
                    json=json,
                    timeout=self._timeout_seconds,
                )
            except requests.Timeout as exc:
                last_error = DataHubClientError(
                    f"DataHub request timed out after {self._timeout_seconds:.1f}s"
                )
                last_error.__cause__ = exc
            except requests.RequestException as exc:
                last_error = DataHubClientError(f"DataHub request failed: {exc}")
                last_error.__cause__ = exc
            else:
                if response.status_code >= 500:
                    last_error = DataHubClientError(
                        f"DataHub API error {response.status_code}: {response.text}",
                        status_code=response.status_code,
                    )
                elif response.status_code >= 400:
                    raise DataHubClientError(
                        f"DataHub API error {response.status_code}: {response.text}",
                        status_code=response.status_code,
                    )
                else:
                    try:
                        payload = response.json()
                    except ValueError as exc:
                        raise DataHubClientError(
                            f"Invalid JSON from DataHub: {response.text[:200]}"
                        ) from exc

                    if not isinstance(payload, dict):
                        raise DataHubClientError(
                            "DataHub response is not a JSON object"
                        )

                    return payload

            if attempt < retry_count - 1:
                time.sleep(retry_delay_seconds * (2**attempt))

        raise last_error or DataHubClientError("Unknown DataHub request failure")

    def _request_via_test_client(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | list[tuple[str, str]] | None = None,
        json: dict[str, object] | None = None,
    ) -> dict[str, object]:
        client = self._test_client
        url = self._url(path)
        if method.upper() == "GET":
            response = client.get(url, params=params)
        elif method.upper() == "POST":
            response = client.post(url, params=params, json=json)
        else:
            raise DataHubClientError(f"Unsupported method in test mode: {method}")

        if response.status_code >= 400:
            raise DataHubClientError(
                f"DataHub API error {response.status_code}: {response.text}",
                status_code=response.status_code,
            )

        payload = response.json()
        if not isinstance(payload, dict):
            raise DataHubClientError("DataHub response is not a JSON object")
        return payload

    def get_instruments(
        self,
        *,
        market: str | None = None,
        instrument_type: str | None = None,
        exchange_segment: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> dict[str, object]:
        """Fetch instrument list from DataHub.

        Args:
            market: Filter by market (e.g., "cn_a")
            instrument_type: Filter by type
                (e.g., "stock", "convertible_bond", "futures", "t0_qdii")
            exchange_segment: Optional DataHub exchange segment filter.
            status: Optional listed/delisted status filter.
            limit: Maximum number of results

        Returns:
            Response envelope with data.items containing instrument records.
        """
        params: dict[str, str] = {}
        if market:
            params["market"] = market
        if instrument_type:
            params["instrument_type"] = instrument_type
        if exchange_segment:
            params["exchange_segment"] = exchange_segment
        if status:
            params["status"] = status
        if limit is not None:
            params["limit"] = str(limit)
        return self._request("GET", "/instruments", params=params)

    def get_history_bars(
        self,
        *,
        symbols: list[str],
        market: str,
        frequency: str,
        start_time: str,
        end_time: str,
        instrument_type: str | None = None,
        quality_policy: str | None = None,
        view: str | None = None,
        dataset_version: str | None = None,
        bar_align: str | None = None,
        session_offset_minutes: int | None = None,
        close_anchor: str | None = None,
        include_tail_partial: bool | None = None,
    ) -> dict[str, object]:
        """Fetch historical bars from DataHub.

        Args:
            symbols: List of instrument symbols
            market: Market identifier (e.g., "cn_a")
            frequency: Bar frequency (e.g., "1d", "1m", "5m")
            start_time: ISO 8601 start timestamp
            end_time: ISO 8601 end timestamp
            instrument_type: Optional instrument type filter
                (e.g., "stock").  Use this when a market has multiple
                instrument namespaces.
            quality_policy: Optional DataHub quality policy override.
            view: Optional DataHub bar view.  Leave unset for DataHub's raw
                canonical default; set to "qfq_canonical" or "hfq_canonical"
                when adjusted prices are required.
            dataset_version: Optional pinned DataHub bars dataset version.

        Returns:
            Response envelope with data.items containing bar records.
        """
        if not symbols:
            raise ValidationError("symbols must not be empty")
        params = {
            "symbols": ",".join(symbols),
            "market": market,
            "frequency": frequency,
            "start_time": start_time,
            "end_time": end_time,
        }
        if instrument_type:
            params["instrument_type"] = instrument_type
        if quality_policy:
            params["quality_policy"] = quality_policy
        if view:
            params["view"] = view
        if dataset_version:
            params["dataset_version"] = dataset_version
        if bar_align:
            params["bar_align"] = bar_align
        if session_offset_minutes is not None:
            params["session_offset_minutes"] = str(session_offset_minutes)
        if close_anchor:
            params["close_anchor"] = close_anchor
        if include_tail_partial:
            params["include_tail_partial"] = "true"
        return self._request("GET", "/history/bars", params=params)

    def get_custom_industry_index_input(
        self,
        *,
        dataset_version: str,
    ) -> dict[str, object]:
        """Fetch metadata for one immutable, index-construction-only input."""

        version = _path_identifier(dataset_version, field="dataset_version")
        return self._request(
            "GET",
            "/history/custom-industry-index-input",
            params={
                "dataset_version": version,
                "consumer_contract": _CUSTOM_INDUSTRY_CONSUMER_CONTRACT,
                "capability": _CUSTOM_INDUSTRY_CAPABILITY,
            },
        )

    def get_custom_industry_index_members(
        self,
        *,
        dataset_version: str,
        l1_name: str | None = None,
        offset: int = 0,
        limit: int = 1000,
    ) -> dict[str, object]:
        """Page bulk members without exposing a single-stock query surface."""

        if offset < 0 or not 1 <= limit <= 1000:
            raise ValidationError("offset must be non-negative and limit must be 1..1000")
        version = _path_identifier(dataset_version, field="dataset_version")
        params = {
            "dataset_version": version,
            "consumer_contract": _CUSTOM_INDUSTRY_CONSUMER_CONTRACT,
            "capability": _CUSTOM_INDUSTRY_CAPABILITY,
            "offset": str(offset),
            "limit": str(limit),
        }
        if l1_name:
            params["l1_name"] = l1_name
        return self._request(
            "GET",
            "/history/custom-industry-index-input/members",
            params=params,
        )

    def get_history_stock_snapshot(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
        market: str = "cn_a",
        dataset_version: str | None = None,
    ) -> dict[str, object]:
        """Reject the retired stock snapshot endpoint deterministically.

        New factor research must use :meth:`get_history_stock_fundamentals`.
        The method remains as a deprecated-read compatibility symbol so old callers
        receive an explicit blocker instead of a silent semantic substitution.
        """
        _ = (symbols, start_date, end_date, market, dataset_version)
        raise DataHubClientError(
            "history/stock-snapshot is retired; use history/stock-fundamentals"
        )

    def get_history_stock_snapshot_coverage(
        self,
        *,
        market: str = "cn_a",
        snapshot_date: str | None = None,
        dataset_version: str | None = None,
    ) -> dict[str, object]:
        _ = (market, snapshot_date, dataset_version)
        replacement = "history/stock-fundamentals/coverage"
        raise DataHubClientError(
            f"history/stock-snapshot/coverage is retired; use {replacement}"
        )

    def get_history_stock_fundamentals(
        self,
        *,
        symbols: list[str],
        start_report_period: str,
        end_report_period: str,
        market: str = "cn_a",
        dataset_version: str | None = None,
    ) -> dict[str, object]:
        """Fetch PIT stock fundamental statements from the current DataHub API."""
        if not symbols:
            raise ValidationError("symbols must not be empty")
        params = {
            "symbols": ",".join(symbols),
            "market": market,
            "start_report_period": start_report_period,
            "end_report_period": end_report_period,
        }
        if dataset_version:
            params["dataset_version"] = dataset_version
        return self._request("GET", "/history/stock-fundamentals", params=params)

    def get_history_stock_fundamentals_coverage(
        self,
        *,
        market: str = "cn_a",
        dataset_version: str | None = None,
    ) -> dict[str, object]:
        """Fetch coverage for the current stock-fundamentals contract."""
        params = {"market": market}
        if dataset_version:
            params["dataset_version"] = dataset_version
        return self._request(
            "GET",
            "/history/stock-fundamentals/coverage",
            params=params,
        )

    def get_history_macro_fundamentals(
        self,
        *,
        series_ids: list[str],
        start_period: str,
        end_period: str,
        market: str = "cn_macro",
        dataset_version: str | None = None,
        as_of: str | None = None,
        include_vintages: bool = False,
        allow_stale_query: bool = False,
    ) -> dict[str, object]:
        """Fetch only publication-lineage-proven macro rows from DataHub.

        Macro observations are unsafe for research when ``available_at`` is
        merely copied from the observation period.  This boundary therefore
        rejects responses until DataHub declares the dataset research-ready
        at query scope and every row carries DataHub's proof plus an evidence
        reference.  DataHub owns the policy vocabulary; Factor Lab validates
        the governed result instead of duplicating that vocabulary locally.
        """
        if not series_ids:
            raise ValidationError("series_ids must not be empty")
        params = {
            "series_ids": ",".join(series_ids),
            "market": market,
            "start_period": start_period,
            "end_period": end_period,
        }
        if dataset_version:
            params["dataset_version"] = dataset_version
        if as_of:
            params["as_of"] = as_of
        if include_vintages:
            params["include_vintages"] = "true"
        response = self._request("GET", "/history/macro-fundamentals", params=params)
        self._validate_macro_publication_lineage(
            response,
            as_of=as_of,
            require_research_ready=not allow_stale_query,
        )
        return response

    @staticmethod
    def _validate_macro_publication_lineage(
        response: Mapping[str, object],
        *,
        as_of: str | None = None,
        require_research_ready: bool = True,
    ) -> None:
        raw_data = response.get("data")
        if not isinstance(raw_data, Mapping):
            raise DataHubClientError("Macro response data must be an object")
        data = cast(Mapping[str, object], raw_data)
        raw_quality = data.get("quality_summary")
        if (
            not isinstance(raw_quality, Mapping)
            or raw_quality.get("readiness_scope") != "query"
            or raw_quality.get("publication_lineage_ready") is not True
        ):
            raise DataHubClientError(
                "Macro query is not publication-lineage research-ready"
            )
        if require_research_ready and raw_quality.get("research_ready") is not True:
            raise DataHubClientError("Macro query is not research-ready")
        raw_items = data.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            raise DataHubClientError("Macro response must contain governed rows")
        for index, raw_item in enumerate(raw_items):
            if not isinstance(raw_item, Mapping):
                raise DataHubClientError(f"Macro row {index} must be an object")
            item = cast(Mapping[str, object], raw_item)
            available_at = str(item.get("available_at") or "").strip()
            observation_date = str(item.get("observation_date") or "").strip()
            evidence_ref = str(item.get("publication_evidence_ref") or "").strip()
            if item.get("publication_lineage_proven") is not True or not evidence_ref:
                raise DataHubClientError(
                    f"Macro row {index} lacks proven publication lineage"
                )
            if not available_at or not observation_date:
                raise DataHubClientError(
                    f"Macro row {index} has unproven publication availability"
                )
            try:
                available_date = date.fromisoformat(available_at[:10])
                observed_date = date.fromisoformat(observation_date[:10])
            except ValueError as exc:
                raise DataHubClientError(
                    f"Macro row {index} has invalid publication dates"
                ) from exc
            if available_date < observed_date:
                raise DataHubClientError(
                    f"Macro row {index} is available before its observation date"
                )
            if as_of is not None:
                try:
                    cutoff = date.fromisoformat(as_of[:10])
                except ValueError as exc:
                    raise DataHubClientError("Macro as_of is not an ISO date") from exc
                if available_date >= cutoff:
                    raise DataHubClientError(
                        f"Macro row {index} violates strict available_at < as_of"
                    )

    def get_history_macro_fundamentals_coverage(
        self,
        *,
        market: str = "cn_macro",
        dataset_version: str | None = None,
    ) -> dict[str, object]:
        """Fetch macro fundamental time-series coverage from DataHub."""
        params = {"market": market}
        if dataset_version:
            params["dataset_version"] = dataset_version
        return self._request(
            "GET",
            "/history/macro-fundamentals/coverage",
            params=params,
        )

    def get_history_dataset(self, dataset_version: str) -> dict[str, object]:
        """Fetch one history dataset manifest from DataHub.

        The manifest is the service-owned handoff for bulk consumers: callers
        can first use :meth:`get_history_datasets` to select a READY adjusted
        dataset, then fetch its manifest/storage URI through this method before
        doing large local reads.
        """
        encoded_version = _path_identifier(dataset_version, field="dataset_version")
        return self._request("GET", f"/history/datasets/{encoded_version}")

    def get_history_universes(
        self,
        *,
        targets: list[str] | None = None,
    ) -> dict[str, object]:
        """Fetch history universe targets from DataHub.

        Args:
            targets: Optional list of target types to filter
                (e.g., ["stock", "futures"])

        Returns:
            Response envelope with data.target_summary and data.universes.
        """
        params: dict[str, str] | list[tuple[str, str]] = []
        if targets:
            params = [("targets", t) for t in targets]
        return self._request("GET", "/history/universes", params=params)

    def get_history_datasets(
        self,
        *,
        market: str | None = None,
        frequency: str | None = None,
        dataset_kind: str | None = None,
        limit: int = 20,
    ) -> dict[str, object]:
        """Fetch available history datasets from DataHub.

        Args:
            market: Filter by market
            frequency: Filter by frequency
            dataset_kind: Optional dataset kind (e.g. bars, fund_nav,
                fund_proxy_nav)
            limit: Maximum number of results (default: 20)

        Returns:
            Response envelope with data.items containing dataset records.
        """
        params: dict[str, str] = {"limit": str(limit)}
        if market:
            params["market"] = market
        if frequency:
            params["frequency"] = frequency
        if dataset_kind:
            params["dataset_kind"] = dataset_kind
        return self._request("GET", "/history/datasets", params=params)

    def get_history_convertible_bond_valuation(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
        market: str = "cn_a",
    ) -> dict[str, object]:
        """Fetch convertible-bond valuation rows from DataHub."""
        if not symbols:
            raise ValidationError("symbols must not be empty")
        params = {
            "symbols": ",".join(symbols),
            "market": market,
            "start_date": start_date,
            "end_date": end_date,
        }
        return self._request(
            "GET", "/history/convertible-bond-valuation", params=params
        )

    def get_history_fund_nav(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
        market: str = "cn_a",
        instrument_type: str | None = None,
        valuation_policy: str | None = None,
        latest_proxy_date: str | None = None,
    ) -> dict[str, object]:
        """Fetch ETF/LOF daily NAV or latest proxy NAV rows from DataHub."""
        if not symbols:
            raise ValidationError("symbols must not be empty")
        params = {
            "symbols": ",".join(symbols),
            "market": market,
            "start_date": start_date,
            "end_date": end_date,
        }
        if instrument_type:
            params["instrument_type"] = instrument_type
        if valuation_policy:
            params["valuation_policy"] = valuation_policy
        if latest_proxy_date:
            params["latest_proxy_date"] = latest_proxy_date
        return self._request("GET", "/history/fund-nav", params=params)

    def get_history_fund_nav_proxy_coverage(
        self,
        *,
        target: str = "t0_qdii",
        market: str = "cn_a",
        latest_proxy_date: str | None = None,
    ) -> dict[str, object]:
        """Fetch DataHub's coverage audit for latest ETF/LOF proxy NAV."""
        params = {"target": target, "market": market}
        if latest_proxy_date:
            params["latest_proxy_date"] = latest_proxy_date
        return self._request("GET", "/history/fund-nav/proxy-coverage", params=params)

    def get_history_transactions(
        self,
        *,
        symbols: list[str],
        start_time: str,
        end_time: str,
        market: str = "cn_a",
        dataset_version: str | None = None,
        instrument_type: str | None = None,
        session_phase: str | None = None,
        include_auction: bool = True,
        limit: int = 10000,
        cursor: str | None = None,
    ) -> dict[str, object]:
        """Fetch ETF/LOF/convertible-bond 3-second transaction rows.

        DataHub exposes these rows as `dataset_kind=transactions`,
        `frequency=3s`.  For reproducible research, callers should discover and
        pin `dataset_version` through :meth:`get_history_datasets` before
        running batch backtests.
        """
        if not symbols:
            raise ValidationError("symbols must not be empty")
        params = {
            "symbols": ",".join(symbols),
            "market": market,
            "start_time": start_time,
            "end_time": end_time,
            "include_auction": str(include_auction).lower(),
            "limit": str(limit),
        }
        if dataset_version:
            params["dataset_version"] = dataset_version
        if instrument_type:
            params["instrument_type"] = instrument_type
        if session_phase:
            params["session_phase"] = session_phase
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/history/transactions", params=params)

    def get_history_transactions_coverage(
        self,
        *,
        market: str = "cn_a",
        dataset_version: str | None = None,
        trading_day: str | None = None,
    ) -> dict[str, object]:
        """Fetch DataHub coverage audit for 3-second transaction datasets."""
        params = {"market": market}
        if dataset_version:
            params["dataset_version"] = dataset_version
        if trading_day:
            params["trading_day"] = trading_day
        return self._request("GET", "/history/transactions/coverage", params=params)

    def submit_download(
        self,
        *,
        symbol_scope: list[str],
        market: str,
        frequency: str,
        start_time: str,
        end_time: str,
        mode: str = "incremental",
        lake_write_policy: str = "commit",
    ) -> dict[str, object]:
        """Submit a download job to DataHub.

        Args:
            symbol_scope: List of symbols to download
            market: Market identifier
            frequency: Bar frequency
            start_time: ISO 8601 start timestamp
            end_time: ISO 8601 end timestamp
            mode: Download mode ("incremental" or "full")
            lake_write_policy: DataHub lake policy ("commit" or "profile_only").

        Returns:
            Response envelope with data.job_id.
        """
        payload: dict[str, object] = {
            "symbol_scope": symbol_scope,
            "market": market,
            "frequency": frequency,
            "time_range": {
                "start_time": start_time,
                "end_time": end_time,
            },
            "mode": mode,
            "lake_write_policy": lake_write_policy,
        }
        return self._request("POST", "/downloads", json=payload)

    def get_job(self, job_id: str) -> dict[str, object]:
        """Get job status from DataHub.

        Args:
            job_id: The job identifier

        Returns:
            Response envelope with data containing status, result_ref, etc.
        """
        encoded_job_id = _path_identifier(job_id, field="job_id")
        return self._request("GET", f"/jobs/{encoded_job_id}")

    def health_live(self) -> dict[str, object]:
        """Check DataHub liveness.

        Returns:
            Response envelope with data.status ("alive" or other).
        """
        return self._request("GET", "/health/live")
