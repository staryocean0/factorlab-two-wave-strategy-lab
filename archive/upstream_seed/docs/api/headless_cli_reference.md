# Headless CLI reference

本文件是 `factor-lab` headless CLI 的参考手册，拆自 [headless_control_surface.md](headless_control_surface.md)。它回答“有哪些 CLI wrapper、怎么传参、输出什么 JSON”。如果你要按用户研究目标选择路线，请读 [`../user/ai_research_cli_control_surface.md`](../user/ai_research_cli_control_surface.md)。

---

## CLI（命令行）

以 editable 或 wheel 形式安装包，然后使用：

```bash
factor-lab health
factor-lab readiness
factor-lab api start --host 127.0.0.1 --port 18080 --home .local/factor-lab
factor-lab api status --home .local/factor-lab
factor-lab api logs --home .local/factor-lab --tail 80
factor-lab api stop --home .local/factor-lab
factor-lab datahub-health
factor-lab datahub-fetch-bars --symbol 000001 --market cn_a --frequency 1d --instrument-type stock --view qfq_canonical --start-time 2026-01-01T00:00:00Z --end-time 2026-03-31T23:59:59Z --source-id datahub_cn_a_prices --dataset-name cn_a_daily --schema-version ds_pit@1.0 --layer pit
factor-lab call GET /runs --scope read --query run_type=factor_evaluation
factor-lab confirm-phrase --action cancel --resource-type run --resource-id run-123
```

`factor-lab api` 在后台管理本地 FastAPI 服务。它在 `FACTOR_LAB_HOME` 下持久化 PID/state/log 文件，并为每个生命周期命令打印 JSON：

- `factor-lab api start` 启动 `uvicorn factor_lab.app.api.main:app`。
- `factor-lab api status` 报告 `running`、`starting`、`stale` 或 `stopped`。
- `factor-lab api logs` 返回 `logs/api-service.log` 尾部内容。
- `factor-lab api stop` 发送优雅终止信号。
- `factor-lab api restart` 组合执行 stop + start。

服务状态契约见 [Headless API 后台服务白皮书](../ops/headless_api_background_service_whitepaper.md)。

`factor-lab call` 接受：

- `--timeout 15` 用于控制 HTTP 请求超时
- `--scope public|read|write|governance`
- 重复使用 `--query key=value`
- `--body-json '{"key":"value"}'`
- `--body-file path/to/body.json`
- `--confirm action:resource_type:resource_id`

超时也可以通过 `FACTOR_LAB_API_TIMEOUT_SECONDS`（或旧别名 `FACTOR_LAB_API_TIMEOUT`）设置。默认值是 `30` 秒。

CLI 始终打印结构化 JSON。

## AI 友好的 CLI 包装命令

通用 `call` 命令仍可用，但外部 agent 可以使用更窄的命令来保留 run/job/artifact ID：

```bash
factor-lab routes --base-url http://127.0.0.1:18080 --json
factor-lab runs get <run_id> --base-url http://127.0.0.1:18080 --json
factor-lab runs list --run-type factor_evaluation --base-url http://127.0.0.1:18080 --json
factor-lab runs timeline <run_id> --base-url http://127.0.0.1:18080 --json
factor-lab runs events <run_id> --base-url http://127.0.0.1:18080 --json
factor-lab runs artifacts <run_id> --base-url http://127.0.0.1:18080 --json
factor-lab runs artifact <run_id> <artifact_id> --base-url http://127.0.0.1:18080 --json
factor-lab runs wait <job_or_run_id> --base-url http://127.0.0.1:18080 --json
factor-lab runs compare --run-id-a <run_a> --run-id-b <run_b> --base-url http://127.0.0.1:18080 --json

factor-lab factor-specs list --base-url http://127.0.0.1:18080 --json
factor-lab factor-specs get fac_mom_20d@1.0 --base-url http://127.0.0.1:18080 --json
factor-lab factor-specs create-dsl --name l7_mom --expression 'rank(delta(close, 20))' --spec-version fac_l7_mom@1.0 --base-url http://127.0.0.1:18080 --json
factor-lab base-factors list --category style --seedable --base-url http://127.0.0.1:18080 --json
factor-lab base-factors get momentum_20d --base-url http://127.0.0.1:18080 --json
factor-lab base-factors seed --factor-id momentum_20d --base-url http://127.0.0.1:18080 --json
factor-lab base-factors seed --all-seedable --base-url http://127.0.0.1:18080 --json

factor-lab datasets publish --source-id <source> --source-family price_volume --dataset-name <name> --schema-version ds_pit@1.0 --layer pit --market cn_a --base-url http://127.0.0.1:18080 --json
factor-lab data-sources list --base-url http://127.0.0.1:18080 --json
factor-lab data-sources create --source-id <source> --source-name <name> --terms-version <terms> --source-family price_volume --field-dictionary-json '{"close":"float"}' --base-url http://127.0.0.1:18080 --json

factor-lab runs submit-evaluation --dataset-version <dataset> --factor-spec-version fac_mom_20d@1.0 --label-spec-version lbl_fwd_ret_5d_ex_current_bar@1.0 --code-version git:headless --base-url http://127.0.0.1:18080 --json
factor-lab runs submit-mining --dataset-version <dataset> --label-spec-version lbl_fwd_ret_5d_ex_current_bar@1.0 --code-version git:headless --base-url http://127.0.0.1:18080 --json
factor-lab runs submit-ml --source-dataset-version <dataset> --baseline-run-id <run> --feature-ref mom_20d --feature-ref vol_20d --base-url http://127.0.0.1:18080 --json
factor-lab runs submit-ml --source-dataset-version <dataset> --baseline-run-id <run> --model-family deep_mlp --deep-architecture mlp --device-preference auto --distributed-mode torch_distributed --world-size 2 --backend gloo --base-url http://127.0.0.1:18080 --json
factor-lab runs submit-portfolio --candidate-set-id <candidate_set> --base-url http://127.0.0.1:18080 --json
factor-lab runs portfolio <portfolio_run_id> --base-url http://127.0.0.1:18080 --json
factor-lab runs ml <ml_run_id> --base-url http://127.0.0.1:18080 --json

factor-lab strategy-specs create --name "BSE inverse momentum" --admitted-factor-id <admitted_factor_id_for_fac_bse_inverse_mom20> --top-n 10 --market-policy cn_bse_equity_v1 --base-url http://127.0.0.1:18080 --json
factor-lab strategy-specs list --base-url http://127.0.0.1:18080 --json
factor-lab strategy-specs get <strategy_spec_id> --base-url http://127.0.0.1:18080 --json
factor-lab strategy-backtests preflight --strategy-spec-id <strategy_spec_id> --signal-dataset-version <daily_pit_tradable_dataset> --minute-dataset-version <minute_pit_tradable_dataset> --start-time 2026-01-02 --end-time 2026-01-03T15:00:00 --base-url http://127.0.0.1:18080 --json
factor-lab strategy-backtests submit --strategy-spec-id <strategy_spec_id> --signal-dataset-version <daily_pit_tradable_dataset> --minute-dataset-version <minute_pit_tradable_dataset> --start-time 2026-01-02 --end-time 2026-01-03T15:00:00 --base-url http://127.0.0.1:18080 --json
factor-lab strategy-backtests detail <run_id> --base-url http://127.0.0.1:18080 --json
factor-lab strategy-backtests chart <run_id> --symbol <symbol> --base-url http://127.0.0.1:18080 --json
factor-lab strategy-backtests dashboard <run_id> --output backtest_dashboard.html --symbol <symbol> --base-url http://127.0.0.1:18080 --json

factor-lab filtering characteristics --rows-file cloudridge_levels.json --index-ref CN_A_CLOUDRIDGE_BETA_EQW --period week --period day --period 60min --output-json artifacts/time_series_characteristics.json --output-md artifacts/time_series_characteristics.md --json
factor-lab filtering parameter-workflow --rows-file cloudridge_levels.json --index-ref CN_A_CLOUDRIDGE_BETA_EQW --period week --period day --period 60min --random-baseline-count 40 --output-json artifacts/filter_parameter_workflow.json --json
factor-lab filtering directional-information --rows-file cloudridge_levels.json --index-ref CN_A_CLOUDRIDGE_BETA_EQW --period 60min --center-period-days 8 --center-period-days 10 --center-period-days 12 --q 0.707 --q 1.0 --q 1.4 --horizon-frac 0.125 --horizon-frac 0.25 --horizon-frac 0.5 --output-json artifacts/filter_dii_surface.json --output-md artifacts/filter_dii_surface.md --json
factor-lab filtering frequency-discovery --rows-file cloudridge_levels.json --index-ref CN_A_CLOUDRIDGE_BETA_EQW --period week --period day --period 60min --period 5min --period 1min --dii-filter-mode bandpass --dii-filter-mode lowpass --output-json artifacts/filter_frequency_discovery.json --json
factor-lab filtering tool-selection --rows-file cloudridge_levels.json --index-ref CN_A_CLOUDRIDGE_BETA_EQW --period 60min --filter-mode bandpass --target-period-lo-bars 34 --target-period-hi-bars 55 --output-json artifacts/filter_tool_selection.json --json
factor-lab filtering strategy-workflow --rows-file cloudridge_levels.json --index-ref CN_A_CLOUDRIDGE_BETA_EQW --higher-period day --execution-period 60min --higher-filter-json '{"name":"daily_iir","family":"laplace_iir","mode":"lowpass","params":{"period":40},"output_kind":"level"}' --execution-filter-json '{"name":"hourly_iir","family":"laplace_iir","mode":"bandpass","params":{"period":12,"q":1.0},"output_kind":"component"}' --higher-cycle-days 8 --execution-cycle-days 2 --render-prefix artifacts/cloudridge_60m_strategy --render-price-scale log --json
factor-lab filtering workflow-chain --rows-file cloudridge_levels.json --index-ref CN_A_CLOUDRIDGE_BETA_EQW --period week --period day --period 60min --period 30min --period 15min --period 5min --period 1min --render-dir artifacts/filter_chain/cloudridge --render-price-scale log --output-json artifacts/filter_chain/cloudridge/workflow_chain.json --json

factor-lab factor-dynamics profile --dataset-version <factor_rows_dataset> --factor-ref industry --value-column industry --base-url http://127.0.0.1:18080 --json
factor-lab factor-dynamics indexes create --name "media cohort" --descriptor-ref industry --membership-dataset-version <membership_dataset> --membership-value-column industry --cohort-value media --base-url http://127.0.0.1:18080 --json
factor-lab factor-dynamics indexes get <cohort_index_id> --base-url http://127.0.0.1:18080 --json
factor-lab factor-dynamics indexes returns <cohort_index_id> --price-dataset-version <daily_price_dataset> --base-url http://127.0.0.1:18080 --json
factor-lab factor-dynamics rotation analyze --source-return-frame-id <source_frame> --target-return-frame-id <target_frame> --lookback-periods 3 --forward-periods 1 --base-url http://127.0.0.1:18080 --json
factor-lab factor-dynamics conditional evaluate <factor_id> --signal-dataset-version <dynamic_signal_rows> --descriptor-dataset-version <descriptor_rows> --label-dataset-version <forward_label_rows> --descriptor-value-column industry --base-url http://127.0.0.1:18080 --json

factor-lab latent discover --dataset-version <daily_pit_dataset> --universe-ref cn_a --start-date 2026-01-01 --end-date 2026-03-31 --feature-family daily_return_corr --base-url http://127.0.0.1:18080 --json
factor-lab latent discover --dataset-version <minute_pit_tradable_dataset> --universe-ref cn_a --start-date 2026-01-01 --end-date 2026-03-31 --feature-family minute_path_similarity --base-url http://127.0.0.1:18080 --json
factor-lab latent runs list --status completed --base-url http://127.0.0.1:18080 --json
factor-lab latent clusters list --run-id <latent_run_id> --base-url http://127.0.0.1:18080 --json
factor-lab latent clusters get <latent_cluster_id> --base-url http://127.0.0.1:18080 --json
factor-lab latent interpret <latent_cluster_id> --decision interpret_new --decision-reason "human naming review" --name "latent theme" --thesis "cluster co-moves in the discovery window" --horizon short --latent-factor-type theme --base-url http://127.0.0.1:18080 --json
factor-lab latent materialize <latent_factor_id> --dataset-version <dataset> --base-url http://127.0.0.1:18080 --json
factor-lab latent factors card <latent_factor_id> --base-url http://127.0.0.1:18080 --json
factor-lab latent versions list <latent_factor_id> --base-url http://127.0.0.1:18080 --json
factor-lab latent versions refresh-exposures <latent_factor_version> --dataset-version <dataset> --base-url http://127.0.0.1:18080 --json
factor-lab latent sets select --name "research factor set" --version-id <latent_factor_version> --selector-reason "strategy research basket" --base-url http://127.0.0.1:18080 --json
factor-lab latent monitor report --run-id <latent_run_id> --latent-factor-id <latent_factor_id> --base-url http://127.0.0.1:18080 --json
factor-lab latent lab state --run-id <latent_run_id> --cluster-id <latent_cluster_id> --base-url http://127.0.0.1:18080 --json
factor-lab latent exposures preview <exposure_frame_id> --limit 500 --base-url http://127.0.0.1:18080 --json
factor-lab latent exposures register-spec <exposure_frame_id> --name "latent materialized frame" --base-url http://127.0.0.1:18080 --json
factor-lab latent handoff <exposure_frame_id> --dataset-version <dataset> --label-spec-version lbl_fwd_ret_5d_ex_current_bar@1.0 --code-version git:headless --base-url http://127.0.0.1:18080 --json
factor-lab latent materialize-handoff <latent_factor_id> --dataset-version <dataset> --label-spec-version lbl_fwd_ret_5d_ex_current_bar@1.0 --code-version git:headless --base-url http://127.0.0.1:18080 --json

factor-lab candidates list --base-url http://127.0.0.1:18080 --json
factor-lab candidates promote --source-run-id <run_id> --candidate-name <name> --base-url http://127.0.0.1:18080 --json
factor-lab candidates transition <candidate_factor_id> --new-status watchlist --reason "ready for reviewer" --evidence-artifact-id <artifact_id> --base-url http://127.0.0.1:18080 --json
factor-lab candidate-sets create --name <set_name> --candidate-factor-id <candidate_id> --base-url http://127.0.0.1:18080 --json
factor-lab candidate-pool add --factor-spec-version fac_mom_20d@1.0 --candidate-name "manual alpha" --base-url http://127.0.0.1:18080 --json
factor-lab candidate-pool add --dsl-expression "rank(close) - rank(open)" --candidate-name "manual dsl alpha" --base-url http://127.0.0.1:18080 --json

factor-lab review create --source-run-id <run_id> --card-json '{"candidate_factor_id":"<candidate_id>","title":"Candidate","evidence_refs":["<artifact_id>"]}' --base-url http://127.0.0.1:18080 --json
factor-lab review feedback <candidate_id> --review-session-id <review_session_id> --action keep --reason "keep for rerun" --evidence-ref <artifact_id> --base-url http://127.0.0.1:18080 --json
factor-lab approvals create --request-type shared_candidate_validated --target-ref run:<run_id> --reason "validate candidate" --review-session-id <review_session_id> --base-url http://127.0.0.1:18080 --json
factor-lab approvals approve <validation_approval_request_id> --comment "validated evidence approved" --base-url http://127.0.0.1:18080 --json
factor-lab candidates transition <candidate_factor_id> --new-status validated --reason "approved evidence" --evidence-artifact-id <artifact_id> --approval-request-id <validation_approval_request_id> --base-url http://127.0.0.1:18080 --json
factor-lab approvals create --request-type shared_rerun --target-ref review_session:<review_session_id> --reason "rerun" --review-session-id <review_session_id> --base-url http://127.0.0.1:18080 --json
factor-lab approvals approve <approval_request_id> --comment "approved" --base-url http://127.0.0.1:18080 --json
factor-lab review rerun <review_session_id> --reason "approved rerun" --candidate-factor-id <candidate_id> --shared-scope --approval-request-id <approval_request_id> --base-url http://127.0.0.1:18080 --json

factor-lab approvals create --request-type factor_admission --target-ref effective_factor:<effective_factor_id> --reason "admit factor" --base-url http://127.0.0.1:18080 --json
factor-lab approvals approve <factor_admission_request_id> --comment "approved for reuse" --base-url http://127.0.0.1:18080 --json
factor-lab admitted-factors admit --effective-factor-id <effective_factor_id> --approval-request-id <factor_admission_request_id> --admitted-name "governed alpha" --base-url http://127.0.0.1:18080 --json
factor-lab admitted-factors list --dataset-version <dataset_version> --base-url http://127.0.0.1:18080 --json
factor-lab admitted-factors get <admitted_factor_id> --base-url http://127.0.0.1:18080 --json
factor-lab admitted-factors transition <admitted_factor_id> --new-status published --reason "ready for reuse" --base-url http://127.0.0.1:18080 --json

factor-lab observability metrics --base-url http://127.0.0.1:18080 --json
factor-lab observability alerts --base-url http://127.0.0.1:18080 --json
factor-lab security guidance --base-url http://127.0.0.1:18080 --json
```

`runs submit-evaluation` 和 `validation submit-candidate` 会在普通回归 / 验证前自动执行 temporal routing。它们的请求体保持不变。动态信号继续返回 202。静态或慢变化描述因子会返回带 `profile_id`、`temporal_class`、`blocked_reason`、`recommended_uses` 和确定性后续控制面的 `E_GATE_BLOCKED`/409：

```bash
factor-lab factor-dynamics profile --dataset-version <factor_rows_dataset> --factor-ref <factor_ref> --value-column factor_value --json
factor-lab factor-dynamics indexes create --name <cohort_name> --descriptor-ref <factor_ref> --membership-dataset-version <descriptor_rows> --membership-value-column factor_value --cohort-value <value> --json
factor-lab factor-dynamics rotation analyze --source-return-frame-id <source_frame> --target-return-frame-id <target_frame> --json
factor-lab factor-dynamics conditional evaluate <factor_id> --signal-dataset-version <dynamic_signal_rows> --descriptor-dataset-version <descriptor_rows> --label-dataset-version <forward_label_rows> --descriptor-value-column factor_value --json
```

`latent handoff` 和 `latent materialize-handoff` 在创建 CandidateFactor 或 ValidationClaim 状态前使用同一个 temporal routing gate。动态 latent exposures 可以继续进入 `pending_review`；静态或慢变化 exposures 会返回带 `gate_details`/`temporal_profile` 的 `handoff.status=blocked_temporal_routing`，并应通过上面的 factor-dynamics cohort-index、rotation 或 conditional-evaluation 命令研究。

所有包装命令都接受 `--base-url`、全局 `--timeout`、`--json` 和 `--compact`。错误响应使用 API client 返回的同一 JSON 错误信封。

### `filtering characteristics`

`factor-lab filtering characteristics` 是本地计算型 wrapper，不需要启动本地 API，也不会创建 CandidateFactor、EffectiveFactor、AdmittedFactor 或交易策略。它用于“先体检再选方法”：

1. 输入一个指数/组合的 `timestamp + close` 序列；
2. 按 `week/day/60min/30min/15min/5min/1min` 重采样；
3. 计算趋势、均值回复/震荡、周期、随机、波动聚集、跳跃厚尾、结构切换和微观结构噪声评分；
4. 按不同周期自动切分多个统计稳定子区间，判断特性是否稳定复现；
5. 用三类可解释闸门做宽松初筛：周期看 `spectral_top3_concentration_ratio >= 8.0`，趋势看 `bdci >= 52.0` 或 `return_autocorr_lag1 >= 0.03`，震荡（反向）看 `return_autocorr_lag1 <= -0.03`；
6. 输出每个周期通过了哪些候选路线，以及明确用途建议。

常用参数：

- `--rows-json` / `--rows-file`：二选一，传入 `[{timestamp, close}, ...]`。
- `--period`：可重复指定；不指定时尝试 `week/day/60min/30min/15min/5min/1min`。
- `--min-observations`：单周期最少 K 线数，不足则该周期 `skipped`。
- `--max-windows-per-period`：每个周期最多保留多少个子区间稳定性样本。
- `--uniform-window-policy`：复现实验用；默认按周期使用不同子区间窗口。
- `--output-json`：写出结构化 artifact。
- `--output-md`：写出中文可读报告。

核心输出：

- `periods[].scores[]`：0–100 分特性评分；
- `periods[].metrics`：BDCI、Hurst、方差比、自相关、频谱熵等统计证据；
- `periods[].dominant_cycles[]`：频谱主峰候选；
- `periods[].method_recommendations[]`：该周期建议的处理方法；
- `periods[].direct_use_gates[]`：周期/趋势/震荡三类初筛闸门；趋势含 BDCI 与 lag1 正收益自相关两条 OR 门；
- `periods[].candidate_categories[]` / `periods[].candidate_category_labels[]`：已通过初筛的候选路线，可多选；
- `periods[].use_category` / `periods[].use_category_label`：向后兼容主分类，真正分流以候选路线列表为准；
- `periods[].recommended_use`：明确建议；
- `periods[].unsuitable_for[]`：明确不适合的用途；
- `periods[].stability`：多区间稳定性统计；
- `periods[].windows[]`：每个子区间的画像；
- `summary.method_routing[]`：跨周期方法路由。

### `filtering parameter-workflow`

`factor-lab filtering parameter-workflow` 是本地计算型 wrapper，不需要启动本地 API，也不会创建 CandidateFactor、EffectiveFactor、AdmittedFactor 或交易策略。它用于“先算再调参”：

1. 输入一个指数/组合的 `timestamp + close` 序列；
2. 按 `week/day/60min/30min/15min/5min/1min` 检查输入粒度；这些值表示K线级别/采样粒度，不是滤波目标周期；
3. 对可用K线级别做长期滚动单位机会密度；
4. 在连续密度曲线上找中心峰和相邻低谷，分箱只作解释标签；
5. 用“折算后最接近目标K线根数”的规则把交易日等效区间划归 1min/5min/.../日线/周线；
6. 输出推荐保留区间、滤波模式、参数变化趋势和可进入后续滤波 battle 的候选参数种子。

常用参数：

- `--rows-json` / `--rows-file`：二选一，传入 `[{timestamp, close}, ...]`。
- `--index-ref`：结果里的指数或组合标识。
- `--period`：可重复指定；不指定时尝试 `week/day/60min/30min/15min/5min/1min`，但输入粒度不足的周期会 `skipped`。
- 默认按周期分工使用不同窗口：`week=60m/12m`、`day=36m/12m`、`60min=12m/6m`、`30min=6m/6m`、`15min=3m/3m`、`5min=1m/1m`、`1min=1m/1m`。这避免分钟线承担日线级长周期滤波。
- `--uniform-window-policy`：显式回到旧版全周期统一窗口；此时 `--window-years`、`--step-years` 对所有周期生效。
- `--random-baseline-count`：随机打乱基线次数；生产研究不要设为 0。
- `--min-continuous-peak-window-share`：连续峰/低谷证据的最低复现率；低于该值不再退回分箱兜底。
- `--output-json`：把完整结果写入文件，便于作为研究 manifest 附件。

核心输出：

- `summary_recommendations`：跨周期综合推荐；
- `periods[].recommendations`：单周期推荐保留区间、解释频段、评分、趋势和滤波器种子；
- `center_period_bars` / `continuous_peak_period_bars`：密度峰中心；
- `retained_period_lo_bars / retained_period_hi_bars`：真正用于生成滤波候选参数的低谷边界；
- `filter_mode`：根据低谷/边缘关系给出的 `lowpass`、`highpass` 或 `bandpass`；
- `owned_intervals`：按K线根数归属后的跨周期职责切片；`assigned_period` 是最终负责周期；
- `merged_owned_intervals`：同一 `assigned_period` 职责切片合并后的最终滤波设计区间；保留给独立参数诊断与人工工具选择，`workflow-chain` 主线不再读取它；
- `period_band_bars`：解释标签，不是最终参数本身；
- `bin_sensitivity_score`：多套分箱下的边界敏感性；
- `periods[].trend_points`：每个滚动窗口的主导高密度频段；
- `periods[].status/skip_reason`：输入粒度或样本不足时的可解释跳过原因。

持久化/复跑约定：

- `--output-json` 写出的完整 JSON 是正式可复用 artifact；Markdown、CSV、PNG 只是下游派生展示。
- `metadata.canonical_output_sections` 固定下游读取范围：`metadata`、`periods`、`summary_recommendations`、`owned_intervals`、`merged_owned_intervals`。
- `metadata.artifact_contract` 和 `metadata.rerun_policy` 会说明何时重跑、如何比较新旧 run。
- 如果未来包装成 REST / UI，必须保留这些结构化字段或提供可下载 JSON，不能只暴露单次截图。

### `filtering directional-information`

`factor-lab filtering directional-information` 是本地计算型 wrapper，用于策略回测前的方向信息频率曲面诊断。它只使用价格序列、因果滤波方向和未来收益 label，不计算仓位、成本、净值、回撤、交易次数或盈亏比。

DII 频率曲面的规范轴是频率/物理周期，不是 K 线 bars。周线、日线、小时线、分钟线只是采样载体；`center_period_bars` 是兼容/实现坐标，输出会同时给出 `center_period_days` 与 `center_frequency_cycles_per_day`。

核心公式：

```text
DII(T,Q,phi)=E[sign(delta filtered_t) * (logP_{t+round(phi*T/delta)}-logP_t)]
```

常用参数：

- `--period`：要评估的K线级别/采样粒度，必填；
- `--center-period-days`：频率优先输入，可重复指定中心周期 `T`（交易日等价）；
- `--center-period-minutes`：频率优先输入，可重复指定中心周期（A股交易分钟，240 分钟=1 交易日）；
- `--center-period-bars`：兼容输入，可重复指定当前采样级别下的滤波实现周期 `P`；不传则使用该K线级别默认网格；
- `--q`：可重复指定 IIR Q 值；默认 `0.707/1.0/1.4`；
- `--horizon-frac`：可重复指定未来收益窗口 `phi`；代码按 `h=round(phi*T/delta)` 换算为 bars，默认 `0.125/0.25/0.5`；
- `--stability-policy`：`calendar_year` 或 `fixed_window`；
- `--robust-*`：参数邻域和稳健分位设置，用于识别宽厚正山脊而不是孤立尖峰；
- `--output-json` / `--output-md`：保存结构化 artifact 和中文报告。

核心输出：

- `points[]`：全部频率曲面点；
- `selected[]`：按强度、稳健分位和 DII 排序的 Top 候选；
- `center_period_days`：规范中心周期，交易日等价；
- `center_frequency_cycles_per_day`：规范中心频率，每交易日循环次数；
- `center_period_bars`：兼容字段；该采样级别上的滤波实现周期；
- `dii_bps`：方向信息指数，以 bps 报告；
- `robust_dii_quantile_bps`：邻域稳健分位，惩罚孤立高点；
- `positive_window_share`：年度或固定窗口中 DII 为正的比例；
- `evidence_strength`：`no_directional_edge`、`thin_directional_edge`、`directional_candidate` 或 `strong_directional_candidate`；
- `metadata.unit_policy`：声明 bars 只是采样实现坐标，曲面规范轴是物理周期/频率；
- `metadata.pre_backtest_boundary`：声明该 artifact 不是策略回测。

### `filtering tool-selection`

`factor-lab filtering tool-selection` 是本地计算型 wrapper。它假设频率区间已经由参数工作流固定，只用信号质量选择工具，不用回测收益调参。

常用参数：

- `--target-period-lo-bars / --target-period-hi-bars`：目标保留周期边界；
- `--targets-json / --targets-file`：多周期独立目标数组；每个周期单独给 `period/filter_mode/target_period_lo_bars/target_period_hi_bars`；
- `--filter-mode`：`lowpass`、`highpass` 或 `bandpass`；
- `--top-n`：保留几个工具；
- `--min-tool-quality-score`：最低质量分；
- `--no-ema / --no-fourier / --no-iir / --no-wavelet`：排除某类候选。

核心输出：

- `evaluations`：所有候选工具的 frequency fit、lag、continuity、fidelity、volatility retention、interpretability 和总分；
- `selected`：进入策略构造的工具；
- `selected[].filter_spec`：可直接传给 `strategy-workflow` 的滤波器 JSON。
- 多周期模式下输出 `period_results[]` 和 `selected_by_period`；后续必须按周期读取对应的 `filter_spec`，不得使用全局工具赢家。

### `filtering strategy-workflow`

`factor-lab filtering strategy-workflow` 构造已注册择时模板。当前支持双周期模板 `higher_period_gate_execution_trigger`（大周期方向门禁 + 本周期买卖触发，默认冲突空仓）、单周期带通分量模板 `single_period_component_trigger`（本周期 component 分量自己同时承担方向识别和买卖触发），以及单周期低通水平斜率模板 `single_period_level_slope_trigger`（本周期 level 斜率承担趋势状态和买卖触发）。

常用参数：

- `--strategy-template`：策略模板；默认 `higher_period_gate_execution_trigger`；
- `--higher-period`：双周期模板的方向门禁周期；单周期模板不需要；
- `--execution-period`：执行和回测周期；
- `--higher-filter-json / --execution-filter-json`：双周期模板分别来自对应周期工具选择结果的 `filter_spec`；单周期模板只提供 `--execution-filter-json`，其中 `single_period_component_trigger` 要求 `output_kind=component`，`single_period_level_slope_trigger` 要求 `output_kind=level`；
- `--higher-cycle-days / --execution-cycle-days`：滤波区间中心的交易日等效值；双周期模板同时提供后会强制检查默认 `3x–8x` 结构候选层级关系；单周期模板可只提供 `--execution-cycle-days`；
- `--min-higher-cycle-ratio / --max-higher-cycle-ratio`：调整允许进入研究集的大周期/本周期倍数区间，默认 `3` 和 `8`；这是结构先验，不是最终最优参数，最终门禁倍数需用 walk-forward/Pareto 收益回撤权衡选择；
- `--conflict-policy`：`flat_on_conflict` 或 `hold_until_exit_trigger`；
- `--cost-bps`：可选 legacy 对称成本覆盖；不传时使用A股默认成本（买入1bps、卖出6bps）。
- `--render-prefix`：可选。最终回测阶段写出 `*.strategy.svg`、`*.signals.csv`、`*.html`；
- `--render-price-scale`：`linear` 或 `log`，控制 K线价格坐标；
- `--render-max-bars`：SVG 最多渲染的执行周期 K线数；CSV 始终保留全量逐K线信号。

核心输出：

- `strategy_template`：本次使用的策略模板；
- `signal_diagnostics`：门禁开启比例、触发比例、冲突比例、开平仓次数；单周期模板中门禁恒为1；
- `composite_backtest`：当前模板主策略下一根 K 线执行回测；
- `baseline_backtests`：双周期模板输出 `execution_only` 与 `higher_gate_only` 对照；单周期模板为空；
- `metadata.scale_hierarchy_assessment`：双周期模板的周期倍数层级判断；单周期模板为 `null`；
- `metadata.gate_ratio_selection_policy`：说明 `3x–8x` 只是结构候选窗口，最终倍数要用 walk-forward/Pareto 选择；
- `metadata.signal_generation_policy`：滤波输出如何变成信号；`output_kind=component` 默认使用滤波分量K线涨跌方向切换，分量K线由跌转涨后下一根K线买入，由涨转跌后下一根K线卖出；
- `metadata.render_artifacts`：启用渲染时的 SVG/CSV/HTML 路径和图表范围；
- `metadata.render_artifacts.signal_field_labels_zh` / `metadata.field_labels_zh`：英文机器字段的中文解释。报告和 HTML 标题/表头优先中文，JSON/CSV 键名保持英文以兼容下游。
- `metadata.lookahead_policy`：双周期模板中大周期信号滞后一根大周期 K 线后再 forward-fill；所有模板的策略信号都在执行周期下一根 K 线生效。

### `filtering frequency-discovery`

`factor-lab filtering frequency-discovery` 只运行 DII 全物理频谱发现，不进入工具选择和回测。常用参数包括 `--period`（允许载体）、`--dii-min-center-days`、`--dii-max-center-days`、`--dii-frequency-grid-points`、`--dii-q`、`--dii-horizon-frac`、`--dii-filter-mode`、`--dii-min-bars-per-cycle`、`--dii-max-bars-per-cycle`、`--dii-tradable-band-merge-ratio`。输出包含 `frequency_surfaces[]`、合并后的 `frequency_candidates[]`、`carrier_candidates[]` 和 `metadata.unit_policy`；`frequency_candidates[].tradable_band_member_*` 说明该可交易频段由哪些正山脊代表合并而来。

### `filtering workflow-chain`

`factor-lab filtering workflow-chain` 把时间序列特性体检、DII 全物理频谱发现、正山脊聚类、载体投影、工具选择、策略前执行风险提示、策略回测和回测渲染串成一个闭环。`--period` 表示允许使用的 K线采样/执行载体，不再表示固定频段归属。

常用参数：

- `--period`：重复指定允许使用的 K线载体；
- `--min-observations`：workflow-chain 主线 DII/工具/策略阶段的最小样本数；
- `--dii-min-center-days / --dii-max-center-days`：限制 DII 物理周期搜索范围；
- `--dii-frequency-grid-points`：物理周期网格点数；
- `--dii-q / --dii-horizon-frac / --dii-filter-mode`：DII 全频谱网格；默认 `bandpass + lowpass`；
- `--dii-min-bars-per-cycle / --dii-max-bars-per-cycle`：载体有效性门禁；
- `--dii-tradable-band-merge-ratio`：相邻正山脊代表合并为可交易频段的最大物理周期比例，默认 `1.35`；
- `--parameter-*`：兼容旧脚本的 deprecated/no-op 参数；metadata 写入 `deprecated_parameter_stage_ignored=true`，不再影响主线候选频段；
- `--tool-*`：传给工具选择阶段的质量门槛；工具目标来自 DII 正山脊载体投影，`--tool-top-n` 会把每个目标区间前 N 个质量候选都带入最终策略阶段；
- `--no-directional-information-precheck`：不再允许；传入会报错，因为 DII 已是 mandatory discovery stage；
- `--same-level-max-ratio / --min-higher-cycle-ratio / --max-higher-cycle-ratio`：周期倍数结构候选政策，不代表最终最优门禁倍数；
- `--no-synthesize-higher-targets`：关闭默认结构候选窗口几何中心倍数方向探针；
- `--render-dir`：启用最终回测 SVG/CSV/HTML 渲染；
- `--output-json`：保存完整链路 artifact。

核心输出：

- `series_characteristics`：前置时间序列体检 artifact；
- `parameter_workflow`：兼容 artifact；workflow-chain 中为 skipped/deprecated；
- `frequency_discovery` / `frequency_candidates` / `carrier_candidates`：DII 全频谱发现、按物理周期聚类后的正山脊代表、以及投影到 K线载体后的可回测目标；
- `tool_results`：DII 正山脊载体投影后的工具选择 artifact；`target.frequency_candidate_id` 回连物理频率候选；`target.pre_strategy_tradability_status` 标明是否命中 A股 T+1/日线附近策略前执行风险提示；
- `strategy_results`：每个通过层级检查的策略回测 artifact；命中 A股 T+1/日内风险提示的目标当前仍进入单周期、双周期和后续 walk-forward，风险只通过 `pre_strategy_tradability_status` 留痕；
- `summary_backtests`：不同执行K线级别的可读回测统计和渲染图路径；双周期行会尽量补充 `reward_retention_vs_single`、`cagr_delta_vs_single`、`drawdown_compression_vs_single`、`pareto_frontier`、`gate_tradeoff_status` 和 `gate_tradeoff_note_zh`；当单周期 CAGR ≤ 0 时，收益保留率不可解释，应看 `cagr_delta_vs_single` 和中文权衡说明；
- `research_decision`：最终研究决策；主轴为 `frequency_decisions[]`，逐物理频率候选 + 承载载体回答 T/f、山脊强弱、工具赢家、T+1执行风险提示、成本/样本周期门禁、单/双周期证据和样本外资格；`period_decisions[]` 仅兼容旧消费者；
- `metadata.chain_order`：固定链路顺序；
- `metadata.period_semantics_policy`：明确 `period` 字段是K线采样粒度，目标周期看 `target_center_days / execution_cycle_days`；
- `metadata.pre_strategy_tradability_gate_policy`：记录 `expected_leg_days = target_center_days / 2` 的 A股 T+1/日内执行风险提示；
- `metadata.directional_information_policy`：记录 DII 公式、宽厚曲面要求和“不是回测”的边界；
- `metadata.gate_ratio_selection_policy`：记录方向门禁倍数的 walk-forward/Pareto 选择口径。

## L7 Agent Automation

L7 是覆盖现有 L1-L6 工作流的自动化层。它把自然语言 idea 映射为候选包和方法建议，发布 L7 artifact；当必需输入存在时提交既有受治理 run，否则带着证据支撑报告停止。

```bash
factor-lab l7 run \
  --base-url http://127.0.0.1:18080 \
  --idea "rank 20 day price momentum" \
  --mode pure_auto \
  --budget small \
  --evidence-policy conservative \
  --automation-depth full_safe \
  --json

factor-lab l7 status <session_id> --base-url http://127.0.0.1:18080 --json
factor-lab l7 report <session_id> --base-url http://127.0.0.1:18080 --json
factor-lab l7 resume <session_id> --base-url http://127.0.0.1:18080 --json
factor-lab l7 choose <session_id> --option use_recommended_method --base-url http://127.0.0.1:18080 --json
```

额外 L7 run 控制项：

- `--evidence-policy conservative|exploratory|custom`
- `--evidence-thresholds-json '{"evaluation_min_rank_ic_mean": 0.01}'`
- `--automation-depth method_only|evidence_loop|full_safe`
- `--max-auto-steps <N>`
- `--candidate-set-id <validated_candidate_set_id>`

完整 CLI 流程：

```bash
factor-lab l7 run \
  --base-url http://127.0.0.1:18080 \
  --idea "optimize the best momentum lookback window" \
  --dataset-version <dataset_version> \
  --budget standard \
  --evidence-policy conservative \
  --automation-depth full_safe \
  --json

# 响应暴露 evidence_verdict、launched_runs、downstream_artifact_ids、
# governance_handoffs、automation_step_count、next_actions 和 human_choices。
factor-lab l7 report <session_id> --base-url http://127.0.0.1:18080 --json
```

L7 响应暴露稳定字段：`decision_log`、`human_choices`、`next_actions`、`artifacts`、`latest_artifacts_by_type`、`evidence_verdict`、`automation_step_count`、`launched_runs`、`downstream_artifact_ids` 和 `governance_handoffs`。L7 artifact 包括 `l7_idea_brief`、`l7_candidate_map`、`l7_method_selection_report`、`l7_execution_plan`、`l7_decision_log`、`l7_evidence_digest`、`l7_early_stop_report` 和 `l7_final_research_report`。

`l7_execution_plan` artifact 包含 `backtest_execution_disclosure`。在回测 continuation 点，`human_choices` 会暴露 `run_backtest_conservative` 和 `run_backtest_chase_breakout`，而不是隐藏的一刀切回测。`run_backtest_conservative` 是推荐的普通策略默认项；`run_backtest_chase_breakout` 在 tick/minute 排队成交模拟实现前会被有意阻断。

## DataHub 拉取控制面

Factor Lab 现在为被动 DataHub 拉取路径暴露官方 API-first 包装：

- `GET /api/v1/datahub/health` 检查已配置的 DataHub base URL、`GET /api/v1/health/live`，以及针对 `GET /api/v1/history/datasets` 和 `GET /api/v1/instruments` 的轻量 pull 探针。
- `POST /api/v1/datahub/fetch-bars` 通过 `DataHubFetchService` 运行完整的 `download -> wait -> fetch bars -> publish dataset` 工作流。

如果需要面向操作员的契约，而不是直接调用 Python service，请使用 CLI 包装命令：

```bash
factor-lab datahub-health --base-url http://127.0.0.1:18080
factor-lab datahub-fetch-bars \
  --base-url http://127.0.0.1:18080 \
  --symbol 000001 \
  --market cn_a \
  --frequency 1d \
  --instrument-type stock \
  --view qfq_canonical \
  --start-time 2026-01-01T00:00:00Z \
  --end-time 2026-03-31T23:59:59Z \
  --source-id datahub_cn_a_prices \
  --dataset-name cn_a_daily \
  --schema-version ds_pit@1.0 \
  --layer pit
```


`factor-lab datahub-fetch-bars` 是价格 / 成交量拉取路径。墙上时钟 offset / noon-close 由 DataHub `/history/bars` 构造，本命令只翻译 FactorLab 菜单。不要用 `datasets derive-shifted-bars` 去造墙上时钟；那条命令只服务云脊午休连续钟。生成的 dataset 必须解析为 `source_family=price_volume`；下游评估提交应显式保留该值。需要复权价格时必须显式传 `--view qfq_canonical`（前复权）或 `--view hfq_canonical`（后复权），并在 A 股股票上建议传 `--instrument-type stock`。

## 破坏性操作确认

以下操作需要显式确认：

- 取消 job
- 取消 run
- 轮换 secret

API 调用方可以：

1. 在 `confirmation.phrase` 中发送正确短语。
2. 先不带确认调用一次，读取 `E_CONFIRMATION_REQUIRED` payload，然后重新提交。

CLI 调用方可以使用 `--confirm action:resource_type:resource_id`。

示例：

```bash
factor-lab call POST /jobs/job-123:cancel \
  --scope write \
  --confirm cancel:job:job-123
```

## 端到端示例

### 1. 引导与 readiness

```bash
factor-lab health
factor-lab readiness
```

### 2. 注册并刷新来源

```bash
factor-lab security principals upsert \
  --principal-id managed_source_owner \
  --display-name "Managed Source Owner" \
  --principal-scope fl:read \
  --principal-scope fl:write \
  --principal-scope fl:governance \
  --role researcher \
  --role reviewer \
  --role governance_admin \
  --json

factor-lab security secrets register \
  --secret-name vendor_api_key \
  --provider env \
  --reference env://VENDOR_API_KEY \
  --owner-principal-id managed_source_owner \
  --rotation-interval-days 30 \
  --json

factor-lab data-sources create \
  --source-id headless_prices \
  --source-name headless_prices \
  --source-family price_volume \
  --connector-type vendor_http \
  --description "Headless market data source" \
  --terms-version vendor_terms@2026-03-28 \
  --field-dictionary-json '{"symbol":"string","close":"float"}' \
  --refresh-policy daily \
  --status active \
  --failure-policy retry_then_manual \
  --json

factor-lab data-sources refresh headless_prices \
  --refresh-status succeeded \
  --refresh-note "headless refresh" \
  --recovery-action none \
  --json

factor-lab data-sources refreshes headless_prices --json
```

### 3. 发布 dataset

```bash
factor-lab datasets publish \
  --source-id headless_prices \
  --source-family price_volume \
  --dataset-name headless_daily_prices \
  --schema-version ds_pit@1.0 \
  --layer pit \
  --market cn_a \
  --json
```

读取返回的 `run_id`，然后检查 artifact，从 `dataset_manifest` artifact 中提取已发布的 `dataset_version`：

```bash
factor-lab runs artifacts <publish-run-id> --json
factor-lab runs artifact <publish-run-id> <dataset-manifest-artifact-id> --json
```

### 4. 运行因子评估与下游研究

```bash
factor-lab runs submit-evaluation \
  --dataset-version <dataset-version> \
  --source-family price_volume \
  --factor-spec-version fac_mom_20d@1.0 \
  --label-spec-version lbl_fwd_ret_5d_ex_current_bar@1.0 \
  --protocol-version eval_daily@1.0 \
  --code-version git:headless \
  --json

factor-lab runs list --run-type factor_evaluation --json
factor-lab candidates promote --source-run-id <factor-run-id> --json
factor-lab candidates list --json
```

读取 portfolio 和 ML 详情时，继续使用 `runs portfolio` 与 `runs ml`。回测证据现在只通过 StrategySpec 分钟级回测产生：

```bash
factor-lab runs submit-portfolio \
  --candidate-set-id <candidate-set-id> \
  --portfolio-spec-version portfolio_equal_weight@1.0 \
  --code-version git:portfolio \
  --json
factor-lab runs portfolio <portfolio-run-id> --json

factor-lab strategy-backtests submit \
  --strategy-spec-id <strategy-spec-id> \
  --signal-dataset-version <daily-pit-tradable-dataset> \
  --minute-dataset-version <minute-pit-tradable-dataset> \
  --start-time 2026-01-02 \
  --end-time 2026-01-03T15:00:00 \
  --json
factor-lab strategy-backtests detail <strategy-backtest-run-id> --json
factor-lab strategy-backtests dashboard <strategy-backtest-run-id> --output dashboard.html --json
```

### 5. 评审、审批与 rerun

```bash
factor-lab review create \
  --source-run-id <factor-run-id> \
  --card-json '{"candidate_factor_id":"candidate-alpha","title":"Alpha","evidence_refs":["<artifact-id>"]}' \
  --json

factor-lab review feedback candidate-alpha \
  --review-session-id <review-session-id> \
  --action keep \
  --reason "keep for rerun" \
  --evidence-ref <artifact-id> \
  --json

factor-lab approvals create \
  --request-type shared_rerun \
  --target-ref review_session:<review-session-id> \
  --reason "rerun after review" \
  --review-session-id <review-session-id> \
  --json

factor-lab approvals list --review-session-id <review-session-id> --json
factor-lab approvals approve <approval-request-id> --comment "approved" --json
factor-lab review rerun <review-session-id> \
  --reason "approved rerun" \
  --candidate-factor-id candidate-alpha \
  --shared-scope \
  --approval-request-id <approval-request-id> \
  --json
factor-lab review timeline <review-session-id> --json
factor-lab review events <review-session-id> --json
```

### 6. 观测与治理

```bash
factor-lab observability metrics --json
factor-lab observability alerts --json
factor-lab security guidance --json
```
