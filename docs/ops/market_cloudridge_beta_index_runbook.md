# 市场相关性 Beta 强度云指数运行手册

日期：2026-05-20
状态：权威、可运维、生命周期中立
范围：DataHub 全市场 beta 强度云扫描，以及等权滚动指数物化

## 权威产品边界

这不再是示例脚本。指数名称固定为：

```text
中文名：云脊A股Beta指数
English: CN-A CloudRidge Beta Index
Symbol: CN_A_CLOUDRIDGE_BETA_EQW
```

“云脊”指市场 beta 云的脊线：它用于描述全市场共振的骨架，而不是交易建议或市值加权基准。

当前自建指数产品为：

```text
DataHub full-market A-share PIT daily bars
  -> raw close-to-close returns
  -> full-market Pearson correlation matrix
  -> per-stock average Fisher-z correlation strength
  -> Dominant Beta Strength Cloud left-shoulder selection
  -> equal-weight / price-neutral constituent pool
  -> weekly or daily rolling levels
  -> linear/log K-line rendering
```

四个载体必须保持同步：

| 载体 | 权威依据 |
|---|---|
| 方法白皮书 | [`cloudridge_beta_index_whitepaper.md`](cloudridge_beta_index_whitepaper.md) 固定数学公式、产品边界、一等资产准入和等权归一化口径。 |
| 运行手册 | 本文固定运维流程、历史导出、GPU/CPU 参数、runtime collection 迁移和生成 artifact。 |
| 代码 | `scripts/datahub_cloudridge_beta_index_rebalance.py` 与 `cloudridge_beta_index_service.py / beta_strength_cloud_scan_service.py` 实现同一套公式。 |
| 测试 | `test_market_correlation_cloudridge_beta_*`、`test_datahub_cloudridge_beta_index_rebalance_script.py`、API/CLI/UI 测试锁定公开行为。 |

不要把已被取代的图组件选择器重新引入生产 payload。公共控制界面使用 CloudRidge 命名（`/cloudridge_beta_indexes` 和 `market-correlation cloudridge-index`）。旧版 import shim 和旧版 runtime collection fallback 只用于读取历史记录；新写入使用 `cloudridge_beta_index_*` collection 和 CloudRidge 模块名。活跃本地 runtime 应使用 `scripts/migrate_cloudridge_runtime_collections.py` 进行物理迁移，以便备份后退役 collection 为空。fallback 留在代码中仅用于尚未迁移的旧备份或复制出来的 runtime 存储。

### 一等市场资产准入

`CN_A_CLOUDRIDGE_BETA_EQW` 是 `asset_kind=self_built_index`、`source_family=price_volume` 的标准化市场点位序列。完整准入字段和 source-universe 边界见 [云脊A股Beta指数白皮书](cloudridge_beta_index_whitepaper.md)。

运行层只需确认：导出的 level/OHLC 行不得绕过标准市场数据门禁，也不得把分析师预期、新闻/NLP、事件 alpha 或另类数据包装成自建指数输入。

## 2026-05-20 产品化滚动界面

CloudRidge 现在是专用的滚动 beta-cloud 指数族。公共控制界面为 `cloudridge_beta_indexes` / `market-correlation cloudridge-index`，权威选择器是 **Dominant Beta Strength Cloud v3**，而不是图组件选择器。

- REST：`/api/v1/cloudridge_beta_indexes`
- CLI：`factor-lab market-correlation cloudridge-index create|rebalance|rebalance-range|levels|constituents|rebalances|render`
- Workbench：Latent Factor Lab（隐性因子实验室） → Market Backbone Index（行情骨架指数） → Beta Strength Cloud Index（Beta 强度云指数）

### 权威数学公式

完整公式以 [云脊A股Beta指数白皮书](cloudridge_beta_index_whitepaper.md) 为准。运行时必须保持：

- `as_of_date=D` 只使用不晚于 `D` 可见的 PIT 数据；
- 常规 PIT/live dataset 使用 `available_at <= as_of_date`；历史回填可显式使用 `--availability-mode trading_day`；
- eligible asset 满足 `min_periods=max(60, ceil(0.8 * lookback))`，测试覆盖除外；
- selector 为 Fisher-z 平均相关强度的 beta cloud 左肩，非 graph component、threshold grid 或 TopK；
- level 计算为收益等权、价格中性。

### 已移除旧图选择器

已被取代的图组件诊断和 soft-cap 兼容字段已从新的生产 payload 中移除。历史细节仅保留在 `.omx/` 研究 artifact 中，用于审计复现。

滚动指数命令示例：

```bash
factor-lab market-correlation cloudridge-index create \
  --name cn_a_dominant_beta_strength_cloud_eqw \
  --universe-ref cn_a \
  --lookback-window 120 \
  --min-periods 96 \
  --coverage-floor 0.50 \
  --json

factor-lab market-correlation cloudridge-index rebalance cldrgidx_xxx \
  --dataset-version bars_cn_a_1d_raw_canonical_aca59a04112c \
  --as-of-date 2026-05-15 \
  --json

factor-lab market-correlation cloudridge-index render cldrgidx_xxx \
  --output-prefix .omx/research-notes/cn_a_beta_strength_cloud_20260515 \
  --price-scale log \
  --json
```

渲染坐标只影响图形展示，不改变指数点位：默认 `--price-scale linear` 是普通坐标，多年K线或累计涨幅较大时可用 `--price-scale log` 查看对数纵轴。Workbench 的 Beta Strength Cloud/Market Backbone 点位图也提供 `linear/log` 下拉选择。

## 本文档存在的原因

beta-strength cloud index 回答的问题不同于已有的 correlation-core TopK index：

- **TopK correlation-core index**：按平均正相关选出最中心的股票，并通过 `market-correlation index` rebalance。
- **Dominant Beta Strength Cloud index**：计算每只股票相对于整个 eligible market 的平均 Fisher-z 相关强度，然后选择处于每日分布左肩处或右侧的股票。

当研究问题是“今天哪些股票属于广义市场 beta 云？”时，使用 `cloudridge-index` route。不要静默替换成 TopK、手动 threshold component 或旧图规则；这些 membership 是刻意不同的。

## 已移除/弃用的界面

- 新生产 payload 不再输出 legacy graph diagnostics、edge peakness、soft cap 或旧 selection-threshold alias。
- 一次性的 CohortIndex 物化脚本和固定手动 threshold 仅是归档复现工具，不是滚动 beta-strength-cloud 产品。

## 持久设计决策

当前实现通过专用的 CloudRidge index definition（指数定义）、rebalance、constituent-frame 和 level-frame 记录持久化选出的 beta-strength cloud。它不会变更 CandidateFactor、EffectiveFactor、AdmittedFactor、StrategySpec 或 orders。

理由：

1. beta-strength cloud membership 是形成日期上的**相对静态市场结构描述符**。
2. 专用滚动指数族是正确的、生命周期中立的产品界面；下方 legacy CohortIndex 物化仅用于归档。
3. 稠密 all-pairs matrix 很大（约 5.5k 只股票的 float32 约为 `~115MB`），因此矩阵类中间产物应保留为本地 run artifact，而 Factor Lab 只持久化 selected membership、return frame 和 render metadata。
4. 周度或日度重算操作应针对每个 formation date 重新运行 strength scan，然后在同一 index definition（指数定义） 下发布该日期的等权 constituent frame 和 level frame。

## 历史重算性能说明

DataHub 全历史脚本针对当前 beta-strength 公式进行优化，而不是针对已删除的图组件选择器：

- 它在每个 rebalance 窗口只计算一次 Pearson correlation matrix，然后直接从矩阵行和推导每只股票的平均 Fisher-z strength。没有 threshold grid scan，也没有 union-find connected-component pass。
- CPU 保持确定性默认值。`--compute-backend auto` 只有在工作区共享启动器已授权该进程且 CuPy 可用时才使用 GPU；否则回退 CPU。`--compute-backend cupy` 是严格模式，缺少共享准入或 CuPy/GPU 不可用都会快速失败。
- 项目依赖权威来源是 `pyproject.toml` + `uv.lock`。基础环境保持 CPU 兼容；可选的 `gpu-rocm` extra 只锁定 `cupy-rocm-7-0==14.0.1` Python 绑定，不再携带 ROCm SDK 共享库。PyTorch 和 CuPy 统一使用宿主 `/opt/rocm` `7.2.4` 与同一 `gfx1151` 独占租约。
- AMD 集成 GPU 路径：同步只含 CuPy 绑定的 extra，然后先跑唯一宿主预检：

  ```bash
  UV_LINK_MODE=copy uv sync --extra gpu-rocm
  scripts/run_factor_lab_rocm_gpu.sh --check
  ```

  共享启动器负责设置 ROCm/HIP 路径、设备权限预检和跨仓独占锁。禁止手工 export `ROCM_HOME` / `LD_LIBRARY_PATH`，也禁止用 `sg render` 绕过准入。
- 历史 DataHub backfill 可以把 `available_at` 存为入库时间，而不是市场数据决策日期。对这些 dataset，使用 `--availability-mode trading_day`：rebalance 仍只使用 `trading_day <= as_of_date`，同时避免错误地得出 2008 年 bar 在 2026 年回填时间戳之前都不可见的结论。
- 对历史运行，它会准备一个 PIT close/availability panel，并在所有周度/日度窗口中复用。每个窗口按 `available_date <= as_of_date` 切片和 mask 该 panel，在避免重复 groupby+pivot 工作的同时保留 PIT 语义。
- `--fast-export-only` 是推荐的全历史研究/导出路径。它使用完全相同的 scan 和 selection formula，但直接写出 `*.constituents.csv`、`*.rebalances.csv`、`*.levels.csv`、`*.summary.json`、`*.kline.svg`、可选的 `*.kline.png` 和 `*.html`，而不是把每个周度 scan 都物化进 runtime state。较短的 API/UI 管理生产窗口使用完整 runtime materialization；2008 至今的历史可视化和审阅使用 fast export。
- `--workers N` 并行化独立 window scan。持久化和最终 rendering 保持顺序执行，使 runtime record 保持确定性。
- 当 CuPy 激活时，脚本会强制 window-level workers 为 `1`，以避免单 GPU memory 过度提交。run summary 会记录 requested/actual backend、visible GPU count 和任何 worker adjustment note。

全历史周度重算示例：

```bash
python scripts/datahub_cloudridge_beta_index_rebalance.py \
  --history-start-date 2008-01-01 \
  --rebalance-frequency weekly \
  --lookback-window 120 \
  --workers 4 \
  --compute-backend auto \
  --price-scale log \
  --availability-mode trading_day \
  --fast-export-only \
  --output-prefix .omx/research-notes/cn_a_beta_strength_cloud_weekly_2008_now
```

严格 GPU 运行：

```bash
PYTHONPATH=src scripts/run_factor_lab_rocm_gpu.sh --cupy \
  scripts/datahub_cloudridge_beta_index_rebalance.py \
  --history-start-date 2008-01-01 \
  --rebalance-frequency weekly \
  --lookback-window 120 \
  --compute-backend cupy \
  --price-scale log \
  --availability-mode trading_day \
  --fast-export-only \
  --output-prefix .omx/research-notes/cn_a_beta_strength_cloud_weekly_2008_now_gpu
```

### 2008 至今的规范验证运行

最新权威本地验证：

```text
dataset_version: bars_cn_a_1d_raw_canonical_46c11d03a3ee
history: 2008-01-01 to 2026-05-18
frequency: weekly
backend: cupy / ROCm
availability_mode: trading_day
price_scale: log
windows: 940
daily level rows: 4459
latest level: 2009.8495641966
selected count range: 963..4676
coverage range: 0.8065205772..0.8755720824
elapsed: 619 seconds
```

生成的 artifact prefix：

```text
.omx/research-notes/cn_a_beta_strength_cloud_weekly_2008_now_gpu_log_20260520
```

重要文件：

```text
*.summary.json       run metadata and fixed contract fields
*.rebalances.csv    weekly as_of/effective dates, counts, coverage, turnover
*.constituents.csv  weekly stock pool and equal weights
*.levels.csv        daily equal-weight price-neutral index levels
*.kline.png/svg     log-scale K-line chart
*.html              shareable report wrapper
```

## 已归档的被取代研究

更早的图组件和固定 threshold 实验已刻意不再在生产运行手册中复现。它们只作为历史研究证据保留在 `.omx/context/` 和 `.omx/research-notes/` 下，用于审计目的。不要把这些 artifact 当作当前指数方法论。

当前生产运行必须使用上文的 beta-strength-cloud 公式和 `cloudridge-index` service surface；其 selector 是 CloudRidge / Dominant Beta Strength Cloud。

## 运行时 collection 迁移

如果 `runtime_state.sqlite3` / `runtime_state.json` 仍包含退役的 `correlation_threshold_pool_index_*` collection，请执行一次迁移：

```bash
PYTHONPATH=src python scripts/migrate_cloudridge_runtime_collections.py --json
```

脚本会先在 `FACTOR_LAB_HOME/backups/cloudridge-runtime-migration-*` 下创建 runtime backup，然后把缺失的行移动到匹配的 `cloudridge_beta_index_*` collection，并规范化 payload 词汇，包括 legacy threshold-scan id key 和退役 record type。它**不会**覆盖有冲突的当前记录；冲突会保留在 legacy collection 中，并且脚本会以退出码 `2` 退出以供人工审阅。

非变更 audit：

```bash
PYTHONPATH=src python scripts/migrate_cloudridge_runtime_collections.py --dry-run --json
```

## 护栏

- 对 beta-strength-cloud scan 和 index materialization 保持 `factor_lifecycle_mutation=false`。
- 不要称它为 alpha factor。它是市场结构/index artifact。
- 不要在 JSON runtime state 中存储完整稠密 matrix。matrix file 作为本地 run artifact 存储，只持久化 selected membership/return frame。
- 不要把 legacy graph diagnostics、固定手动 cutoff 或旧 selection-threshold alias 重新引入 production constituent。
- index level 保持 return-equal-weight 和 price-neutral；绝对股价既不影响 entry weight，也不影响 exit weight。

## 历史验证说明

pre-v3 和 raw-daily 验证输出不再嵌入本文档，因为它们使用了已被取代的 selection semantics 或非最终 data 口径。它们只应保留在 research notes 中。当前历史行为的公开参考是上文总结的权威 2008 至今 CloudRidge export，未来验证更新也只能作为 CloudRidge beta-strength-cloud run 追加。

filtering 和 timing-signal research 是下游验证工作流，不属于指数构建的一部分。其当前复权/QFQ 与 60m opportunity-density 证据已索引在 `.omx/research-notes/cloudridge_opportunity_density_research_manifest_20260521.md`；不要把这些滤波参数诊断结论混回 CloudRidge constituent selector。
