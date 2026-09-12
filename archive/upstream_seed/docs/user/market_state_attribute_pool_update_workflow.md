# 市场状态属性池更新工作流

本工作流是属性池随时间更新的唯一入口。源设施先自行完成数据物化和验收，本
工作流随后统一登记；禁止直接复制散落数据到current目录。

## Phase 0：先验框架

```bash
.venv/bin/python scripts/update_market_state_attribute_pool_infrastructure.py \
  --framework-only \
  --result-json docs/ops/evidence/market_state_attribute_pool_infrastructure_v1_20260824/framework_validation.json
```

命令默认加载`market_state_attribute_pool_overlay_mo_theta@1.0.json`。如需显式指定，可重复传入`--overlay <path>`；overlay只追加源，不覆盖基础注册表。

只有五位一体表面、五池身份和权限门通过后，才允许盘点数据。

## Phase 1：盘点与登记

1. 只读搜索现有manifest、Parquet、CSV和验证证据。
2. 判断其属于哪个pool；跨池数据不得复制身份。
3. 在`market_state_attribute_pool_registry@1.0.json`登记source。
4. required只用于当前必须存在的权威源；历史/未来源用optional。
5. 先登记，不移动、不删旧文件。

## Phase 2：发布内容寻址Snapshot

```bash
.venv/bin/python scripts/update_market_state_attribute_pool_infrastructure.py \
  --publish \
  --result-json docs/ops/evidence/market_state_attribute_pool_infrastructure_v1_20260824/publish_result.json
```

同样registry和source bytes必须产生同一snapshot id。

## Phase 3：独立复核Current

```bash
.venv/bin/python scripts/update_market_state_attribute_pool_infrastructure.py \
  --validate-current \
  --result-json docs/ops/evidence/market_state_attribute_pool_infrastructure_v1_20260824/current_validation.json
```

## Phase 4：时间推进

当某个源更新时：

1. 先由源设施重建并验收；
2. 更新registry中的权威source path/version；
3. 重新publish，产生新snapshot；
4. 对比新旧catalog的source hash和池状态；
5. validate-current通过后才交付下游；
6. 保留旧snapshot，不回写历史证据。

如果source bytes已经变化而尚未publish，`--validate-current`会以
`registered current source hash drifted`失败；不得跳过这一步继续消费旧catalog。

## 失败关闭

- required源缺失；
- 五池身份漂移；
- 五位一体入口缺失；
- 权限被打开；
- snapshot hash不一致；
- current指向不完整目录。

任一发生即停止，不允许人工把状态改绿。
