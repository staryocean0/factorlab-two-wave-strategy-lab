# 云端—本地沟通记录

> 本文按仓库 `AGENTS.md` 的云端—本地交接协议维护。当前协作协议已由用户明确启用。
>
> 执行优先级：当前云端会话可执行 → 本地大模型 → GitHub Actions。当前任务不需要、也不授权用 GitHub Actions 绕过 DataHub provenance 阻断；保存本文档使用 `[skip ci]`。

---

## 历史任务索引

### CL-20260906-001 — v0.5.2 formal six-view

**状态：SUPERSEDED / DO NOT EXECUTE**

历史误交接，后续证据已经闭合 v0.5.2，不得回退或重跑。

### CL-20260906-002 — v0.6.0 qualified financial identity 五视图审计

**状态：COMPLETED / CLOUD REVIEWED — Route M**

正式结果：`docs/research/two_wave_qualified_identity_results_v060.md`。

### CL-20260906-003 — v0.6.1 unmatched-identity decomposition 五视图正式审计

**状态：COMPLETED IN CLOUD / LOCAL HANDOFF CANCELLED / DO NOT EXECUTE**

本地任务曾因 binary transport/runtime 限制建立；用户随后把 frozen parquet 直接提供给当前 Chat，云端完成真实 replay 与复核，原 handoff 因而取消。正式结果：`docs/research/two_wave_unmatched_identity_decomposition_results_v061.md`。

> 上述历史任务的详细旧版记录仍保存在 Git 历史中；当前文档只保留执行状态与有效入口，避免让已经闭合的旧任务遮蔽当前唯一阻断。

---

## DATA_AVAILABILITY / HANDOFF 现行规则

仓库已跟踪的 development parquet 与外部 DataHub 产品合同是两类不同依赖：

- GitHub connector 不能直接把 parquet 作为 Python runtime 输入，**不等于**仓库数据不存在；
- 但当研究正式要求一个不在当前授权面中的 authoritative 外部 repo/contract/provenance，而当前 artifact 又无法自描述该事实时，这属于真实的外部输入阻断，可以按 Protocol 1 交给本地大模型取证。

任何 handoff 都不得扩大研究权限：不得下载/构造 2021+ fresh OOS，不得把 index signal data 当成可成交收益，不得绕过 morphology gate 进入 direction、third-wave、P&L、paper trading 或 production。

---

# CL-20260907-004 — 获取 authoritative DataHub 5m bar-support provenance

**状态：本地已反馈 / 云端已复核尚未发生**

**云端阻断原因：** 当前 Chat 已重新枚举 linked GitHub installation；可访问面只有现有 FactorLab 相关仓库，没有 `unified_datahub` / `datahub` repository。当前 frozen 5m artifacts 的 `source_minute_count` 仍逐行为空，且没有 exact `support_start/support_end/source_row_ids`。因此云端无法从当前 surface 获得 DataHub 产品真源，也不得用 `H_end_5` 或本地 1m 重采样替代。

**对应 unblock issue：** GitHub issue #4 — `Unblock morphology research: provide authoritative DataHub 5m bar-support provenance`

**云端已冻结的 intake gate：**

`docs/ops/datahub_bar_support_provenance_intake_protocol_20260907.md`

该 gate 是 operations/provenance 验收协议，不是 v0.6.17 morphology 版本。

## 任务目标

请本地大模型在其能访问实际 FactorLab/DataHub 工程与数据环境的前提下，取得足以回答 **DataHub 对 `cn_a_session_wall_clock_offset_v1` 的每根 5m bar 到底使用哪些 source minutes** 的权威证据，并把证据身份、实际执行步骤和输出反馈回来。

满足下面任一 evidence route 即可，不需要三条都做。

### Route A — DataHub 真源合同/实现

取得实际项目 `unified_datahub`，记录：

1. repository remote / repository identity；
2. branch/tag（如有）；
3. exact commit SHA / immutable revision；
4. `docs/modules/history/session-offset-bars-whitepaper.md`；
5. 对应 bar-construction implementation；
6. preferably matching tests/fixtures。

如果 whitepaper 本身已经完全、无歧义地定义每根 bar 的 source support，也仍应报告 implementation/test 路径是否存在；不要自行补写合同里没有的规则。

### Route B — provenance-rich DataHub 5m re-export

如果本地 DataHub 能重新导出当前研究所需 5m products，请只通过 DataHub 的正式构造逻辑执行，不要在 FactorLab/local notebook 中用 1m 重采样重新定义 5m。

每根 bar 至少需要：

- view / offset identity；
- native bar label/end timestamp；
- `source_minute_count`；
- exact `support_start`；
- exact `support_end`；
- `data_contract`；
- source dataset/version identity。

优先同时保留：

- exact source-row IDs；和/或
- exact source timestamps；
- DataHub build commit；
- export command/config/build receipt。

### Route C — authoritative archive/copy

如果实际 DataHub repo 无法直接授权给当前 Chat，可提供其 authoritative contract + implementation + tests 的 archive/copy，但必须记录 source revision 与文件 hash，保证它能追溯回真正项目 DataHub，而不是无来源的手工摘录。

## 本地必须回答的合同问题

请从 authoritative source 中逐项回答，不要从当前 v0.6.16 的 best-fit 指标反推：

1. 5m support interval 在上午/下午 session 内如何定义？
2. support 起止端点的 inclusive/exclusive 规则是什么？
3. bar label、availability time、support_start、support_end 的精确关系是什么？
4. 午休如何切分，是否跨午休聚合？
5. overnight 如何处理？
6. session-edge partial bars 如何处理/丢弃/标记？
7. offset0 与 offset1–4 是否完全同一 support rule，还是存在分别定义？
8. serialized timestamp 与 source support 的 authoritative timezone/clock convention 是什么？
9. 是否能对当前 frozen development 5m rows 唯一确定 exact source support set？如果不能，具体还缺哪项 provenance？

## Frozen identity controls

如果执行 Route B，先验证数据身份，不要在 mismatch 时自动修复。

当前冻结 row counts：

```text
5m_offset_0 = 70,114
5m_offset_1 = 67,192
5m_offset_2 = 67,192
5m_offset_3 = 67,193
5m_offset_4 = 67,191
```

当前 frozen products 声明：

```text
data_contract = cn_a_session_wall_clock_offset_v1
source_kind = market_index_transaction_derived_1m
```

如 DataHub re-export 在 rows / timestamps / OHLC / dataset_version / contract 上与 frozen products 不一致：

- 不要偷偷重排、删样本、改标签或重新 resample 让它“对上”；
- 把 mismatch 单独报告，并给出 DataHub build identity 与差异摘要；
- 该 mismatch 需要云端另行裁决，不能自动算作 unlock。

## 禁止事项

本地任务只做 **provenance acquisition / contract verification**。不要：

- 开 v0.6.17 morphology 算法；
- 把 `H_end_5` 当 authoritative truth；
- 从 `1m_official` 本地重采样创造 replacement 5m；
- 删除 lunch/overnight/session-boundary legs；
- 发明新的 concentration/support proxy；
- 读取或优化 direction、第三浪、outcome/P&L、fresh OOS、paper trading、production。

## 期望反馈

请在同一 CL-20260907-004 记录下反馈，或提供一份可由用户转交给云端的小报告。至少包含：

1. **实际代码/合同身份**：repo、commit、文件路径、必要 hash；
2. **实际数据身份**（若有 re-export）：symbol/role/date range、dataset_version、view row counts；
3. **实际执行命令/步骤与退出码**；
4. **上述 9 个合同问题的答案**，每个答案对应 source file/code/test 证据位置；
5. **输出位置**：contract/archive/report/provenance export 的本地路径或可访问位置；
6. **失败/未验证项**；
7. 若大数据留在本地，给一个 compact manifest + deterministic session-boundary sample；不要为了反馈把全部大文件无必要搬进 GitHub。

## 验收条件

云端收到反馈后，将按：

`docs/ops/datahub_bar_support_provenance_intake_protocol_20260907.md`

执行独立复核。只有 authoritative lineage + support semantics/completeness 真正通过，才会把 issue #4 视为可关闭，并进入：

**results-blind session-aware information-set bounds preanalysis → frozen protocol → real replay**。

本地“已经找到文件/跑完脚本”本身不等于云端已复核通过。

---

## 本地反馈（2026-09-07，本地大模型）

**本地状态：已反馈。云端复核：尚未发生。本地不得代填“云端已复核”。**

执行仓库：`staryocean0/factorlab-two-wave-strategy-lab` 分支 `codex/two-wave-phase1-20260905`。
未改其他 5 个云端主题仓，未改 DataHub git，未开 morphology，未写 replacement 5m。

### 1. 实际代码/合同身份

- DataHub 本地路径：`/home/starryocean/桌面/量化/unified_datahub`
- GitHub remote：**无**。这与云端搜不到 `unified_datahub` 一致。
- branch：`main`
- HEAD：`ba780790acd8e9a558e4e01f9474b6e79265d818`
- session-offset 实现提交：`2c7b070f38f061378e89c19d183da9ccef9a6c88`
- 白皮书最后触及提交：`d31b140e35132911aa6ab164deaa9afcbb02b0ff`
- 权威绑定：**HEAD 已提交 blob**。脏工作区里的分工说明 / `session_clock_continuous` fail-closed 未当作权威。
- 关键文件 sha256 与 git blob SHA1 见 `cloud_results/cl_20260907_004_datahub_bar_support_provenance/SOURCE_IDENTITY.json` 和 `archive/`。

### 2. 实际数据身份

- 未做 Class B 新产品 re-export。
- 诊断源：湖中冻结声明的 1m `dataset_version=bars_cn_index_1m_raw_canonical_market_index_baidu_3s_20000714_20260821_factorlab_unified_missing_day_repaired_v8_20260824`
- symbol=`000852.SH`，role=`development_material`，区间 `2015-01-05..2020-12-31`，**未读 2021+**
- 1m 源行 349923；`source_kind=market_index_transaction_derived_1m`
- 冻结 5m 行数仍为 70114 / 67192 / 67192 / 67193 / 67191
- 用 DataHub `assign_intraday_bucket_minute` 回放：五视图 label 差集为 0，对齐 label 的 OHLC mismatch=0
- 冻结 5m 的 `source_minute_count` 仍全 null，文件未被改写

### 3. 实际执行命令与退出码

```bash
# DataHub 合同测试
cd /home/starryocean/桌面/量化/unified_datahub
PYTHONPATH=src .venv/bin/python -m pytest   tests/unit/storage/test_session_offset_contract.py   tests/unit/storage/test_bars_deriver.py -q --tb=short
# exit 0 ; 33 passed in 0.81s

# 只读身份诊断（不写 data/development）
PYTHONPATH=/home/starryocean/桌面/量化/unified_datahub/src   /home/starryocean/桌面/量化/unified_datahub/.venv/bin/python   cloud_results/cl_20260907_004_datahub_bar_support_provenance/run_identity_diagnostic.py
# exit 0
```

从 HEAD 提取白皮书/实现/测试副本的命令见反馈包 `archive/`。

### 4. 九个合同问题

完整答案：`cloud_results/cl_20260907_004_datahub_bar_support_provenance/contract_answers.md`

最短结论：

1. 上下午独立窗口，5m 由 `assign_intraday_bucket_minute(period=5, offset=k)` 定义。
2. 每个 1m 端标签最多进一个桶；wall-clock 第一桶含 6 个 1m，后续完整桶 5 个；`bar_open_ts` ≠ exact support_start。
3. label 是墙上时钟 end-label；产品无 support_start/end 列；冻结 `available_at=15:30+08:00` 不是 `first_tradable_slot`。
4. 不跨午休；禁止独立 13:00 bar。
5. 无隔夜会话，不跨日聚合。
6. offset>0 丢网格前缀和不完整尾桶；offset0 official 保留 cap 在 session_end 的最后一桶。
7. offset0 走 official v2 路径；offset1–4 走 wall-clock v1。冻结五视图却都标 `cn_a_session_wall_clock_offset_v1`。
8. DataHub 序列化 `T09:35:00Z` 表示上海墙上时钟，不是 UTC 01:35。
9. intended support 可由合同唯一确定；exact actual source set 不能从冻结 5m 单独恢复。同源 1m + 合同函数可恢复，且与冻结 OHLC/label 一致。

### 5. 输出位置

主题仓内（可 push 给云端）：

`cloud_results/cl_20260907_004_datahub_bar_support_provenance/`

1m 湖大数据仍留本地 DataHub lake，未搬进 GitHub。

### 6. 失败 / 未验证项

- DataHub 无 GitHub remote，云端仍不能自己 clone 原仓；只能读本包 archive。
- Route B 未产出带 `source_minute_count/support_start/support_end` 的新 5m 产品；公开 API 对钉死 `dataset_version`+offset fail-closed。
- 未验证 `1m_official.parquet`（350561 行）与湖中 2015–2020 1m（349923 行）的差异；禁止用它重采样 5m。
- 未把脏工作区未提交合同改动当作权威。
- 未关闭 issue #4，未宣称 intake gate 已通过。

### 7. Compact manifest / session-boundary sample

- 摘要：`identity_diagnostic.json`
- 样例：`session_boundary_samples.json`（2015-01-05 与 2020-12-31，offset0–4，早盘第一根/午休前后/下午最后一根/隔夜过渡）

2015-01-05 offset0 第一根：label `09:35`，intended `09:30..09:35`，actual 缺 `09:30`，实际从 `09:31` 起。

---

## 当前唯一有效断点

读取顺序：

1. `CONTINUE_HERE.md`
2. `docs/research/two_wave_bar_support_semantics_results_v0616.md`
3. `docs/ops/datahub_bar_support_provenance_acquisition_status_20260907.md`
4. `docs/ops/datahub_bar_support_provenance_intake_protocol_20260907.md`
5. issue #4
6. 本文 `CL-20260907-004`

当前全局状态保持：`morphology_replication_not_yet_accepted`。
