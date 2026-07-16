# 文档工具链与回退策略

## 角色分工

1. **OfficeCLI（推荐候选）**：用于可脚本化地创建/编辑 Office 文件、渲染预览以及“渲染后检查再修正”的循环。其本地优先的 Office 工作流和 Word/Excel/PPT 渲染能力适合成为后续报告交付管线的一部分。来源：[iOfficeAI/OfficeCLI](https://github.com/iOfficeAI/OfficeCLI)。
2. **Microsoft Word 或 LibreOffice**：负责旧式 `.doc` 到 `.docx` 的布局保真转换、模板样式继承和最终人工检查。
3. **python-docx**：只编辑 `.docx`，适合生成结构化段落、表格和插图；不能直接安全编辑旧式 `.doc`。
4. **Matplotlib + Mermaid/Graphviz**：生成可追溯的报告图，不承担 Word 排版。

## OfficeCLI 在报告工作区中的定位

OfficeCLI 负责**副本 `.docx` 的格式、布局、目录/交叉引用刷新、内容结构检查和渲染预览**，不负责替代图形源文件。报告图仍从 `figures/source/` 导出，再插入文档副本。

安装并完成小副本验证后，遵循其分层策略：先只读检查（`view outline` / `view issues`），再做结构化编辑，必要时才进入 XML 层；格式不确定时先查 `help`，不要猜参数。对于常规实训报告，应选择通用 `word` 工作流而不是期刊专用 `academic-paper` 工作流，除非学校明确给出了期刊/引用格式要求。

OfficeCLI 的核心接口面向 `.docx`；官方技能说明把 `.doc` 列为插件扩展能力。因此旧模板的转换保真必须先在副本上验证，不能假设可以直接编辑原 `.doc`。

## 推荐处理顺序

原模板是 `.doc` 时：

```text
原始 .doc（只读）
  -> Office/LibreOffice 转换得到 output/模板副本.docx
  -> 在副本上插入内容和图表
  -> OfficeCLI 或 Office/LibreOffice 导出 PDF/图片预览
  -> 人工检查版式并保留可编辑 .docx
```

如果 OfficeCLI 尚未安装或无法处理该模板，不能强行用 `python-docx` 打开 `.doc`；先使用可用的 Office 转换工具，或请用户提供 `.docx` 副本。安装新工具、调用网络服务、覆盖文件均需在实际生成前确认。

## 预检

运行：

```powershell
& "<skill-directory>\scripts\preflight_report_tools.ps1" -TemplatePath "<template-path>"
```

该脚本只报告模板和可用命令，不修改任何文件。

## PPT 源文件与渲染检查

PPT 同样遵循源文件副本 → 编辑 → 导出或渲染 → 目视检查 → 修正的循环。保护用户提供的 `.pptx`，在 `report-workspace/ppt/input/` 记录原文件名、大小、修改时间和哈希后，从新预览副本开始修改；流程图、曲线、视频关键帧和素材清单保留在 `ppt/source/`、`ppt/assets/` 与 `ppt/qa/`，不能只在 PowerPoint 内保留不可追溯的截图。

渲染时至少检查单页、整套 contact sheet、全尺寸文字/图例、暗底投影对比度、图片裁切、跨页对齐、视频备份和讲解备注。输出应版本化放在 `ppt/output/`，渲染图放在 `ppt/render/`；无法渲染时，先保留可编辑源和待检项，不猜测版式已经正确。
