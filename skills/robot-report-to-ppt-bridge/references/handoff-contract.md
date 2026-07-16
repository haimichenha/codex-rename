# 报告到 PPT 交接包契约

交接包写入 `ppt-workspace/handoff/presentation-evidence-v1.json`。它是只读快照，不是报告或 PPT 的双向同步文件。

## 最小 schema

```text
schema_version
source_report_version / source_commit / generated_at
claims[]:
  claim_id, statement, status, source_asset_ids,
  data_version, test_condition, limitation, allowed_ppt_use
assets[]:
  asset_id, path, type, rights, evidence_status,
  supports, does_not_support, crop_notes
figures[]:
  figure_id, editable_source, export_path, units, data_scope
open_questions[]
```

## 校验

1. 每个已验证 claim 至少有一个 `source_asset_id` 或用户确认来源。
2. 数值必须关联数据版本、单位、测试条件或数据范围；不足时降级为待验证。
3. `allowed_ppt_use` 指明可作为主证据、支撑证据、解释材料或不得使用。
4. 交接包生成后，报告内容与资产不再被此技能改写；PPT 产生的新猜测只可写入 `open_questions`，等待用户或报告流程确认。
5. 缺少权属、图源、条件或可编辑源时，一次性列入 `open_questions`，而不是用外部图片或估算数值填补。
