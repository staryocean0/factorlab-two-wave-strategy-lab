# v0.6.16 native 5m bar-support semantics：正式结果与云端裁决

日期：2026-09-07

状态：`bar_support_contract_not_recoverable_from_available_artifacts`

操作基线仍为 **v0.4.3**；全局状态仍为 `morphology_replication_not_yet_accepted`。本轮只审计 bar-support contract/provenance；没有修改数据、identity、matcher、projection、publication、qualification、direction、outcome 或 trading logic。

## 1. 结果前冻结

- `docs/research/two_wave_bar_support_semantics_preanalysis_v0616.md`
- `docs/research/two_wave_bar_support_semantics_protocol_v0616.md`

冻结规则明确规定：只有 DataHub implementation/product contract 或 artifact 明文 support provenance 才能建立权威 bar support；supplied-1m 上的 best fit 只能用于 falsification，不能升格为 contract。

## 2. 权威来源链当前不闭合

FactorLab `session_offset_defaults.py` 明确声明：

- wall-clock bars 由 **DataHub** 构造；
- FactorLab 只选择 research menu / clocks，不得本地重采样；
- offset contract 为 `cn_a_session_wall_clock_offset_v1`；
- offset0 使用 `session_end_label_v2`，offset1–4 使用 `session_wall_clock`；
- official 1m close clocks 为 09:31–11:30 / 13:01–15:00；5m offset close clocks 在上午/下午 session 内分别生成。

`unified_offset_data_and_backtest_whitepaper.md` 又明确把产品真源指向外部 `../../unified_datahub/docs/modules/history/session-offset-bars-whitepaper.md`。

当前 linked GitHub installation 中没有该项目 DataHub repository；全局搜索返回的同名公共仓库与本项目无关，因此没有被替代使用。

## 3. Frozen parquet 产品缺少逐 bar support provenance

五个 5m products 的固定事实：

```text
data_contract   = cn_a_session_wall_clock_offset_v1
source_kind     = market_index_transaction_derived_1m
dataset_version = bars_cn_index_1m_raw_canonical_market_index_baidu_3s_20000714_20260821_factorlab_unified_missing_day_repaired_v8_20260824
```

但 `source_minute_count` 逐行全部为 null：

```text
offset0  0 / 70,114 non-null
offset1  0 / 67,192
offset2  0 / 67,192
offset3  0 / 67,193
offset4  0 / 67,191
```

导出 schema 也没有 `support_start/support_end/source_row_ids` 一类字段。现有 timestamp/bar_end 字段描述 label/availability，而不是 source support interval。

因此 artifact 自身不是 provenance-complete 的 nested-bar product。

## 4. Fixed support hypotheses：数据强烈支持 end-label，但不能变成 contract

### H_end_5

对同一 session 内、以 native label `t` 结束的五个 official-1m close rows：

| view | evaluable | native close = candidate last close | all five 1m closes inside native [L,H] |
|---|---:|---:|---:|
| offset0 | 70,108 | 70,108 | 70,099 |
| offset1 | 67,187 | 67,187 | 67,176 |
| offset2 | 67,188 | 67,188 | 67,181 |
| offset3 | 67,187 | 67,187 | 67,179 |
| offset4 | 67,187 | 67,187 | 67,179 |

Close-label agreement为 100%；OHLC-envelope consistency >99.98%。

### H_start_5

明显不成立：native close 与候选最后一根 1m close 只在几十个 bar 上偶然相等，且大多数候选 closes 不在 native envelope 内。

### H_prev_open_5

对相邻 native labels 在 official-1m index 上恰好相差 5 的 transitions，与 H_end_5 基本一致；但 offset1–4 每个 view 约 2,920 个午休/隔夜 transition 的 index gap 为 10，因此不能把“相邻 native closes”普遍解释为一个 5-minute source bucket。

这些结果只**证伪 H_start_5 并支持 H_end_5 的 plausibility**；按 frozen governance，不足以证明 DataHub 的正式 support contract。

## 5. Session-boundary structure

Offset1–4 的典型结构：

```text
fine-index gap = 5   : ~64,263–64,264 transitions
fine-index gap = 10  : ~2,920–2,921 transitions
```

其中 gap=10 基本由：

```text
lunch     1,461
overnight ~1,459
```

组成。例如 offset1：11:26→13:06 与 14:56→次日09:36。

这与 FactorLab close-clock contract“上午/下午 session 独立生成 offset bars、session-edge partials 不在完整 grid 中”一致，但仍不能告诉我们每根 exported OHLC 的 exact source-row support。

## 6. 正式裁决

> **`bar_support_contract_not_recoverable_from_available_artifacts`**

解释：

1. DataHub 被明确指定为 wall-clock bar construction owner；
2. 本会话无法访问项目 DataHub product source/whitepaper；
3. frozen 5m artifacts 没有逐 bar source support provenance，`source_minute_count` 全 null；
4. H_end_5 在数据上极强一致，但 protocol 禁止用 best-fit oracle relation 代替 product contract；
5. 因此不能据此修复 v0.6.15 structural bounds，更不能本地重采样重新定义 support。

## 7. 工程结论 / 下一步

在继续 guarantee-style hidden-path bounds 之前，必须满足至少一项：

- 获取项目 DataHub 的 `session-offset-bars` product contract / implementation；或
- 由 DataHub 重新导出 provenance-rich bars，逐 bar 至少保留 `source_minute_count`、exact support start/end，并最好保留 source-row IDs / source timestamp list。

取得权威 support 后，才能另开 session-aware information-set bounds protocol。未经该证据，不允许把 H_end_5 直接冻结为生产/研究真值。

当前全局状态仍为：`morphology_replication_not_yet_accepted`。
