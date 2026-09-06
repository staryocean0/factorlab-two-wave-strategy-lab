#!/usr/bin/env bash
set -Eeuo pipefail
trap 'code=$?; echo "[codex-cloud] ERROR line=${LINENO} exit=${code} command=${BASH_COMMAND}" >&2; exit "$code"' ERR

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

echo "[codex-cloud] repository: $ROOT"
echo "[codex-cloud] commit: $(git rev-parse HEAD)"
echo "[codex-cloud] PATH: $PATH"

choose_python311() {
  local candidate
  for candidate in python3.11 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)
PY
      then
        command -v "$candidate"
        return 0
      fi
    fi
  done

  echo "[codex-cloud] Python 3.11 was not found." >&2
  echo "[codex-cloud] Configure Codex Environment -> Set package versions -> Python 3.11, then Reset cache." >&2
  command -v python >/dev/null 2>&1 && python --version >&2 || true
  command -v python3 >/dev/null 2>&1 && python3 --version >&2 || true
  ls -1 /usr/bin/python* 2>/dev/null >&2 || true
  return 21
}

BASE_PYTHON="$(choose_python311)"
echo "[codex-cloud] base python: $BASE_PYTHON ($($BASE_PYTHON --version 2>&1))"

VENV="$HOME/.cache/factorlab-two-wave-py311"
if [[ ! -x "$VENV/bin/python" ]] || ! "$VENV/bin/python" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)
PY
then
  echo "[codex-cloud] creating venv: $VENV"
  rm -rf "$VENV"
  "$BASE_PYTHON" -m venv "$VENV"
fi

PYTHON="$VENV/bin/python"
echo "[codex-cloud] venv python: $($PYTHON --version 2>&1)"

"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install "editables==0.6" -e .

# Setup runs in a separate shell. Persist the venv for the later agent phase.
BASHRC="$HOME/.bashrc"
MARKER="# factorlab-two-wave Codex Cloud"
touch "$BASHRC"
if ! grep -Fq "$MARKER" "$BASHRC"; then
  {
    echo ""
    echo "$MARKER"
    echo "export PATH=\"$VENV/bin:\$PATH\""
    echo "export PYTHONUNBUFFERED=1"
  } >> "$BASHRC"
fi

"$PYTHON" - <<'PY'
import importlib
mods = ("numpy", "pandas", "pyarrow", "pytest", "factor_lab")
for name in mods:
    mod = importlib.import_module(name)
    print(f"[codex-cloud] import ok: {name} {getattr(mod, '__version__', '')}")
PY

echo "[codex-cloud] dependency setup complete"
echo "[codex-cloud] run 'bash .codex/cloud_verify.sh' in the first cloud task to verify shipped parquet identities"
