---
doc_id: WF-HISTORY-SESSION-OFFSET-BARS-001
truth_role: sop
module_primary: history
module_related: []
governed_surface: session-offset / noon-close bars query workflow
---

# 会话相位 / 中午收盘 K 线查询工作流

长期口径见 [`session-offset-bars-whitepaper.md`](session-offset-bars-whitepaper.md)。本文件只写可重放查询步骤。

## 前置

1. DataHub API 可访问，1m raw canonical 已 READY，或按需派生源存在。
2. 不要把官方 latest 或 FactorLab 钉死 15:00 QFQ 改成 noon-close。
3. 日常 `scripts/daily_data_refresh_workflow.py` 不自动物化本产品。

## 查询

60 分钟从 09:35 起：

```bash
datahubctl history bars \
  --symbol 000001 --market cn_a --frequency 60m \
  --start-time 2014-01-02T00:00:00Z --end-time 2014-01-02T15:00:00Z \
  --session-offset-minutes 5
```

15 分钟研究菜单是 +5 / +10，不是 +15：

```bash
datahubctl history bars \
  --symbol 000001 --market cn_a --frequency 15m \
  --start-time 2014-01-02T00:00:00Z --end-time 2014-01-02T15:00:00Z \
  --session-offset-minutes 5
```

中午收盘日线：

```bash
datahubctl history bars \
  --symbol 000001 --market cn_a --frequency 1d \
  --start-time 2014-01-02T00:00:00Z --end-time 2014-01-02T15:00:00Z \
  --close-anchor 11:30
```

验收：

- 不传新参数时，60m 仍是 `10:30 / 11:30 / 14:00 / 15:00`。
- `60m + 5` 只有 `10:35 / 14:05`，没有独立 `13:00`。
- `1d + 11:30` 的 `first_tradable_slot` 是当日 `13:00`，close 不含下午。
- 钉死旧 `dataset_version` 同时传 offset / close_anchor 必须 400。

```bash
PYTHONPATH=src .venv/bin/python -m pytest \
  tests/unit/storage/test_session_offset_contract.py \
  tests/unit/storage/test_bars_deriver.py -q
```
