#!/usr/bin/env bash
set -Eeuo pipefail
trap 'code=$?; echo "[codex-cloud] VERIFY ERROR line=${LINENO} exit=${code} command=${BASH_COMMAND}" >&2; exit "$code"' ERR

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

VENV="$HOME/.cache/factorlab-two-wave-py311"
if [[ -x "$VENV/bin/python" ]]; then
  PYTHON="$VENV/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON="$(command -v python3.11)"
else
  PYTHON="$(command -v python)"
fi

echo "[codex-cloud] verify python: $($PYTHON --version 2>&1)"

"$PYTHON" - <<'PY'
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import sys

if sys.version_info[:2] != (3, 11):
    raise SystemExit(f"expected Python 3.11, got {sys.version.split()[0]}")

for module in ("numpy", "pandas", "pyarrow", "pytest", "factor_lab"):
    importlib.import_module(module)

import pyarrow.parquet as pq

root = Path.cwd()
manifest_path = root / "data/manifest.json"
if not manifest_path.is_file():
    raise SystemExit("data/manifest.json missing from checkout")
manifest = json.loads(manifest_path.read_text())
products = {row["path"]: row for row in manifest["products"]}
required = [f"data/development/5m_offset_{i}.parquet" for i in range(5)]

for rel in required:
    if rel not in products:
        raise SystemExit(f"manifest entry missing: {rel}")
    expected = products[rel]
    path = root / rel
    if not path.is_file():
        raise SystemExit(f"repo checkout missing binary data: {rel}")

    size = path.stat().st_size
    if size != int(expected["file_bytes"]):
        raise SystemExit(
            f"file size mismatch for {rel}: actual={size} expected={expected['file_bytes']}"
        )

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    digest = h.hexdigest()
    if digest != expected["sha256"]:
        raise SystemExit(
            f"sha256 mismatch for {rel}: actual={digest} expected={expected['sha256']}"
        )

    rows = pq.ParquetFile(path).metadata.num_rows
    if rows != int(expected["row_count"]):
        raise SystemExit(
            f"row-count mismatch for {rel}: actual={rows} expected={expected['row_count']}"
        )

    print(f"[codex-cloud] verified {rel}: bytes={size} rows={rows} sha256={digest}")

print("[codex-cloud] five native 5m parquet files match data/manifest.json")
PY
