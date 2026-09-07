# CL-20260907-004 本地 DataHub provenance 反馈包

状态：`local_feedback_ready_cloud_review_pending`

这不是 v0.6.17，不是 morphology 结果，也不关闭 GitHub issue #4。云端仍须按

`docs/ops/datahub_bar_support_provenance_intake_protocol_20260907.md`

独立复核。

## 执行了什么

- Route A：绑定本地项目 DataHub 已提交 HEAD，而不是脏工作区。
- Route C：把白皮书、合同、deriver、query、测试的 HEAD blob 拷进 `archive/`，并记录 git blob SHA1 与 sha256。
- 身份诊断：用 DataHub `assign_intraday_bucket_minute` 对照冻结 `dataset_version` 的 1m 湖，核验 2015-01-05..2020-12-31 / `000852.SH` 五个 5m 视图。不是 replacement 5m 产品。
- Route B：没有产出带 `source_minute_count/support_start/support_end` 的新 5m 产品。

## 文件

| 路径 | 作用 |
|---|---|
| `SOURCE_IDENTITY.json` | repo / commit / 文件 hash |
| `archive/` | 可上传给云端阅读的权威副本 |
| `HASHES.sha256` | 副本 sha256 |
| `contract_answers.md` | 9 个合同问题 |
| `identity_diagnostic.json` | 五个视图 label/OHLC/occupancy 摘要 |
| `session_boundary_samples.json` | offset0–4 的会话边界样例 |
| `test_receipt.json` | DataHub 33 passed |
| `run_identity_diagnostic.py` | 诊断脚本（只读，不写 `data/development/`） |

## 未做

- 未开 morphology
- 未把 `H_end_5` 升格为真源
- 未用 `1m_official` 重采样
- 未读 2021+
- 未改冻结 parquet
- 未代填“云端已复核”
