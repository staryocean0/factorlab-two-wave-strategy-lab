#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

echo "[codex-cloud] maintenance at commit $(git rev-parse HEAD)"

python - <<'PY'
import sys
if sys.version_info[:2] != (3, 11):
    raise SystemExit(
        f"Codex Cloud environment must use Python 3.11; got {sys.version.split()[0]}"
    )
PY

python -m pip install -e . "editables==0.6"

bash .codex/cloud_verify.sh

echo "[codex-cloud] maintenance complete"
