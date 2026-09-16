# R5-B1 specialist Stage 1 — execution-surface note

日期：2026-09-16

Stage：`R5_B1_specialist_stage1_stability_continuous_shape_v1`

科学 protocol、runner、tests 和 execution freeze 已在任何 Stage-1 real-data outcome 可见之前冻结。

当前会话执行面事实：

- GitHub connector 能读取文本与列出 tracked Parquet，但不能把 binary Parquet 内容交给计算容器；
- current cloud container 对 github/raw GitHub 直接网络解析失败；
- 已授权 local machine 在本轮冻结后暂时离线。

因此授权使用 repository-native GitHub Actions 作为**纯执行面**，复用仓库中既有 frozen-research workflow 模式。该选择不改变任何科学定义、门槛、数据角色或裁决表。

Boundaries：

- workflow 必须在执行前校验 frozen artifact blob identities 与 source SHA256；
- 只运行 frozen 5 tests 和 frozen runner；
- 只读取 tracked `data/development/5m_offset_0.parquet`；
- 只上传 Stage-1 JSON receipt artifact；
- 不读 BLACKBOX / post-2020；不做 PnL/Sharpe；不修改 registry；不获得 production authority；
- workflow 不自动把结果写回仓库，结果必须由 cloud review 后再落库。

Execution-surface authority = true for this frozen Stage-1 run only.
Scientific protocol changed = false.
