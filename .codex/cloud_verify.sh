#!/usr/bin/env bash
set -Eeuo pipefail
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
"$PYTHON" -c 'import sys; assert sys.version_info[:2] == (3, 11), "Python 3.11 required"'
"$PYTHON" scripts/repository_consistency.py --check
"$PYTHON" scripts/validate_theme_package.py
