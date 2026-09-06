# 云端—本地沟通记录

> 本文按仓库 `AGENTS.md` 的云端—本地交接协议维护。当前协作协议已由用户明确启用。
>
> 执行优先级仍为：当前云端会话可执行 → 本地大模型 → GitHub Actions。用户已明确 Actions 当前无可用额度，因此不得为研究任务启动、重跑或用 push 试探 Actions。

---

## CL-20260906-001 — 历史误交接：v0.5.2 formal six-view

**状态：SUPERSEDED / DO NOT EXECUTE**

该任务曾误把历史 v0.5.2 run 当成当前断点。后续证据已闭合 v0.5.2，不得据此回退或重跑。

---

## CL-20260906-002 — v0.6.0 qualified financial identity 五视图审计

**状态：COMPLETED / CLOUD REVIEWED — Route M**

冻结上游：`v0.5.2 exact-ridge + v0.5.4 full-cycle qualification`。

本地曾执行正式五视图 replay，云端随后验收并裁决 Route M：exclusive packing 必须永久保持 downstream，但 canonical qualified identity 自身在 harmless 5m slicing 上仍 materially unstable。

关键 controls：

- qualified: `734 / 691 / 691 / 721 / 746`
- canonical: `712 / 673 / 678 / 700 / 728`
- strict matches offset0 vs1..4: `180 / 129 / 129 / 184`
- main unmatched: `531 / 583 / 582 / 527`
- ambiguity: `1/1, 0/0, 1/0, 1/1`
- v0.6.0 identity prefix: 15/15 PASS, rewrite 0

正式结果：`docs/research/two_wave_qualified_identity_results_v060.md`。

---

## DATA_AVAILABILITY — 现行规则

仓库已经跟踪全部 development parquet；“GitHub connector 不能文本预览 parquet”**不是缺数据**。

只有两种情况可以因执行问题 handoff：

1. required repo path 实际不存在 / hash 不一致；或
2. 当前云端会话对冻结步骤发生真实执行失败，并记录 traceback / exit code。

2026-09-06 后续已证明，普通 Chat 的 shell 与 GitHub connector 是不同执行面：GitHub connector 可正常读取研究源码，但 shell 无 GitHub outbound TCP；二进制数据可由用户作为 Chat 文件输入进入当前 runtime。以后应区分“代码访问”“binary transport”“runtime dependency/内存”三个问题，不得混称为 GitHub 不可达。

---

## CL-20260906-003 — v0.6.1 unmatched-identity decomposition 五视图正式审计

### 最终状态

- 云端预分析：`COMPLETED`
- 冻结协议：`COMPLETED`
- evaluator 实现：`COMPLETED`
- frozen implementation commit：`bda82c29103080f69f36d7848b40216088895b3a`
- 原始 handoff：`CANCELLED — cloud execution became possible after user supplied binary data to Chat`
- 本地执行：`NOT REQUIRED / DO NOT EXECUTE`
- 云端真实 replay：`COMPLETED`
- 云端 decomposition review：`COMPLETED`
- overall morphology：`morphology_replication_not_yet_accepted`
- operational baseline：`v0.4.3`

### 为什么原 handoff 被取消

CL-003 最初因为当前 Chat shell 无 GitHub TCP、GitHub connector 又不能把 parquet binary 放入 Python runtime，而被标记等待本地执行。

用户随后直接把仓库 main ZIP 上传到当前 Chat。五个 frozen native-5m parquet 因而进入当前 runtime；研究源码则直接从 GitHub frozen research commit 读取。用户指出“代码并没有丢，GitHub 研究分支仍可读”，该纠正成立。

因此 Protocol 2 的最高优先级“当前云端会话直接执行”重新变得可行，本地 handoff 自动撤销。**本地模型不得再执行 CL-003。**

### 执行证据边界

本轮由 ChatGPT 网页 Chat 当前 cloud runtime 实际执行；没有新 GitHub Actions，也没有采用本地模型的结果。

数据：用户上传 ZIP 中的 frozen parquet；五个 SHA256 / rows / 2015-01-05—2020-12-31 date range 全部与 `data/manifest.json` 一致；无 resample、无 2021+、fresh OOS=false。

研究代码：来自 frozen commit `bda82c29103080f69f36d7848b40216088895b3a`。历史 artifact 已含源码快照的核心文件，先以 Git blob SHA 对 frozen commit 做逐文件验证再复用；v0.6.0/v0.6.1 evaluator 直接读取 frozen commit。

当前 Chat 不是完整 branch checkout，且 Python 3.13 无 `pyarrow` package，所以该执行**不是整仓字节级原样重放**。只属于 runtime 的 execution bridges：

1. read-only minimal Parquet reader for shipped flat PyArrow/ZSTD/dictionary files；
2. 原 runner 同时持有五个 full reconstructed views 时 OOM，真实 exit `137`；之后使用 offset0 常驻、offset1..4 逐个 build/audit/save/release 的两视图 streaming orchestration；
3. filtered-extremum survival 的全节点扫描替换为同定义的 `(level, kind, time)` 索引 + ±5m bisect；使用前原扫描 vs 索引版 100 组 random equivalence **100/100 PASS**。

以上 bridge 均未提交 research source，未改变 attribution order、5m tolerance、mutual-unique relation、ridge linking、tuple-birth death certification、qualification、direction 或 outcome logic。

### 测试 / controls

- focused governance tests：**29/29 PASS**
- v0.6.0 + v0.6.1 helper tests：**17/17 PASS**
- unchanged `scripts/validate_theme_package.py`：当前 Chat 因顶层缺 `pyarrow.parquet` package 未原样 PASS；保留 runtime caveat，不得写成 PASS
- offset0 behavioral identity checkpoint：`38,049 evaluated / 734 qualified / 404 legacy selected / 38,636 tuple births / 712 canonical`
- streaming v0.6.1 replay：exit **0**

Frozen five-view controls 全部精确复现：

```text
qualified: 734 / 691 / 691 / 721 / 746
canonical: 712 / 673 / 678 / 700 / 728
offset1: matches 180, ambiguity 1/1, unmatched 531/492
offset2: matches 129, ambiguity 0/0, unmatched 583/549
offset3: matches 129, ambiguity 1/0, unmatched 582/571
offset4: matches 184, ambiguity 1/1, unmatched 527/543
```

### v0.6.1 正式 decomposition

四组 comparisons 共 `2,223` unmatched pair-observations：

| primary attribution | count | fraction |
|---|---:|---:|
| **post_tuple_birth_loss** | **789** | **35.49%** |
| filtered_extremum_survival_mismatch | 496 | 22.31% |
| qualification_survival_loss | 481 | 21.64% |
| tuple_topology_or_death_certification_mismatch | 355 | 15.97% |
| birth_scale_path_shift | 69 | 3.10% |
| birth_scale_path_ambiguous | 27 | 1.21% |
| qualified_strict_edge_nonmutual | 3 | 0.13% |
| evaluated_identity_nonmutual | 2 | 0.09% |
| tuple_identity_nonmutual | 1 | 0.04% |

raw-evaluated / filtered-tuple phase mismatch 都是 0。

### 最大单项的内部定位

789 个 `post_tuple_birth_loss`：

- raw projection displacement = **787**
- projection invalid = 2
- evaluate_pair invalid = 0

即 **99.75%** 是：已经存在 strict-matched filtered exact-ridge tuple counterpart，但当前 `sequential_raw_close_extreme_inside_filtered_phase_bounds` 投影回 raw price 后，对应五个 raw anchors 的 financial identity displacement 超过一根 nominal 5m bar。

这不授权放宽 matcher。下一步应先审计 projection identity 本身。

同时 `filtered_extremum_survival_mismatch + tuple_topology_or_death_certification_mismatch = 38.28%`，qualification survival 也有 21.64%，所以不能把全部 instability 宣称为一个 projection bug。

### 结果入口

正式报告：

`docs/research/two_wave_unmatched_identity_decomposition_results_v061.md`

可审计小产物：

```text
cloud_results/cloud_chat_v061_unmatched_identity_decomposition/summary.json
cloud_results/cloud_chat_v061_unmatched_identity_decomposition/data_identity.json
cloud_results/cloud_chat_v061_unmatched_identity_decomposition/execution_receipt.json
```

当前 Chat 生成过四份 full detail JSON 和 run.log；其 SHA256 已写入 execution receipt。大 detail 不重复搬入 GitHub。

### 云端裁决

v0.6.1 decomposition gate 已闭合。

下一 formal research step 不是 repair，而是**先冻结 raw-projection identity preanalysis/audit**，诊断同一 strict-matched filtered tuple 为什么被映射成不同 raw financial identity。

任何 replacement projection、matcher tolerance、qualification threshold、ridge linking、direction 或 trading 改动，都必须等新的结果前 protocol；v0.6.1 数字本身不授权修改。

---

## 当前唯一有效断点

读取：

1. `CONTINUE_HERE.md`
2. `docs/research/two_wave_unmatched_identity_decomposition_results_v061.md`
3. `cloud_results/cloud_chat_v061_unmatched_identity_decomposition/summary.json`
4. `cloud_results/cloud_chat_v061_unmatched_identity_decomposition/execution_receipt.json`

**CL-001/CL-003 都不得再执行；CL-002 已闭合。新的本地任务只有未来云端出现新的真实执行阻断时才另编号。**
