#!/usr/bin/env python3
"""Persist the current LAT-channel 15-tool registry view."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for location in (ROOT, ROOT / "src"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

from factor_lab.market_state.tool_registry_v1_5 import (  # noqa: E402
    build_tool_registry_v1_5_payload,
    validate_tool_registry_v1_5_payload,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts/market_state/tool_registry_v1_5",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload = build_tool_registry_v1_5_payload()
    validate_tool_registry_v1_5_payload(payload)
    (args.output_dir / "tool_registry.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = f"""# 市场状态工具注册表 V1.5

- 当前工具数：`{payload['tool_count']}`
- 新增工具：`lowpass_bandpass_lat_channel`（低通带通LAT通道，channel/volatility_channel）
- 直接基础：`{payload['base_registry_version']}`
- 不继承历史表：`{payload['historical_registry_not_inherited']}`
- 原因：`{payload['historical_exclusion_reason']}`
- 生产、动态参数、工具路由权限：全部 `false`

这是当前十五工具的身份与可执行基准注册，不是优先级结论。
"""
    (args.output_dir / "report_zh.md").write_text(report, encoding="utf-8")
    print(json.dumps({"tool_count": payload["tool_count"], "valid": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
