# 两浪研究继续入口：v0.6.17 已云端冻结，Stage 1 preflight 已完成，等待 authoritative-source formal replay（2026-09-08）

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

## Stage 1 cloud preflight 已执行

正式记录：

`docs/ops/v0617_stage1_cloud_preflight_20260908.md`

云端 shell 尝试直接 clone 当前公开研究分支，实际因 outbound DNS 失败：

```text
exit = 128
Could not resolve host: github.com
```

因此没有伪称整仓 cloud pytest 已通过。GitHub connector 仍可读取精确源码并写入分支，云端完成了 frozen implementation 的静态/数学 preflight，并发现一个真实 protocol-conformance implementation bug：原 `validate_transition_topology()` 无法发现 authoritative source universe 中被 support/gap **同时漏分类**的 timestamp。

已在 formal real-data output 产生之前修复：

```text
5ed707215072076deb502953e534eea5de70b5cc
  exact support+gap source-row partition fail-closed guard

2c3b28bef68da01a616e74b034555e996574406f
  exact-partition + forbidden-input signature tests
```

该修复没有修改 frozen preanalysis/protocol，也没有改变 bound mathematics。

云端 supplemental source-equivalent stress check：

```text
10,000 random feasible variable-step covered paths
J/profile coverage failures = 0

exact partition       = PASS
missing source row    = expected FAIL-CLOSED
unexpected source row = expected FAIL-CLOSED
```

Stage 1 当前裁决：

`implementation_preflight_pass_with_full_local_test_required`

含义：实现 preflight 可继续，但 exact repo full pytest 仍必须由能访问本地仓库/DataHub 的执行环境完成并记录真实 exit code。

另有一个必须 fail-closed 报告的 edge：v0.6.13 `concentration_profile()` 对 `N<2` 定义为 `fewer_than_two_movements`，而 v0.6.17 数学 simplex 在 `N=1` 给退化 0 值。formal runner 必须在 oracle 前报告 `N=1` leg count；如存在，不得把 undefined oracle 强行改写为 0 来制造 coverage。

## 当前 post-freeze implementation

基础 implementation-only commits：

```text
3e49adf2a37c8b947d88ea0f46e17da8537ea074  helper
2f29faf1e09c9fe78eb6fccdf00b88a7d0904eac  synthetic tests
a96422d6aff1baff4192ef1c41eef04ef3eed054  source identity gate
```

云端 Stage 1 preflight corrections：

```text
5ed707215072076deb502953e534eea5de70b5cc  topology exact-partition guard
2c3b28bef68da01a616e74b034555e996574406f  conformance tests
```

文件：

```text
src/factor_lab/visual_structure/two_wave/session_aware_information_set_bounds_v0617.py
tests/unit/test_two_wave_session_aware_information_set_bounds_v0617.py
```

这些都只是 frozen protocol 的实现。formal replay 不得修改冻结数学/数据合同。

## 当前尚未发生

正式结果文件目前不存在：

`docs/research/two_wave_session_aware_information_set_bounds_results_v0617.md`

正式 compact output 目录目前也尚未形成：

`cloud_results/cloud_chat_v0617_session_aware_bounds/`

因此 **v0.6.17 real-data replay 尚未闭合**，不能声称 session-aware bounds 已通过，也不能更新 morphology verdict。

## 唯一下一正式动作

继续执行 `CL-20260908-005`，但本地执行者必须先读取本次 cloud preflight：

`docs/ops/v0617_stage1_cloud_preflight_20260908.md`

执行链固定为：

**full local Stage 1 pytest/conformance → authoritative DataHub support-topology + native identity gates → price-blind bound registry checkpoint → oracle coverage/tightness formal replay → local feedback → cloud independent review。**

必须使用 accepted DataHub 349,923-row source surface；不能把 FactorLab 350,561-row `1m_official` 当 exact source support。

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
5. `docs/ops/v0617_stage1_cloud_preflight_20260908.md`
6. `docs/research/two_wave_session_aware_information_set_bounds_preanalysis_v0617.md`
7. `docs/research/two_wave_session_aware_information_set_bounds_protocol_v0617.md`
8. `src/factor_lab/visual_structure/two_wave/session_aware_information_set_bounds_v0617.py`
9. `tests/unit/test_two_wave_session_aware_information_set_bounds_v0617.py`
10. `docs/ops/cloud_local_communication.md` 中 `CL-20260908-005`

**当前断点不是继续设计 v0.6.17，而是使用修正后的 frozen-protocol implementation 执行 authoritative-source formal replay。**
