---
name: robot-report-to-ppt-bridge
description: 仅在用户明确要求将已完成的报告、实验文档或证据台账提炼为答辩 PPT 时使用。把报告中的可核查结论、素材和限制整理成只读交接包，供独立 technical-defense-ppt Skill 使用；不撰写报告正文，也不直接制作或修改 PowerPoint。
---

# 报告到 PPT 的证据交接

本技能是可选桥接层，不是报告 Skill 或 PPT Skill 的前置条件。只有用户明确提出“报告转答辩”“从文档提炼 PPT”时才使用。

## 输入与输出边界

- 输入：已定稿或指定版本的报告、证据清单、图表源、照片、日志和用户确认；一律只读。
- 输出：`ppt-workspace/handoff/presentation-evidence-v1.json` 及必要的 `questions-for-source.md`。
- 不修改 Word/PDF、报告 manifest、原始图片、日志、实验数据或现有 `.pptx`。
- 不进行审美排版、PPTX 制作或报告正文改写；交接包完成后由 `technical-defense-ppt` Skill 接手。

## 执行顺序

1. 读取 `references/handoff-contract.md`，为每个候选结论登记 claim_id、证据状态、限制、来源和允许的 PPT 用法。
2. 为每项照片、日志、图表和视频登记 asset_id、权属、可证明/不可证明范围、裁切说明和可编辑源。
3. 将没有充分来源的内容列入 `questions-for-source.md`；不让它进入已验证 claim。
4. 生成只读交接包后停止。本技能不调用报告模板编辑脚本，也不创建幻灯片。

## 交接规则

- 报告到 PPT 是单向数据流：PPT 可引用或重排交接包，但不能反写报告。
- 已有报告不是独立 PPT 的必要条件；没有报告时应直接使用 `technical-defense-ppt` Skill。
- 若用户希望同时修改报告与 PPT，分别运行两个 Skill，并通过本交接包人工确认版本边界。

## 参考文件

- `references/handoff-contract.md`：交接包 schema、校验条件和缺料处理。
