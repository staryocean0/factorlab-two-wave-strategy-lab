# 1m native-path alignment inventory review

日期：2026-09-16

状态：`INVENTORY ACCEPTED FOR NEW OUTCOME-BLIND IDENTITY FREEZE`

GitHub Actions run `35041427672` completed successfully at head `9d18f536dda25eeac6ffb7f26a8ad4c27aad73fe`. Artifact `10425251748`, digest `sha256:a52a3aec36d4be78e07cabcf716dab11ea1679fdd4dc1d01437126e23aa8f8cc`.

本次只做数据 inventory，没有读取 future-return outcome、PnL、BLACKBOX 或 post-2020 数据，也没有本地 resample。

## 关键事实

- 1m source SHA 与 manifest 一致：`755217afce9dec383e48cd46d591402fa90dc50897abeb3dc7097c9a18a109d4`；
- 350,561 rows，000852.SH，2015-01-05..2020-12-31；
- 1,462 trading days，其中 1,460 天恰好 240 rows；最小异常日 18 rows；无重复 symbol+timestamp；
- 70,114 个 official 5m endpoints 中 70,112 个存在完全相同 timestamp 的 1m close，presence=`99.99715%`；
- 所有已匹配 endpoint 的 1m close 与 official 5m close 完全相等：max absolute diff=`0`，nonzero count=`0`；
- 70,108 / 70,114 official 5m endpoints 拥有 endpoint 及前 4 个 native 1m timestamps 的完整同日 chain，fraction=`99.99144%`；
- 1,460 / 1,462 天所有 5m endpoint 都拥有该完整 chain，仅 2 天有缺口。

## 结论

`1m_official.parquet` 可用于新的 native-path research，只要 runner 明确要求 exact 1m continuity，并自动丢弃少量不完整路径，而不是填补、重采样或修改原始价格。

允许下一步冻结一个新的 continuous path-information identity。该 identity 必须与旧 T1 的 5-sigma shock event 不同：不做 shock threshold 搜索；用 native 1m 路径相对 official 5m endpoint 的额外信息，控制 endpoint displacement 后测试路径信息是否有增量。

BLACKBOX 仍为空；production authority=false。
