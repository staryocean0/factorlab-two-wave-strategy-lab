#!/usr/bin/env python3
"""Shared local/manual-CI verification entrypoint. Never run scientific outcomes."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verification_commands(python: str, static_only: bool) -> list[list[str]]:
    commands = [[python, "scripts/check_repository_consistency.py"]]
    if not static_only:
        commands += [[python, "scripts/validate_theme_package.py"], [python, "-m", "pytest", "-q"]]
    return commands


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static-only", action="store_true", help="Not a substitute for the full required suite")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = {"schema": "two_wave_repository_verification@1.0", "python": sys.version,
              "mode": "static_only" if args.static_only else "full",
              "execution_location": "invoking_environment", "steps": [],
              "scientific_outcomes_run": False, "authority_granted": False,
              "full_regression_executed": False}
    if not args.static_only and sys.version_info[:2] != (3, 11):
        report.update(status="blocked_environment", error="Full verification requires the package's Python 3.11 contract")
        rc = 2
    else:
        rc = 0
        for command in verification_commands(sys.executable, args.static_only):
            start = time.monotonic()
            try:
                proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
                step = {"command": command, "returncode": proc.returncode,
                        "seconds": round(time.monotonic() - start, 3),
                        "stdout": proc.stdout, "stderr": proc.stderr}
            except OSError as exc:
                step = {"command": command, "returncode": 127, "error": str(exc)}
            report["steps"].append(step)
            print(json.dumps(step, ensure_ascii=False), flush=True)
            if command[-3:] == ["-m", "pytest", "-q"]:
                report["full_regression_executed"] = True
            if step["returncode"]:
                rc = 1
                break
        report["status"] = "failed" if rc else ("passed_static_only" if args.static_only else "passed_full")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"verification status: {report['status']}; receipt: {args.report}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
