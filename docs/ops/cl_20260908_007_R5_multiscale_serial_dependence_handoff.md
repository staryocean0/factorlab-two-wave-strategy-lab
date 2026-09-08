# CL-20260908-007 — R5 多尺度序列依赖 TRAIN / VALIDATION 执行交接

日期：2026-09-08

状态：`LOCAL EXECUTION REQUIRED / CLOUD REVIEW PENDING`

Research identity：`R5_multiscale_serial_dependence_state_v1`

## 1. 任务目的

在**不使用任何 BLACKBOX** 的前提下，执行已经 results-blind 冻结的 R5 浅层筛选：

1. R5-A：短期负记忆 + 较慢正记忆的 mixed state 是否有足够供给；
2. R5-B：anti-persistence 是否增强下一步均值回归；
3. R5-C：较慢正记忆状态中的 counter-trend shock 是否更容易在随后 15m 回到 parent direction。

这是 reusable TRAIN / VALIDATION research，不是 fresh OOS，不是 PnL backtest。

## 2. 分支与冻结身份

仓库：`staryocean0/factorlab-two-wave-strategy-lab`

分支：`codex/two-wave-phase1-20260905`

执行前必须更新到包含 freeze 的最新分支，并核对：

```text
preanalysis
  docs/research/reversal_mean_reversion_R5_multiscale_serial_dependence_preanalysis_20260908.md
  blob e9f901e98485226678eb1324a3447df3472ea136

protocol
  docs/governance/reversal_mean_reversion_R5_multiscale_serial_dependence_protocol_v1.json
  blob 87446bd1d16baf280220cdd10ab53cd45193e649

runner
  scripts/run_broad_rmr_R5_multiscale_serial_dependence.py
  blob cd0ac94f7f8dc4fba7c9ee25701bcca02f551f2a

tests
  tests/unit/test_broad_rmr_R5_multiscale_serial_dependence.py
  blob cd3b91b528185912c085bab9b3e8caf6dba4c956

execution freeze
  docs/governance/reversal_mean_reversion_R5_execution_freeze_v1.json
```

任何上述 blob 不一致：停止，不执行真实结果。

## 3. 数据身份

只允许：

```text
data/development/5m_offset_0.parquet
symbol = 000852.SH
rows = 70,114
sha256 = bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48
max day = 2020-12-31
```

角色：

```text
TRAIN      = 2015-01-05..2018-12-31
VALIDATION = 2019-01-01..2020-12-31
BLACKBOX   = none
```

TRAIN 与 VALIDATION 都可以读取细节；本任务没有 blackbox。

## 4. 必须按顺序执行

### Stage 1 — synthetic gates

```bash
pytest -q tests/unit/test_broad_rmr_R5_multiscale_serial_dependence.py
```

期望：7 tests 全部通过。

若失败，只允许修 implementation bug。不得修改：

- 240 return volatility window；
- 960 state window；
- short lags 1..3；
- long lags 12..18；
- 100 pairs/lag；
- TRAIN 80% abs-z shock quantile；
- R5-A supply minimum；
- R5-C sample minimum；
- B/C 模型容量与系数方向。

若需要修 implementation，先在本交接记录或单独 incident 文件说明原因，并确认科学协议未改。

### Stage 2 — frozen TRAIN / VALIDATION run

```bash
python scripts/run_broad_rmr_R5_multiscale_serial_dependence.py \
  --output docs/research/local_broad_rmr_R5_multiscale_serial_dependence_receipt_v1.json
```

Runner 自己必须校验 source SHA、rows、symbol、max day。

## 5. 允许输出

compact receipt 可包含：

- exact source identity；
- exact continuous-return row count；
- R5-A TRAIN/VALIDATION state supply 和 mixed-state 描述；
- R5-B TRAIN fit coefficients、VALIDATION pooled/2019/2020 MSE 与预测相关；
- 仅当 B1 通过 core gate 时的 B2；
- R5-C q80（仅由 TRAIN feature distribution 得到）、trigger/resolved counts；
- C0/C1 TRAIN coefficients、VALIDATION MSE、mean recovery / positive recovery fraction；
- frozen overall adjudication。

## 6. 明确禁止

- 不读 2021+；
- 不指定或打开 BLACKBOX；
- 不叫 fresh OOS；
- 不报告 PnL / Sharpe / 交易收益；
- 不改 lag/window/quantile；
- 不按年份/方向/时段找有利子集；
- 不上 HMM/rSLDS/Koopman；
- 不重写旧 R1/R2/R3/R4/T1 的结论。

## 7. 回传要求

执行后使用 `[skip ci]` 推回：

```text
docs/research/local_broad_rmr_R5_multiscale_serial_dependence_receipt_v1.json
```

并在 commit message 中说明：

- actual test command / exit code / passed count；
- actual runner command / exit code；
- source SHA / rows；
- BLACKBOX_read=false；
- post_2020_rows_read=false；
- PnL_read=false；
- local result = `local_reported`，云端尚未复核。

大数据不需要推回。

## 8. 云端验收

收到 receipt 后云端会先做：

1. blob/source/role 复核；
2. 验证 R5-A 是否决定了 B/C 可执行性；
3. 验证 B2 没有绕过 B1；
4. 验证 C sample gate 与系数方向；
5. 区分 `local_reported` 与 `cloud_reviewed`；
6. 再决定 R5 是继续在 TRAIN/VALIDATION 研究，还是低容量机制关闭。

本地完成不等于云端验收。
