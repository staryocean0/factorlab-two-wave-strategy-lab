# 同尺度两浪研究：持久化审查包

代码提交：`ba871b71edc3994c9e611f2451d414bb4f33cfcb`。正式运行：`33961057778`。

本目录保存全部主5分钟候选、互斥分段、全长含未决分区、确认事件带，全部41个D0/C2G审计案例、98个D1已发布案例，以及六视图所有组的摘要。其他视图的完整逐条账本保留在源运行工件，并可由已提交代码重放。

- [D0/C2G图集：保留旧案例及失败模式](v04/gallery/README.md)
- [D1全部98个发布段：按时间排序、不挑成功样本](v041/gallery/README.md)
- [D0/C2G六视图摘要](v04/summary.json)
- [D1六视图摘要、偏移稳健性及微扰](v041/summary.json)
- [主视图D1分段](v041/5m_offset_0/D1/segments.json)
- [主视图D1全长分区，包含未覆盖与未决](v041/5m_offset_0/D1/partition.json)
- [归档清单与运行来源](delivery_manifest.json)

`full_run_output_sha256.json`是完整源工件的校验清单，不表示本目录含有其他视图的全部逐条文件。`delivery_manifest.json`逐项列明真正复制的内容及其源路径和哈希。

304项测试及120次独立截断重放通过，不代表形态验收通过。主视图仅覆盖4521/70114根（6.448%）；D1为32上涨、31下跌、1震荡、34不确定。其他5m偏移与主视图的结构区间交并比仅约12%—20%。保留`morphology_replication_not_yet_accepted`，没有收益计算、第三浪或交易权限。

形态区间为事后描述，确认条带不是实时交易状态。必须尊重原始`available_at`及`effective_information_time`，不能回填或前向延长为当时已知信号。
