#!/usr/bin/env bash
set -Eeuo pipefail
trap 'code=$?; echo "[codex-cloud] MAINTENANCE ERROR line=${LINENO} exit=${code} command=${BASH_COMMAND}" >&2; exit "$code"' ERR

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

echo "[codex-cloud] maintenance at commit $(git rev-parse HEAD)"

VENV="$HOME/.cache/factorlab-two-wave-py311"
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "[codex-cloud] cached Python 3.11 venv missing; rebuilding via cloud_setup.sh"
  bash .codex/cloud_setup.sh
  exit 0
fi

PYTHON="$VENV/bin/python"
"$PYTHON" - <<'PY'
import sys
if sys.version_info[:2] != (3, 11):
    raise SystemExit(f"cached venv must be Python 3.11; got {sys.version.split()[0]}")
PY

"$PYTHON" -m pip install "editables==0.6" -e .

echo "[codex-cloud] maintenance complete"
echo "[codex-cloud] parquet verification remains an explicit task command: bash .codex/cloud_verify.sh"
