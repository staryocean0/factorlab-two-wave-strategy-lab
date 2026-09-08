# 云端—本地沟通记录

> 本文按仓库 `AGENTS.md` 的云端—本地交接协议维护。当前协作协议已由用户明确启用。
>
> 执行优先级：当前云端会话可执行 → 本地大模型 → GitHub Actions。用户当前不授权/不需要用 Actions；文档和研究提交使用 `[skip ci]`，不得用 push 试探 Actions 额度。

---

## 历史任务索引

### CL-20260906-001 — v0.5.2 formal six-view

**状态：SUPERSEDED / DO NOT EXECUTE**

### CL-20260906-002 — v0.6.0 qualified financial identity 五视图审计

**状态：COMPLETED / CLOUD REVIEWED — Route M**

正式结果：`docs/research/two_wave_qualified_identity_results_v060.md`。

### CL-20260906-003 — v0.6.1 unmatched-identity decomposition

**状态：COMPLETED IN CLOUD / LOCAL HANDOFF CANCELLED / DO NOT EXECUTE**

正式结果：`docs/research/two_wave_unmatched_identity_decomposition_results_v061.md`。

---

# CL-20260907-004 — 获取 authoritative DataHub 5m bar-support provenance

**状态：COMPLETED / LOCAL FEEDBACK RECEIVED / CLOUD REVIEWED — `authoritative_archive_copy_accepted`**

本地反馈 commit：

`79925a46d8d5df5aff5674cd61c43e5f15a08276`

本地 evidence pack：

`cloud_results/cl_20260907_004_datahub_bar_support_provenance/`

云端 frozen intake gate：

`docs/ops/datahub_bar_support_provenance_intake_protocol_20260907.md`

云端独立复核：

`docs/ops/datahub_bar_support_provenance_cloud_review_20260907.md`

复核结论：

`authoritative_archive_copy_accepted`

Issue #4 已 `completed` 关闭。该状态只解除 DataHub provenance blocker；全局 morphology 仍为 `morphology_replication_not_yet_accepted`。

### Accepted authority

```text
DataHub committed HEAD = ba780790acd8e9a558e4e01f9474b6e79265d818
session-offset implementation ancestor = 2c7b070f38f061378e89c19d183da9ccef9a6c88
whitepaper last-touch ancestor = d31b140e35132911aa6ab164deaa9afcbb02b0ff
symbol = 000852.SH
source_kind = market_index_transaction_derived_1m
dataset_version = bars_cn_index_1m_raw_canonical_market_index_baidu_3s_20000714_20260821_factorlab_unified_missing_day_repaired_v8_20260824
date_range = 2015-01-05..2020-12-31
source_rows = 349,923
2021+ rows = 0
```

Known retained caveat：frozen offset0 parquet 的 `data_contract` 文本写 wall-clock v1，但 authoritative code 对 offset0 走 official v2；official-route replay 对冻结 offset0 全部 70,114 labels/OHLC exact match。不得改 frozen metadata，也不得再用该字段选择 support。

---

# CL-20260908-005 — 执行冻结 v0.6.17 session-aware information-set bounds formal replay

**状态：OPEN / LOCAL EXECUTION REQUIRED / CLOUD REVIEW PENDING**

## 任务边界

本任务不是设计新算法，也不是重新冻结协议。云端已经 results-blind 冻结：

```text
preanalysis:
  docs/research/two_wave_session_aware_information_set_bounds_preanalysis_v0617.md
  blob = 77f54c7a8e3699997450eaad941ed13b1e561b3a

protocol:
  docs/research/two_wave_session_aware_information_set_bounds_protocol_v0617.md
  blob = f0f6acd06c7ccacd331ed9938f77ff68c9519cfa

freeze commit = 61eba4c80215bb07375e59d3c53e8ac2b989ff28
freeze receipt:
  docs/ops/v0617_session_aware_bounds_freeze_receipt_20260908.md
```

formal real-data results 尚未产生。YV/本地执行者只负责**按 frozen protocol 实现/验证并运行 formal replay**。

## 现有 implementation-only 起点

协议冻结后已经存在：

```text
3e49adf2a37c8b947d88ea0f46e17da8537ea074
  src/factor_lab/visual_structure/two_wave/session_aware_information_set_bounds_v0617.py

2f29faf1e09c9fe78eb6fccdf00b88a7d0904eac
  tests/unit/test_two_wave_session_aware_information_set_bounds_v0617.py

a96422d6aff1baff4192ef1c41eef04ef3eed054
  source-identity gate cleanup
```

这些是 frozen protocol 的候选实现，不是新的研究协议。可修复 protocol-conformance implementation bug，但任何修复必须先记录原因，且不得改变 frozen mathematics/data contract。

## 执行前 hard gate

1. 更新/检出 `staryocean0/factorlab-two-wave-strategy-lab` 的 `codex/two-wave-phase1-20260905` 最新状态。
2. 验证上述 preanalysis/protocol blob SHA 未变化；若变化，**停止**并报告，不执行 formal replay。
3. DataHub 使用本地实际工程；验证 committed HEAD/accepted archive lineage。不要把脏工作区未提交规则当作 authority。
4. 必须使用 accepted DataHub source surface：

```text
symbol = 000852.SH
source_kind = market_index_transaction_derived_1m
dataset_version = bars_cn_index_1m_raw_canonical_market_index_baidu_3s_20000714_20260821_factorlab_unified_missing_day_repaired_v8_20260824
date_range = 2015-01-05..2020-12-31
source_rows = 349,923
2021+ = 0
```

5. 不得用 FactorLab `1m_official.parquet`（350,561 行）替代 exact DataHub source，除非另有事前冻结的 exact row-level bridge；当前没有该 bridge。
6. offset0 support 必须按 authoritative official v2；offset1–4 按 wall-clock v1。不要从 frozen offset0 `data_contract` 文本决定构造规则。
7. DataHub `...T09:35:00Z` 在构造函数中是上海墙上时钟 label；不要按 UTC 01:35 做 minute-of-day。

任何 source identity / native identity / support replay mismatch 都必须 fail closed，不能自动修复。

## 必须按顺序执行

### Stage 1 — synthetic / implementation conformance

先运行现有 v0.6.17 tests，并补齐 frozen protocol section 9 要求但现有测试尚未覆盖的 synthetic/topology gates。至少证明：

- m=1..6 generalized vertex TV max；
- variable-step feasible paths coverage；
- C_inf/C_1/C_2 coverage；
- un-enveloped actual source gap 强制 universal bound；
- lunch/overnight 无 source rows 时不制造 fake gap；
- discarded source rows 产生 gap；
- positive price scaling invariance；
- closed-leg future append invariance；
- bound API 不接收 source fine prices/oracle/counterpart/direction/outcome；
- source identity mismatch fail closed；
- audited transition 中 source timestamp duplicate/double-assigned/unclassified fail closed。

测试不通过时停止 real-data interpretation；不得为了通过而修改 frozen protocol。

### Stage 2 — authoritative support topology + native identity gate

使用 DataHub authoritative `assign_intraday_bucket_minute(period=5, offset=k, include_tail_partial=false)` / official equivalent path构建 actual source membership。不要 locally resample 创建新的 5m product。

先证明五个 frozen 5m views：

```text
offset0 = 70,114
offset1 = 67,192
offset2 = 67,192
offset3 = 67,193
offset4 = 67,191
```

对每个 view 必须：

- identical native label set；
- extra/missing labels = 0；
- aligned OHLC mismatch = 0；
- 每根 emitted bar non-empty actual support；
- last support close == native close；
- assigned source closes 全在 native [L,H]；
- every source row between audited native endpoints 被 price-blind topology stage 精确分类，不得 double assignment / silent deletion。

Transition topology 至少记录 frozen protocol section 5 的字段，并将：

- `gap_source_count=0` → `fully_enveloped_transition`
- `gap_source_count>0` → `contains_unenveloped_source_gap`

午休/隔夜的纯 wall-clock elapsed time 不算 gap；只有真实存在但未被 current native bar envelope 覆盖的 source rows 才算 gap。

### Stage 3 — price-blind bound registry

**先生成并持久化 topology + bounds registry，再读取 fine prices/oracle。**

建议将 Stage 3 registry 的 SHA256 / row count / schema 写入 execution receipt，形成明确的 pre-oracle checkpoint。

- fully enveloped transition/leg：严格调用 frozen variable-step bounds；
- leg 只要含一个 un-enveloped source gap：整个 leg 使用 universal `J in [1/N,1]`、profile `[0,log N]`；
- 不删除 structural-gap leg；
- 不根据 oracle 位置收窄任何 interval。

### Stage 4 — oracle validation / tightness descriptive replay

只有 Stage 3 已固定后才允许读取 fine prices/oracle，用于：

- exact N validation；
- J1 coverage；
- C_inf/C_1/C_2 coverage；
- bound width / normalized width；
- oracle position；
- transition/leg topology counts；
- frozen step-count bins；
- strict same-event 29,453；
- both-qualified 482；
- qualification disagreement 699；
- target repaired 80 / agreement 56 / disagreement 24；
- frozen cross-slicer comparison。

任何 coverage failure 是 model/data bug。不得针对失败样本 widening/tuning。

## Frozen upstream control numbers

正式 interpretation 前必须复现：

```text
published identities = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
published raw strict pairs = 8,381 / 5,770 / 6,204 / 9,098 = 29,453
both-qualified = 482
qualification disagreements = 699
target repaired = 80 = 56 agreement + 24 disagreement
fine profile defined = 737,070 published legs
oracle-comparable strict pair-leg observations = 117,805
```

任一 upstream behavioral drift 都停止 interpretation。

## 必须输出

按 frozen protocol section 14 写入：

`cloud_results/cloud_chat_v0617_session_aware_bounds/`

至少包含：

```text
summary.json
support_topology_summary.json
source_identity.json
native_identity.json
synthetic_gate_receipt.json
data_consistency.json
bound_tightness.json
step_count_overlay.json
cross_slicer_bounds.json
strata_overlays.json
execution_receipt.json
```

正式报告：

`docs/research/two_wave_session_aware_information_set_bounds_results_v0617.md`

大型 row-level topology 可留本地，但 `execution_receipt.json` 必须记录 SHA256、row count、schema、确定性生成命令和本地位置。

## 允许的正式裁决

只允许 frozen protocol section 15 中五种：

- `session_aware_bounds_valid_and_ready_for_identifiability_interpretation`
- `session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`
- `session_aware_bounds_cover_oracle_but_are_too_wide_for_identification`
- `session_aware_bounds_fail_support_topology_or_oracle_coverage`
- `mixed_identifiability_requires_more_audit`

不得自行新增“看起来更好”的 verdict。

## 继续禁止

- 不改 frozen preanalysis/protocol；
- 不 promotion `H_end_5`；
- 不 local 1m→5m replacement resample；
- 不删除 structural-gap/session-boundary legs；
- 不 empirical shrink bounds；
- 不新增 concentration point proxy/threshold；
- 不改 matcher/projection/publication/qualification/roughness；
- 不读/优化 direction、第三浪、outcome/P&L、fresh OOS、paper trading、production。

## 本地反馈要求

执行完成后在本 CL-005 后追加实际反馈，至少包括：

1. FactorLab exact commit / implementation changes；
2. DataHub exact committed identity 与 source dataset identity；
3. 全部实际命令、退出码、测试数量；
4. Stage 1–4 gate PASS/FAIL；
5. required outputs 的位置与 hashes；
6. formal adjudication；
7. 所有失败、未验证、runtime bridge；
8. 明确写：`云端复核尚未发生`。

提交到研究分支时使用 `[skip ci]`。不要运行 GitHub Actions。

本地完成 ≠ 云端独立复核；不得自行修改 global morphology state。

---

## 当前唯一有效断点

读取顺序：

1. `AGENTS.md`
2. `CONTINUE_HERE.md`
3. `docs/ops/datahub_bar_support_provenance_cloud_review_20260907.md`
4. `docs/ops/v0617_session_aware_bounds_freeze_receipt_20260908.md`
5. `docs/research/two_wave_session_aware_information_set_bounds_preanalysis_v0617.md`
6. `docs/research/two_wave_session_aware_information_set_bounds_protocol_v0617.md`
7. v0.6.17 helper + tests
8. 本文 `CL-20260908-005`

当前动作：**执行 frozen v0.6.17 formal replay；不要重新设计 v0.6.17。**


---

## 本地反馈 — CL-20260908-005（2026-09-08）

**状态：LOCAL REPORTED / 云端复核尚未发生**

执行身份：本地 Codex controller。工作目录 `/home/starryocean/桌面/量化/factorlab-two-wave-strategy-lab`。研究分支 `codex/two-wave-phase1-20260905`。执行时代码起点 SHA `0edb9cf08b38141b68e513e58020fc8d5cbd8312`。新增 implementation-only runner：`scripts/run_two_wave_session_aware_information_set_bounds_v0617.py`。

未改 frozen preanalysis/protocol。未使用 FactorLab `1m_official.parquet` 作为 source support。未使用 DataHub 脏工作区。GitHub Actions 未运行。未读 direction / 第三浪 / outcome / PnL / 2021+。未自行修改 global morphology state。

### 命令与退出码

| 命令 | 退出码 |
|---|---|
| `pytest -q tests/unit/test_two_wave_session_aware_information_set_bounds_v0617.py` | 0（14 passed） |
| `python scripts/run_two_wave_session_aware_information_set_bounds_v0617.py` | 0 |

### Stage gates

1. Stage 1 synthetic：PASS
2. Stage 2 source/native/topology：PASS（349,923 rows；五个 frozen 5m views label/OHLC/support exact）
3. Stage 3 pre-oracle bounds registry：PASS（737,104 legs 先落盘再读 oracle）
4. Stage 4 oracle：PASS（N mismatch 0，coverage fail 0）

### DataHub identity

```text
HEAD = ba780790acd8e9a558e4e01f9474b6e79265d818
accepted contract archive blob = accb183f695880c5524f7263bfdfae1debe006a0
symbol = 000852.SH
source_kind = market_index_transaction_derived_1m
dataset_version = bars_cn_index_1m_raw_canonical_market_index_baidu_3s_20000714_20260821_factorlab_unified_missing_day_repaired_v8_20260824
date_range = 2015-01-05..2020-12-31
source_rows = 349923
2021+ = 0
```

v8 湖路径中 hardlink 分区的文件内 `dataset_version` 列可能仍是旧 canonical；本 replay 与 CL-004 hive_partitioning 一致，以目录根 v8 为 identity。

### Formal adjudication

`session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`

offset0 gap transitions = 0；offset1–4 各 2,922 个 un-enveloped source-gap transitions；208,744 / 737,104 published legs 进入 universal bound。oracle coverage = 1.0。不得删除这些 legs，也不得把 discarded minutes 并进邻 bar envelope。

正式报告：`docs/research/two_wave_session_aware_information_set_bounds_results_v0617.md`

### Compact outputs

目录：`cloud_results/cloud_chat_v0617_session_aware_bounds/`

| file | sha256 |
|---|---|
| summary.json | 8765c5faced7e5d8c51ce2ab9c8377f4237f8223eb4720eb22d187e79438714a |
| support_topology_summary.json | a170cc43fb5bd97c56e9c8f4232952ac5f918ab141b743439a7e381a36789185 |
| source_identity.json | 077e981c63f76ebe2277bce4c207a0f74570d1e1d5f4117ca627ad4e831bf471 |
| native_identity.json | 1471bd02fa69eb45dd96157ce276fb3451a6e26bff5e2ef045e70771cf74d258 |
| synthetic_gate_receipt.json | 844ae152caca869058dc9f8ceec92a69c181aeeca0f5ac0afc66c2630831a3c8 |
| data_consistency.json | 87ed61b6ae22f82625693d4740b4b5571ac4224192ec23507375eca7814f3656 |
| bound_tightness.json | 99658677a32ea71469146d00fcbef68c7d2238268ca50db4b44dbf31296c2930 |
| step_count_overlay.json | a928ca84463fbd8fff6915ebfd7742d6fa408b24dd6745615edfab936d9700d1 |
| cross_slicer_bounds.json | c645f762807b6a5ae37e49084b90c91b43d484b3896f8290925347719d2dc44b |
| strata_overlays.json | f3f50bfcd5eafe7b73a9d4f0e0c8ce38a87228ac944242412dd6948560bc7a10 |
| execution_receipt.json | c4a837529ee3c478daf364939391a36924571cce01f717a1587c2f5028acca07 |

大型 registry 留本地：

```text
tmp/v0617_local_registries/transition_topology_counts.parquet
  rows=338877 sha256=3519cae59fe4e067c16402f667341009b954ba205a58c186134732cea8aa660f
tmp/v0617_local_registries/published_leg_bounds_pre_oracle.parquet
  rows=737104 sha256=824bbba91b666f49ea44717a6b8aed505e56998b0aadaeaa092e13a05c0e8dc9
```

Runtime bridge：DataHub v8 湖路径 hardlink 分区的文件内 dataset_version 列不是 v8 字符串；identity 按目录根与 CL-004 hive 口径绑定。不是 1m_official 替换，也不是新 5m 产品。

**云端复核尚未发生。**

---

# CL-20260908-006 — T1 transitory-shock supply-only audit

**状态：LOCAL REPORTED / 云端复核尚未发生 / outcomes still sealed**

交接文件：`docs/ops/cl_20260908_006_T1_transitory_shock_supply_handoff.md`

执行身份：本地 Codex controller。同一研究分支 `codex/two-wave-phase1-20260905`，执行时代码 SHA `0edb9cf08b38141b68e513e58020fc8d5cbd8312`。未改 frozen theory/protocol/runner/tests。未跑任何 outcome 脚本。GitHub Actions 未运行。

### Frozen blob verification

```text
docs/research/reversal_mean_reversion_round2_transitory_shock_theory_intake_20260908.md
  792e768ed8d7fb1808583a49f16d42b9c7438f97
docs/governance/reversal_mean_reversion_T1_transitory_shock_supply_protocol_v1.json
  49615926077f1f2e45e08f427f745363581e2e26
scripts/audit_broad_rmr_T1_transitory_shock_supply.py
  9bc4533dacb5914ee63b5d9d82a745694031b917
tests/unit/test_broad_rmr_T1_transitory_shock_supply.py
  e6acd417a74e4164e77f195db739b5328b8e0542
```

### 命令与退出码

| 命令 | 退出码 |
|---|---|
| `pytest -q tests/unit/test_broad_rmr_T1_transitory_shock_supply.py` | 0（8 passed） |
| `python scripts/audit_broad_rmr_T1_transitory_shock_supply.py --output docs/research/local_broad_rmr_T1_transitory_shock_supply_receipt_v1.json` | 0 |

### Source identity

```text
data/development/5m_offset_0.parquet
  rows = 70114
  SHA256 = bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48
data/development/1m_official.parquet
  rows = 350561
  SHA256 = 755217afce9dec383e48cd46d591402fa90dc50897abeb3dc7097c9a18a109d4
symbol = 000852.SH
max day = 2020-12-31
```

此 T1 使用已准入 FactorLab development package，不与 CL-005 的 DataHub 349,923-row source 混用。

### Supply counts

| partition | extreme events | aligned events | minimum | pass |
|---|---:|---:|---:|---|
| BUILD 2015-2018 | 366 | 364 | 150 | true |
| 2019 | 48 | 48 | 50 | false |
| 2020 | 87 | 87 | 50 | true |

BUILD 拒绝原因：`support_count_3=1`，`support_count_4=1`。2019/2020 无 alignment reject。

`within_bar_retrace_fraction` 描述性摘要见 receipt：BUILD mean 0.01393 / median 0；2019 mean 0.01500 / median 0；2020 mean 0.01855 / median 0。

### Supply gate

`T1_current_data_event_supply_insufficient`

2019 aligned events 48 < 50。未降低 5-sigma 阈值，未改 960-bar 窗口，未搜其他 offset，未打开 post-event outcomes。

Receipt：`docs/research/local_broad_rmr_T1_transitory_shock_supply_receipt_v1.json`  
sha256 `fb067ddd2e07b14da9e5e64ee0403830baa14518ee75737ac244023f3c98a5bd`

Flags：

```text
post_event_outcomes_read=false
future_return_read=false
reversal_or_continuation_label_read=false
PnL_read=false
post_2020_rows_read=false
outcome_execution_authorized=false
```

**云端复核尚未发生。**

---

## 当前本地回传后的断点

两个本地任务均已 `local_reported`，彼此独立，均等待云端复核：

1. `CL-20260908-005`：M0 v0.6.17 formal replay 已回传；云端先做 source/blob/gate 独立复核。
2. `CL-20260908-006`：T1 supply 不足（2019 aligned 48<50）；outcomes 仍封闭。云端先做 supply/source/blob 独立复核。不得因 supply 失败而降低阈值。

本地完成 ≠ 云端独立复核。
