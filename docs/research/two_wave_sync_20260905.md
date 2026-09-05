# 两浪续研 GitHub 同步与全量运行记录（2026-09-05）

本轮代码、报告和审查包已按用户明确授权写回私有仓库 `staryocean0/factorlab-two-wave-strategy-lab` 的 `codex/two-wave-phase1-20260905` 分支，完整研究与校验工作流均成功。草稿 [PR #1](https://github.com/staryocean0/factorlab-two-wave-strategy-lab/pull/1) 保持开放，未合并 main。**工程验证通过；H0 形态复刻仍未验收，独立真实参考为零，H1/H2、交易和收益研究继续关闭。**

本页更新[续研报告](two_wave_continuation_report_20260905.md)中此前被自动审批阻断的交付状态，并补充远端十四视图结果。旧报告与原审查 ZIP 保留形成时的六视图范围和历史记录。

## 提交与交付校验

- 本轮起点：`0b7ca8f31bcea1d21d86caca143512ac38c4ef82`。
- 已运行的研究代码提交：[`828d13d14aaed4ac2e358c71b06e415d37f87efe`](https://github.com/staryocean0/factorlab-two-wave-strategy-lab/commit/828d13d14aaed4ac2e358c71b06e415d37f87efe)，树为 `0458491d9abd42d6176562d340f4a92b2f45dd95`；21 个文本文件及 ZIP 的远端 Git blob 与本地逐一一致。
- 本页所在后续提交仅保存文档、审查入口与执行证据，沿用上面已通过的代码与工作流；提交消息使用 `[skip ci]` 避免重复运行。下述测试结果归属于 `828d13d…`，不混称为后续文档提交的独立测试。
- [完整续研审查包](../../cloud_results/two_wave_continuation_20260905.zip)：100 个文件，8,069,191 字节；无原始 Parquet，包含六视图私有开发行情的衍生回放与结果。
- ZIP SHA-256：`9c8f8c97d0089903291af723e60964c1bdadaf829f2ded9776b7d8654530fa99`；Git blob：`ed8d75e6f643fa4d12099e4b9a3e2744141690be`。
- [交付核对记录](../../cloud_results/two_wave_remote_20260905/delivery_receipt.json)。原冻结规范与十五工具身份不变；没有添加 2021 年以后数据，没有重采样或安装生产候选工具。

## 四个远端运行全部成功

| 事件 | 工作流 | 运行 | 结论 |
|---|---|---|---|
| PR | 全量研究 | [33949407076](https://github.com/staryocean0/factorlab-two-wave-strategy-lab/actions/runs/33949407076) | success |
| push | 全量研究 | [33949405211](https://github.com/staryocean0/factorlab-two-wave-strategy-lab/actions/runs/33949405211) | success |
| PR | 包校验与测试 | [33949407079](https://github.com/staryocean0/factorlab-two-wave-strategy-lab/actions/runs/33949407079) | success |
| push | 包校验与测试 | [33949405239](https://github.com/staryocean0/factorlab-two-wave-strategy-lab/actions/runs/33949405239) | success |

以下详细结果逐条解析自 PR 全量研究 [job 101261220527](https://github.com/staryocean0/factorlab-two-wave-strategy-lab/actions/runs/33949407076/job/101261220527)。分支 head 是 `828d13d…`，实际 checkout 的 PR 测试合并提交是 `e10e840865d08962c15bfa419868cbae31de4373`，两者不混用。

验证通过：473 个冻结资产、14 个供应商数据产品、749,337 源文件行、15 个不可变工具；源数据日期为 2015-01-05 至 2020-12-31。197 项测试通过，42/42 前缀检查通过，13 个代码/定义来源哈希与本地相符。源文件行包含重叠产品；三尺度处理合计 2,248,011 行，不代表增加独立样本。

本地仍缺八个原始 Parquet，因此旧本地完整包校验失败记录保留；此次远端完整仓库的包校验已补上这一验证缺口。

## 十四视图、三个冻结尺度的结果

共 43,874 个相关候选，明确分类 2,187 个（4.9847%），uncertain 41,687 个，invalid 0 个。跨尺度、跨产品及相邻窗口存在相关性，以下计数不能当作独立样本量或准确率。

| 冻结反转尺度 | 候选数 | range | uptrend | downtrend | uncertain | 明确占比 |
|---|---:|---:|---:|---:|---:|---:|
| 0.008 | 18,552 | 309 | 244 | 310 | 17,689 | 4.6518% |
| 0.010 | 14,155 | 272 | 204 | 244 | 13,435 | 5.0865% |
| 0.012 | 11,167 | 235 | 172 | 197 | 10,563 | 5.4088% |
| 合计 | 43,874 | 816 | 620 | 751 | 41,687 | 4.9847% |

### 拒判联合诊断

仅在已记录对象上忽略指定布尔拒判标记，其他条件与分母均不变；未重跑替代模型、未调阈值、未据覆盖率择优。

| 计数条件 | 明确数 | 较原记录新增 | 明确占比 |
|---|---:|---:|---:|
| 原记录 | 2,187 | 0 | 4.9847% |
| 仅忽略 `cycle_amplitude_change` | 2,365 | 178 | 5.3904% |
| 仅忽略 `uneven_phase_drift` | 4,604 | 2,417 | 10.4937% |
| 同时忽略上述两个标记 | 5,628 | 3,441 | 12.8276% |

`uneven_phase_drift` 总触发 34,823 次，但仅 2,417 个对象只有它这一项阻断；`cycle_amplitude_change` 总触发 24,993 次，仅 178 个对象只有它这一项阻断。触发次数不是删除条件后获救的对象数。原始周期极差包含漂移乘以时长，与去漂移宽度不同；流式反例与拒判归因支持继续澄清定义，不支持直接放松冻结规则。

全量 43,874 个有效结构的 E 残差分解最大绝对重构误差为 `3.019806626980426e-13`，与六视图机制分析一致。详细联合模式保存在下方证据 ZIP 的 `parsed_pr_job_summary.json`。

### 参考评价与稳健性边界

- 审查窗口从六视图的 42 个扩展到十四视图的 138 个后，依赖合并仍只有 6 个 calendar blocks。六个年度联合分层各仅一个块，95% CI 保持 `null`。仅增加重叠窗口不能解决可估计性。
- 固定微扰在 0.01 基准下匹配 14,047 / 14,155 个结构（99.2370%）。这是冻结容差内的结构匹配覆盖，**不是参考准确率**。原生日志未包含全部事件及分类转移明细；这些明细仍在原生工件内，未下载检查，不能作进一步稳定性结论。
- 12 个合成场景成功运行，但不替代真实独立标签。独立真实参考仍为零，准确率与相关性 CI 尚不可报告。

## 可审查证据与入口

- [精简十四视图结果](../../cloud_results/two_wave_remote_20260905/compact_remote_results.json)、[42 组逐视图/尺度记录](../../cloud_results/two_wave_remote_20260905/per_view_scale_runs.json)、[已运行提交的脚本/工作流快照](../../cloud_results/two_wave_remote_20260905/head_source_snapshot.json)。13 项来源哈希核对明细位于证据 ZIP 的 `parsed_pr_job_summary.json`。
- [本轮执行证据 ZIP](../../cloud_results/two_wave_remote_20260905/remote_evidence.zip)：包含完整作业日志、详细解析、运行/步骤/工件元数据、交付回执和 SHA-256 清单。原始日志 769,286 字节，SHA-256 为 `90798d31a1e8e9b7e48d2a602814454adb9fe54a2263c6e983a6c3594f160a6c`；已与返回全文逐字节核对。
- [六视图完整基准回放](../../cloud_results/two_wave_continuation/baseline_full_replay/replay.html)、[在线盲 pilot](../../cloud_results/two_wave_continuation/blind_pilot/pilot_online_blind.html)、[离线盲 pilot](../../cloud_results/two_wave_continuation/blind_pilot/pilot_offline_blind.html)：HTML 下载到本地后打开；线上盲标只看指定历史截止点。
- [pilot 操作说明](two_wave_blind_pilot_instructions.md)、[诊断图](../../cloud_results/two_wave_continuation/figures/two_wave_diagnostic.png)。全部空白标注表、结果与相对链接依赖保留在原续研审查 ZIP 内。

十四视图完整原生工件可从上方 PR 研究运行下载：工件 ID `9964429484`，名称 `two-wave-phase-one-e10e840865d08962c15bfa419868cbae31de4373`，54,548,875 字节；GitHub 记录的 digest 为 `sha256:ac78edd65290d0dd7b2fc24dee67ed3e8d8e0213c27f38999526024534c1a613`，到期时间 **2026-10-05 06:25:30 UTC**。该 digest 是远端元数据，本轮未下载整包自行重算。本分支保存的执行日志与精简结果不能替代工件内全部细节。

## 下一轮研究起点

1. 用盲 pilot 收集真人定义反馈和实际来源，明确“趋势”是否容许两周期速度或原始极差不同；离线意见不改标为在线。
2. 在正式标签评价前另行冻结可估计的抽样设计。若定义或识别规则需要修订，另起 v0.2 并保留 v0.1 失败结果。
3. 收集独立、去重、完整窗口参考并进行双人仲裁，随后才计算点估计、相关性 CI 与歧义敏感性。
4. 形态验收通过之前继续停留在 H0；不能根据工程通过、覆盖率变高或未来收益打开 H1/H2。
