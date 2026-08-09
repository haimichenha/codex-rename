# Office Skills

面向机器人、嵌入式、自动化与技术答辩项目的 Codex Office 文档技能仓库。`main` 是唯一的可用主分支：报告和 PPT 使用各自独立的生产技能、资料工作区与版本化交付物，不再使用“报告转 PPT”桥接技能。

## 当前技能

| 技能 | 适用任务 | 不做什么 |
| --- | --- | --- |
| [`robot-report-suite`](skills/robot-report-suite/SKILL.md) | 基于 Word 模板创建、重构和修订 `.docx/.pdf` 实验报告、技术报告与竞赛报告 | 不创建或排版 `.pptx` |
| [`technical-defense-ppt`](skills/technical-defense-ppt/SKILL.md) | 创建、改版、逐页审稿、渲染和交付答辩/项目汇报 `.pptx` | 不改写 Word 报告 |

只有这两个 Office 生产入口。报告需要 PPT 时，将已定稿报告作为 PPT 的**只读材料**；PPT 需要报告修订时，回到报告技能。两者不得覆盖或清理对方工作区。

## 报告：模板 + 资料燃料 → 初版 → 微调

1. 将原始 Word 模板、原报告和格式要求复制到 `report-workspace/input/`，保持只读并记录哈希。
2. 将图片、日志、测量表、代码说明、数据 CSV 和文字资料按来源放入 `input/fuel/` 或 `evidence/`；它们是报告的“燃料”，不是可以凭文件名臆测的结论。
3. 先冻结保留范围：`保留全部模板结构`、`仅保留基础信息页`，或用户明确列出的范围；新资料不会取消已有模板约束。
4. 建立材料台账、章节卡片、图表清单和 `format-contract.md` 后输出版本化初版 `v0`。
5. 渲染 `.docx/.pdf` 检查基础信息页、空白、表格、图注、分页和证据回链；把反馈写入差异清单，依次产生 `v1`、`v2`……，不覆盖输入或上一确认版。

建议目录：

```text
report-workspace/
  input/
    template/              # 模板、原报告、格式要求（只读副本）
    fuel/                  # 原始图片、数据、文字资料与代码说明
  evidence/                # 已核查的日志、照片、测量表与来源说明
  sections/                # 章节卡片、材料增量台账、风格说明
  figures/source/          # 可编辑图源
  figures/export/          # 插入报告的图
  output/                  # v0、v1… 的 .docx/.pdf
  qa/                      # 渲染图、格式审计和修订记录
```

## PPT：资料燃料 → 逐页锁定 → 初版 → 微调

1. 将原 PPT、照片、图表、日志、数据文本和项目资料复制到 `ppt-workspace/input/fuel/`；原 PPT 另存于 `input/original/`，均不可直接覆盖。
2. 建立资产台账：每份资料标注 Asset ID、版本、能证明什么、不能证明什么和可用页面。
3. 先规定**每一页**：单页结论、证据等级、Hero、Support、Finish、版式、相邻页差异与讲解节拍，写入 `page-locks/`。没有页面锁定卡不得进入排版。
4. 按页面顺序构建 `v0`：先校准封面、最难技术页和最强验证页，再完成其余页面。
5. 每轮导出逐页渲染图与 contact sheet；先修证据和结论，再修阅读路径、裁切和排版，最后做视觉细节。所有微调以 `v1`、`v2`…… 输出，不覆盖原件。

建议目录：

```text
ppt-workspace/
  input/
    original/              # 原 PPT（只读副本）
    fuel/                  # 图片、视频帧、数据、文本、日志和报告副本
  brief/                   # 受众、时长、主线与限制
  assets/                  # 资产台账与证据边界
  page-locks/              # 每页结论、内容与版式锁定卡
  source/                  # 可编辑图表、拓扑、讲稿和 PPT 源
  output/                  # v0、v1… 的 .pptx/.pdf
  render/                  # 单页渲染图与 contact sheet
  qa/                      # 审稿、评分和修订记录
```

## 分支说明

| 分支 | 状态 | 用途 |
| --- | --- | --- |
| `main` | **生产分支** | 当前唯一安装与使用来源；包含两个独立 Office 技能及其模板/渲染/质检规则。 |
| `feature/split-report-ppt-skills` | 历史整合分支 | 用于开发阶段比对；含已弃用的 `robot-report-to-ppt-bridge`，不要安装。 |
| `feature/robot-report-build-skill` | 历史分支 | 报告技能早期开发记录。 |
| `feature/technical-defense-ppt-skill` | 历史分支 | PPT 技能早期开发记录。 |
| `feature/codex-provider-switch` | 历史/非 Office 分支 | 与 Office 文档生产无关，不作为本仓库的安装入口。 |

## 安装或同步到 Codex

克隆主分支后，仅复制这两个目录到 `%USERPROFILE%\.codex\skills\`：

```powershell
git clone --branch main https://github.com/haimichenha/office-skills.git
Copy-Item -Recurse -Force .\office-skills\skills\robot-report-suite "$env:USERPROFILE\.codex\skills\robot-report-suite"
Copy-Item -Recurse -Force .\office-skills\skills\technical-defense-ppt "$env:USERPROFILE\.codex\skills\technical-defense-ppt"
```

随后执行 VS Code 的 **Developer: Reload Window**，让技能列表重新加载。不要复制历史分支中的桥接技能。
