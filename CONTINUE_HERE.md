# 两浪研究继续入口：v0.6.16 bar-support semantics audit 已闭合（2026-09-07）

当前全局状态：`morphology_replication_not_yet_accepted`；操作基线仍为 **v0.4.3**；PR #1 保持 Draft。Direction/D1/D2/PAWCT、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

## 最近闭合链条

- v0.6.13：step-count normalization 显著削弱 raw-J duration bias，但 native→fine concentration gap 仍 materially 存在；
- v0.6.14：native close-only coarsening response 较稳定但不追踪 hidden fine refinement；
- v0.6.15：native-OHLC structural bounds 的 hidden-path model 被 session/data-consistency gate 拦截；
- v0.6.16：先审计 native 5m bar-support contract，而不是继续猜 session-aware bounds。

## v0.6.16 正式结果

结果前：
- `docs/research/two_wave_bar_support_semantics_preanalysis_v0616.md`
- `docs/research/two_wave_bar_support_semantics_protocol_v0616.md`

正式结果：
- `docs/research/two_wave_bar_support_semantics_results_v0616.md`
- `cloud_results/cloud_chat_v0616_bar_support_semantics/` 下 7 个 protocol-required compact files

正式裁决：

> **`bar_support_contract_not_recoverable_from_available_artifacts`**

### 权威来源链

FactorLab 明确声明 wall-clock bars 由 **DataHub** 构造，`session_offset_defaults.py` 只选择 clocks/menu，不拥有 bar construction。FactorLab 白皮书又把产品真源指向：

`../../unified_datahub/docs/modules/history/session-offset-bars-whitepaper.md`

但当前 linked GitHub installation 不包含项目 `unified_datahub` repository；没有用无关公共同名仓库替代。

### Frozen artifact provenance 不完整

五个 5m 产品都声明：

```text
data_contract = cn_a_session_wall_clock_offset_v1
source_kind = market_index_transaction_derived_1m
```

但 `source_minute_count` 逐行全 null：

```text
offset0 0 / 70,114 non-null
offset1 0 / 67,192
offset2 0 / 67,192
offset3 0 / 67,193
offset4 0 / 67,191
```

导出 schema 也没有 `support_start/support_end/source_row_ids` 等逐 bar support provenance。

### Fixed hypotheses 只做 falsification

`H_end_5`（五个 official 1m labels ending at native label）在五个 views 上 native close **100% 等于候选最后 1m close**；all candidate closes inside native `[low,high]` 也 >99.98%。`H_start_5` 明显被证伪。

但 frozen protocol 禁止把 best-fit relation 当成 DataHub product contract，因此 H_end_5 只记录为 strong plausibility，不得据此修 v0.6.15 guarantee-style bounds。

Offset1–4 相邻 native labels 仍系统包含约 `2,920–2,921` 个 fine-index gap=10 transitions，几乎全部是 lunch/overnight session boundaries；这说明“相邻 native close = 一个 5m source bucket”不能普遍成立。

## 下一 formal action

在继续 deterministic structural bounds 前，必须先取得**权威 bar-support provenance**，至少满足其一：

1. 获取项目 DataHub `session-offset-bars` product contract / implementation；或
2. 由 DataHub 重导出 provenance-rich bars，每根 bar 至少带：
   - `source_minute_count`
   - exact `support_start/support_end`
   - 最好再带 source-row IDs / source timestamps。

未经该证据，不允许本地按 H_end_5 重采样或冻结 support，也不允许删除 session-boundary legs 后继续 bounds。

当前研究数学在这里进入**数据合同依赖点**，不是再造一个 proxy 的问题。
