#!/usr/bin/env python3
"""Metadata-only schema inventory for broad reversal Stage-1.

Does not read row values or compute market outcomes. It reports Parquet schema,
row counts, row-group counts and file identity only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE = ROOT / "cloud_inputs/frozen_research_cache_v065_v0613"
EXPECTED = {
    "published_identities_v065.parquet": "8596622924e92182756162b7bdf0959f6d8ddc2222d6dbc9b4e4379cada9974c",
    "strict_pairs_v065.parquet": "8b3b9477bfb26a591566d19b8571d57dd6e2b2cbe004c38c92e857daadaf8158",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory(path: Path) -> dict:
    pf = pq.ParquetFile(path)
    schema = pf.schema_arrow
    return {
        "path": str(path),
        "sha256": sha256(path),
        "num_rows": int(pf.metadata.num_rows),
        "num_row_groups": int(pf.metadata.num_row_groups),
        "num_columns": int(pf.metadata.num_columns),
        "columns": [
            {"name": field.name, "type": str(field.type), "nullable": bool(field.nullable)}
            for field in schema
        ],
        "metadata_keys": [
            k.decode("utf-8", "replace") if isinstance(k, bytes) else str(k)
            for k in sorted((schema.metadata or {}).keys())
        ],
        "row_values_read": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    cache = args.cache.resolve()
    payload = {
        "schema_id": "factorlab_broad_rmr_stage1_cache_schema_inventory@1.0",
        "research_role": "metadata_only_results_blind_inventory",
        "row_values_read": False,
        "files": {},
    }
    for name, expected_sha in EXPECTED.items():
        p = cache / name
        if not p.exists():
            raise FileNotFoundError(p)
        info = inventory(p)
        if info["sha256"] != expected_sha:
            raise RuntimeError(f"SHA mismatch for {name}: {info['sha256']}")
        payload["files"][name] = info

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
