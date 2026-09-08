# v0.6.17 session-aware information-set bounds：本地 formal replay 结果

日期：2026-09-08

状态：`local_reported` / **云端复核尚未发生**

正式裁决（frozen protocol 五种之一）：

`session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`

操作基线仍为 **v0.4.3**；全局状态仍为 `morphology_replication_not_yet_accepted`。本轮没有修改 matcher、projection、publication、qualification、roughness、direction、outcome、PnL，也没有把 FactorLab `1m_official.parquet`（350,561 行）当作 DataHub source support。

## 1. 结果前冻结与 Stage 1 synthetic gates

```text
preanalysis blob = 77f54c7a8e3699997450eaad941ed13b1e561b3a
protocol blob    = f0f6acd06c7ccacd331ed9938f77ff68c9519cfa
freeze commit    = 61eba4c80215bb07375e59d3c53e8ac2b989ff28
```

`pytest -q tests/unit/test_two_wave_session_aware_information_set_bounds_v0617.py`：退出码 0，14 passed。

现有测试已覆盖 protocol section 9 的 vertex TV、variable-step coverage、universal-gap、zero-source lunch/overnight、exact partition fail-closed、scale invariance、closed-leg locality、forbidden API 与 source-identity gate。未改 frozen protocol。

## 2. Source / native identity

DataHub committed HEAD `ba780790acd8e9a558e4e01f9474b6e79265d818`。赋值函数使用 CL-004 已验收 archive：

`cloud_results/cl_20260907_004_datahub_bar_support_provenance/archive/session_offset_contract.py`

blob `accb183f695880c5524f7263bfdfae1debe006a0`。未使用 DataHub 脏工作区。

```text
symbol = 000852.SH
source_kind = market_index_transaction_derived_1m
dataset_version = bars_cn_index_1m_raw_canonical_market_index_baidu_3s_20000714_20260821_factorlab_unified_missing_day_repaired_v8_20260824
date_range = 2015-01-05..2020-12-31
source_rows = 349,923
2021+ = 0
offset0 construction = official v2
offset1-4 construction = wall-clock v1
```

v8 湖路径中未受 missing-day 影响的分区是从前一 canonical root hardlink 过来的，文件内 `dataset_version` 列可能仍写旧版本。本 replay 与 CL-004 duckdb hive_partitioning 一致：以目录根 v8 为 identity，不以 hardlink 文件内残留列为 identity。

Native identity gate 五个 frozen 5m views 全部通过：label 集合 exact、OHLC mismatch 0、empty support 0、last support close mismatch 0、assigned close outside envelope 0。

```text
5m_offset_0 = 70,114
5m_offset_1 = 67,192
5m_offset_2 = 67,192
5m_offset_3 = 67,193
5m_offset_4 = 67,191
```

## 3. Support topology

338,877 个相邻 native transition。`m` 最大 6，未出现需 fail-closed 的更大 occupancy。

| view | fully enveloped | unenveloped source gap |
|---|---:|---:|
| 5m_offset_0 | 70,113 | 0 |
| 5m_offset_1 | 64,269 | 2,922 |
| 5m_offset_2 | 64,269 | 2,922 |
| 5m_offset_3 | 64,270 | 2,922 |
| 5m_offset_4 | 64,268 | 2,922 |

Gap 行几乎全部是 3 或 4 个真实存在、但未被当前 offset bar 接收的 source minutes（午休/隔夜 dropped partials）。没有 source row 的纯 wall-clock 午休/隔夜不记为 gap。

大表 `tmp/v0617_local_registries/transition_topology_counts.parquet` 留本地，sha256 `3519cae59fe4e067c16402f667341009b954ba205a58c186134732cea8aa660f`。

## 4. Stage 3 price-blind bounds 后才读 oracle

737,104 published legs（184,276 identities × 4）先写入

`tmp/v0617_local_registries/published_leg_bounds_pre_oracle.parquet`

sha256 见 `execution_receipt.json`。随后才用 DataHub source closes 做 oracle。

## 5. Hard controls

```text
published identities = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
published raw strict pairs = 8,381 / 5,770 / 6,204 / 9,098 = 29,453
both-qualified = 482
qualification disagreements = 699
target repaired = 80 = 56 agreement + 24 disagreement
published legs = 737,104
```

无 identity/pair/qualification drift。

v0.6.13 的 `fine profile defined = 737,070` 是旧 n≥2 可用性计数，不是本轮 identity 集合。v0.6.17 对全部 737,104 legs 都注册了 bounds（含 N=1）。v0.6.10 overlay 大小 117,805 仍保留为历史对照；本轮完整 pair-leg 产品是 29,453 × 4 = 117,812。

## 6. Oracle / tightness

- registered N vs actual DataHub fine-step count mismatch = 0
- J / C_inf / C_1 / C_2 coverage failure = 0
- defined oracle legs = 737,104
- full coverage fraction = 1.0

结构 gap 腿全部保留，并用 universal simplex 覆盖，没有按 oracle 收窄。

全样本（含 universal-bound legs）J 宽度：median 0.690，mean 0.639。offset0 无 structural-gap legs；offset1–4 共 208,744 / 737,104 = 28.3% 的 published legs 因至少一段 un-enveloped source gap 进入 universal bound。

## 7. 裁决

允许的五种裁决中，本轮选择：

`session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`

理由：topology 与 oracle coverage 均通过，因此不是 coverage failure；但 offset1–4 的 session-boundary 丢弃是真实的 slicer 信息损失，不是测量噪声，且影响超过四分之一 published legs。这不能通过删除这些 legs 或把它们并进邻 bar envelope 来“修好”。

本结果不授权 qualification 阈值、bound shrinkage、direction、第三浪、outcome/P&L、fresh OOS、paper trading 或 production。

## 8. 产物

紧凑回传：`cloud_results/cloud_chat_v0617_session_aware_bounds/`

大型 row-level registry 留本地，路径与 sha256 写在 `execution_receipt.json`。

**云端复核尚未发生。**
