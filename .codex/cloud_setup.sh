#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

echo "[codex-cloud] repository: $ROOT"
echo "[codex-cloud] commit: $(git rev-parse HEAD)"
echo "[codex-cloud] python: $(python --version 2>&1)"

python - <<'PY'
import sys
if sys.version_info[:2] != (3, 11):
    raise SystemExit(
        f"Codex Cloud environment must use Python 3.11; got {sys.version.split()[0]}"
    )
PY

# Keep setup identical to the research environment already used for local
# replay. Setup runs before the agent phase and has network access in Codex
# Cloud, so all dependencies can be resolved here even when agent internet is
# disabled.
python -m pip install -e . "editables==0.6"

bash .codex/cloud_verify.sh

echo "[codex-cloud] setup complete"
