# 两浪研究继续入口：v0.6.16 已闭合，DataHub provenance acquisition 已穷尽当前可用 surface（2026-09-07）

当前全局状态：`morphology_replication_not_yet_accepted`；操作基线仍为 **v0.4.3**；PR #1 保持 Draft。Direction/D1/D2/PAWCT、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

## 最近闭合链条

- v0.6.13：step-count normalization 显著削弱 raw-J duration bias，但 native→fine concentration gap 仍 materially 存在；
- v0.6.14：native close-only coarsening response 较稳定但不追踪 hidden fine refinement；
- v0.6.15：native-OHLC structural bounds 的 hidden-path model 被 session/data-consistency gate 拦截；
- v0.6.16：native 5m bar-support contract audit，正式裁决 `bar_support_contract_not_recoverable_from_available_artifacts`。

## v0.6.16 正式结果

结果前：
- `docs/research/two_wave_bar_support_semantics_preanalysis_v0616.md`
- `docs/research/two_wave_bar_support_semantics_protocol_v0616.md`

正式结果：
- `docs/research/two_wave_bar_support_semantics_results_v0616.md`
- `cloud_results/cloud_chat_v0616_bar_support_semantics/` 下 7 个 protocol-required compact files

FactorLab 明确声明 wall-clock bars 由 **DataHub** 构造，并把产品真源指向：

`../../unified_datahub/docs/modules/history/session-offset-bars-whitepaper.md`

现有 frozen 5m artifacts 只有：

```text
data_contract = cn_a_session_wall_clock_offset_v1
source_kind = market_index_transaction_derived_1m
```

但 `source_minute_count` 逐行全 null，且没有 exact `support_start/support_end/source_row_ids`。`H_end_5` 虽在五个 views 上给出 100% close-label agreement、>99.98% envelope consistency，但它仍只能作为 plausibility/falsification evidence，不能替代 DataHub product contract。

## 2026-09-07 provenance acquisition attempt 已完成

本轮已把当前 Chat 能自主访问的 evidence surface 全部检查完，并记录在：

`docs/ops/datahub_bar_support_provenance_acquisition_status_20260907.md`

检查结果：

1. linked GitHub installation：完整搜索后没有可访问的 `unified_datahub` / `datahub` repository；
2. owner-level repository enumeration：`staryocean0` 当前可访问 surface 只有 FactorLab 相关 repositories，没有改名后的 DataHub 候选；
3. public GitHub：没有可见的 `staryocean0/unified_datahub`；
4. public web：没有找到权威 `session-offset-bars-whitepaper.md` / `cn_a_session_wall_clock_offset_v1` 项目来源；无关公共同名 DataHub 没有被替代使用；
5. FactorLab branch/archive：只有指向 DataHub 真源的 workflow/whitepaper/reference，没有 vendored authoritative implementation/contract；
6. ChatGPT File Library：再次搜索后仍没有 `unified_datahub` archive、session-offset-bars contract 或 provenance-rich re-export；
7. frozen artifacts：仍不包含逐 bar exact support provenance。

正式 acquisition 状态：

`authoritative_datahub_bar_support_evidence_unavailable_in_current_surfaces`

这意味着当前研究已经到达**外部数据合同依赖点**，不是继续发明 proxy/threshold 可以解决的问题。

## Unblock tracking issue

已创建 GitHub issue **#4 — `Unblock morphology research: provide authoritative DataHub 5m bar-support provenance`**。

Issue #4 是当前唯一 unblock 工单。它不是用来授权降级假设；只有在下述任一权威证据条件真正满足后，研究才恢复。

## 最小解锁条件

满足任意一项即可恢复研究：

1. 连接/授权实际项目 `unified_datahub` GitHub repository，使当前 Chat 至少能读取 `docs/modules/history/session-offset-bars-whitepaper.md`，最好同时可读构造实现与 tests；或
2. 上传/提供 authoritative DataHub contract/implementation 的 archive/copy；或
3. 提供 DataHub provenance-rich 5m re-export，每根 bar 至少包含：
   - `source_minute_count`
   - exact `support_start`
   - exact `support_end`
   - 最好再带 source-row IDs / exact source timestamps。

## 解锁前禁止事项

在权威 provenance 到位前，不允许：

- 把 `H_end_5` 冻结成 authoritative support truth；
- 本地重采样 `1m_official` 重新定义 5m support；
- 删除 lunch/overnight/session-boundary legs 后继续 deterministic bounds；
- 从相邻 native closes 推导 guarantee-style hidden-path support；
- 回到 point-estimate concentration proxy 代替 provenance；
- 恢复 direction、第三浪、outcome/P&L、fresh OOS 或交易。

## 一旦解锁，唯一下一 formal research action

取得权威 support provenance 后，**另开 results-blind session-aware information-set bounds preanalysis + frozen protocol**。新协议必须直接消费 recovered contract/provenance；此前 H_end_5 的 best-fit relation 不自动继承为真值。

**在解锁前，不再开启新的 morphology 算法版本。**
