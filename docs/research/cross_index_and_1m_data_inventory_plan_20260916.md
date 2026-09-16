# Post-R6 data inventory plan

日期：2026-09-16

状态：`INVENTORY ONLY / NO NEW OUTCOME SCREEN`

## 1. Cross-index candidate

首选候选 family 原为 `market_common_vs_idiosyncratic_shock_reversion`。

已盘点 `staryocean0/factorlab-trend-reversion-regime-lab`：其 `data/market/5m/` 当前含 `000688.SH` 与 `000852.SH`，但该仓当前数据治理文件明确写明“没有新的本地交付任务或已授权实证候选”，现有数据仅限明确约束的历史观察。因此本项目不跨仓消费该数据做新 R7 outcome research。

本仓 `data/development/` 只有 `000852.SH`，所以 cross-index family 暂记 `deferred_due_to_upstream_research_authority`，不是科学 falsification。

## 2. Next admissible data asset

本仓 manifest 已明确授权的 development material 包括：

- `data/development/1m_official.parquet`
- rows=`350,561`
- 2015-01-05..2020-12-31
- SHA256=`755217afce9dec383e48cd46d591402fa90dc50897abeb3dc7097c9a18a109d4`
- instrument=`000852.SH`

1m official 是已有 DataHub-built source product，不允许本地制造新的 wall-clock resample。

## 3. Inventory questions before freezing R7

只回答：

1. 1m schema、symbol、日期边界和 source hash 是否与 manifest 一致；
2. 每日 1m row-count distribution 与 exact-1m continuity；
3. 1m `bar_end_shanghai` 是否能按 timestamp identity 与现有 5m official endpoints 对齐；
4. 每个 5m endpoint 之前是否存在足够的连续 1m observations，可支持“intraminute path information”而不重采样价格；
5. 缺失/重复 timestamp 的数量。

禁止在 inventory 中计算 future-return effect、reversal outcome、threshold performance 或 favorable period/sign。

若 inventory 完整，下一科学 identity 才冻结为一个 1m native-path transient-excursion mechanism；若 inventory 不完整，换其它 broad family，不修改数据。
