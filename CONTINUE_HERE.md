# 两浪 H0：从这里继续（2026-09-05 本轮续研）

> 更新：用户已在下一轮明确授权将本次代码、报告、审查包写回下述私有仓库研究分支，并运行研究工作流。该授权持续有效，无需再次询问。当前同步与运行状态见 `docs/research/two_wave_sync_20260905.md`；下方写回阻断段落保留为历史记录。

## 当前事实

- 目标仍是连续同尺度两个完整波形与父结构分类的形态复刻。H0 未验收；独立真实标签为 0；H1/H2、交易、注册可用仍未开放。
- GitHub：`staryocean0/factorlab-two-wave-strategy-lab`，Private，草稿 PR #1，远端研究分支 `codex/two-wave-phase1-20260905`。
- 本轮开始核对的远端 head：`0b7ca8f31bcea1d21d86caca143512ac38c4ef82`。识别代码原提交 `f0ae399e76e962c6dcc29a5c5e0611430dcd88c8`；`9c1f588…` 是资产源快照，不能混称识别代码 head。
- 原始规范 v0.1、协议 v0.1、geometry/models/engine/data/replay/annotations 及原15工具均未修改。
- 本轮只分析可取得的6个Parquet视图。原8个较大源文件缺失；完整本地package validator失败，不能写全包通过。

## 这次新增的研究结论

1. 18组旧记录共8,208相关候选；原明确384（4.68%）。单移除uneven标记后799（9.73%），连同原始周期振幅标记一起移除后982（11.96%）。只做布尔归因，未改模型或挑参数。
2. 完整流式反例证明：五点严格平行等宽且匀速漂移，仍可能仅因原始周期振幅比>1.6拒判。原始振幅含漂移×时长，不等于去漂移宽度。
3. E可精确分解为两项残差来源；真实8,208对象最大重构误差约2.24e-13。多个拒判条件不是独立证据，但不据此宣告可删除。
4. 42个既定审查核心跨产品合并后每年一个block，共6个；年度分层没有可估计的年内抽样变异。需要另版评价设计，不能凭增加重叠标签解决。

## 已实现并实际验证

- diagnostics.py及诊断CLI；adjudication.py及双人对照、准备表、签署仲裁CLI；uncertainty.py及窗口审计/真实参考评价CLI。
- 六视图`.01`基准重跑18,992行、2,736结构；24个pivots/cycles/structures/events记录文件与上次逐字节一致，6/6前缀检查通过。
- 完整基准回放包含六视图全部已供历史；在线pilot仅原bar#0—978，离线pilot至1106，两者无算法记录。
- 首个固定pilot核心：30m_offset_15/.01，#723—978。它是操作/定义试用，不替代200对象及每类30的独立参考目标。
- 最终完整测试数量见cloud_results/two_wave_continuation/verification.json及tests.xml；已有独立代理审查并修复来源/窗口/重复真值门禁问题。

## 文件入口

- docs/research/two_wave_continuation_report_20260905.md
- docs/research/two_wave_rejection_diagnostics_20260905.md
- docs/research/two_wave_uncertainty_method.md
- docs/research/two_wave_annotation_adjudication_workflow.md
- docs/research/two_wave_blind_pilot_instructions.md
- cloud_results/two_wave_continuation/（真实分析、完整回放、空表、图与验证证据）

## GitHub 写回阻断：不要绕过

本轮create_tree上传汇总脚本/工作流被自动审批拒绝。只读核对了账号、仓库与既有同仓库交付授权说明后，重新尝试一次仍被拒绝：自动审批不认可本次向该目的地披露新增研究代码的明确授权。此后未进行任何GitHub写操作，未提交到远端，未通过别的路径转传。

交付时只需用户明确确认：允许把本次新增代码、报告和审查包写回上述同一私有仓库研究分支，并运行其研究工作流；不合并main。若后续用户已经回答同意，应沿用授权，核对远端新head后推进，不要反复询问。

## 下一步执行顺序

1. 若已得到本次写回明确授权，核验远端head和diff，在同一草稿PR保存增量；处理他人的后续变更，不强推。新增工作流会运行全14视图并把每组分类、拒判和hash写入原生日志；本轮还没运行这些新远端检查。
2. 用盲pilot收取真人意见和实际来源，先确定用户的“趋势”是否允许两周期速度或原始极差不同。看过未来的意见保留为离线，不改名成在线。
3. 在标签评价前冻结新的可估计抽样设计；如改识别模型则另起v0.2，保留v0.1失败结果。禁止仅据覆盖更高或收益更好选择。
4. 收集独立、去重、完整窗口的offline/online参考，完成争议仲裁、点估计、相关性CI及歧义敏感性。没有足够证据就继续H0未验收。
5. 只有通过形态门后才能打开第三浪统计；用户唯一策略性退出仍是本级反向突破，同向突破不自动退出或交接。

## 增量包使用

在任意目录解压交付包阅读，不要先覆盖已有仓库。代码与文档增量在two_wave_continuation.patch，基线为上方0b7ca8f。先在完整仓库执行git apply --check，再应用补丁；然后将交付包cloud_results/two_wave_continuation复制到仓库相同目录。若已有这些新文件或远端进展，先比较、保留版本，不能直接覆盖。

本包不含原始Parquet。请使用仓库原始受清单管理的行情；不能重采样、补造或请求2021年以后数据来解决缺失。
