# 两浪研究继续入口：v0.6.17 已云端冻结，等待正式 session-aware bounds replay（2026-09-08）

当前全局状态：`morphology_replication_not_yet_accepted`；操作基线仍为 **v0.4.3**；PR #1 保持 Draft。Direction/D1/D2/PAWCT、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

## 当前真实前沿

v0.6.16 的 DataHub bar-support provenance 阻断已经解除。

`CL-20260907-004` 本地取得 authoritative DataHub contract / implementation / tests archive 和只读 identity diagnostic 后，云端按事前冻结的 intake gate 完成独立复核：

`docs/ops/datahub_bar_support_provenance_cloud_review_20260907.md`

正式 intake adjudication：

`authoritative_archive_copy_accepted`

GitHub issue #4 已以 `completed` 关闭。该关闭只解除外部 provenance blocker，**不等于 morphology acceptance**。

## 权威 DataHub 绑定

冻结 authority：

```text
DataHub committed HEAD = ba780790acd8e9a558e4e01f9474b6e79265d818
session-offset implementation ancestor = 2c7b070f38f061378e89c19d183da9ccef9a6c88
whitepaper last-touch ancestor = d31b140e35132911aa6ab164deaa9afcbb02b0ff
symbol = 000852.SH
source_kind = market_index_transaction_derived_1m
dataset_version = bars_cn_index_1m_raw_canonical_market_index_baidu_3s_20000714_20260821_factorlab_unified_missing_day_repaired_v8_20260824
source date range = 2015-01-05..2020-12-31
DataHub source rows = 349,923
2021+ = 0
```

关键合同语义：

- offset0 使用 official `cn_a_session_end_label_no_noon_partial_v2`；
- offset1–4 使用 `cn_a_session_wall_clock_offset_v1`；
- 上下午独立，不跨午休/隔夜；
- wall-clock offset session 首个完整 bucket 可包含 6 个 1m end labels；后续通常 5 个；真实缺分钟会减少 occupancy；
- `bar_open_ts` 不是 exact support_start；
- DataHub 构造路径里的 `...T09:35:00Z` 是上海墙上时钟标签，不能按 UTC 01:35 做 minute-of-day；
- frozen offset0 parquet 的 `data_contract` 文本仍写 wall-clock v1，但权威 official-route replay 对全部 70,114 labels/OHLC 为 exact identity。该字段作为已知 metadata caveat 保留，**不得用于决定 offset0 support**；
- FactorLab `1m_official.parquet` 有 350,561 行，不能自动替代 accepted DataHub 349,923-row source surface。

## v0.6.17 results-blind freeze

云端 freeze receipt：

`docs/ops/v0617_session_aware_bounds_freeze_receipt_20260908.md`

冻结 artifacts：

```text
docs/research/two_wave_session_aware_information_set_bounds_preanalysis_v0617.md
  git blob = 77f54c7a8e3699997450eaad941ed13b1e561b3a

docs/research/two_wave_session_aware_information_set_bounds_protocol_v0617.md
  git blob = f0f6acd06c7ccacd331ed9938f77ff68c9519cfa

protocol freeze commit = 61eba4c80215bb07375e59d3c53e8ac2b989ff28
```

这些协议在正式 replay 结果出现前已经冻结。后续不能根据 real-data/oracle 结果改协议来让 coverage/tightness 变好；发现协议前提失败时只能 fail closed。

## 已存在的 post-freeze implementation

协议冻结后已经有三个 implementation-only commits：

```text
3e49adf2a37c8b947d88ea0f46e17da8537ea074  helper
2f29faf1e09c9fe78eb6fccdf00b88a7d0904eac  synthetic tests
a96422d6aff1baff4192ef1c41eef04ef3eed054  source identity gate
```

文件：

```text
src/factor_lab/visual_structure/two_wave/session_aware_information_set_bounds_v0617.py
tests/unit/test_two_wave_session_aware_information_set_bounds_v0617.py
```

它们只能作为 frozen protocol 的实现。若 formal execution 发现实现 bug，可修复实现并记录，但不得改变冻结数学/数据合同。

## 当前尚未发生

正式结果文件目前不存在：

`docs/research/two_wave_session_aware_information_set_bounds_results_v0617.md`

因此 **v0.6.17 real-data replay 尚未闭合**，不能声称 session-aware bounds 已通过，也不能更新 morphology verdict。

## 唯一下一正式动作

执行 `CL-20260908-005`：

**按冻结 v0.6.17 protocol，在本地 DataHub authoritative source 环境完成 support-topology identity gates → synthetic gates → formal real replay → oracle coverage / tightness 描述输出。**

输出必须写入冻结协议 section 14 指定的：

`cloud_results/cloud_chat_v0617_session_aware_bounds/`

正式报告：

`docs/research/two_wave_session_aware_information_set_bounds_results_v0617.md`

本地完成后，云端必须独立复核；本地 green run 本身不构成 morphology acceptance。

## 继续禁止

- 不改 frozen preanalysis/protocol；
- 不把 v0.6.16 `H_end_5` 当真值；
- 不用 FactorLab `1m_official` 本地重采样 replacement 5m；
- 不删除 structural-gap / lunch / overnight / session-boundary legs；
- 不根据 oracle 结果收窄 bound；
- 不发明 concentration point proxy / threshold；
- 不改 recognizer / matcher / projection / publication / qualification / roughness；
- 不恢复 direction、第三浪、outcome/P&L、fresh OOS 或交易。

## 下一位执行者读取顺序

1. `AGENTS.md`
2. `CONTINUE_HERE.md`
3. `docs/ops/datahub_bar_support_provenance_cloud_review_20260907.md`
4. `docs/ops/v0617_session_aware_bounds_freeze_receipt_20260908.md`
5. `docs/research/two_wave_session_aware_information_set_bounds_preanalysis_v0617.md`
6. `docs/research/two_wave_session_aware_information_set_bounds_protocol_v0617.md`
7. `src/factor_lab/visual_structure/two_wave/session_aware_information_set_bounds_v0617.py`
8. `tests/unit/test_two_wave_session_aware_information_set_bounds_v0617.py`
9. `docs/ops/cloud_local_communication.md` 中 `CL-20260908-005`

**当前断点不是继续设计 v0.6.17，而是执行已经冻结的 v0.6.17 formal replay。**