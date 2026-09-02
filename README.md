# Resume Skills

面向校招、实习与项目型求职简历的 Codex 技能仓库。`main` 是唯一安装入口，当前只维护一个生产技能：[`resume-builder`](skills/resume-builder/SKILL.md)。

## 能做什么

- 收集并比较简历模板，提炼版式元素而非复制他人的个人信息；
- 保护原始模板、证书、项目资料、照片与既有简历，建立可追溯的资料台账；
- 将教育、获奖、项目职责、技术栈和完整项目链接组织为一页或两页简历；
- 使用克制的黑、灰、留白和少量分隔，避免密集蓝线与大面积蓝色填充；
- 根据照片比例选择：优先保留用户认可母版；用户要求时以表格为网格基准精调“浮于文字上方”的照片，只有明确需要稳定齐平时才嵌入；
- 导出 PDF、检查页数、链接、溢出与可读性，并以 `v1`、`v2`… 保留版本。
- 防止常见错误：不覆盖/误删可用版本，不把完整正文摘要成短版，不把已认可版式重建成古怪新样式。

## 工作流

```text
模板收集 → 原始资料入库 → 事实/链接台账 → 内容保留与取舍 → 版式与照片 → PDF 渲染质检 → 版本化交付
```

在开始时运行：

```powershell
python .\skills\resume-builder\scripts\init_resume_workspace.py D:\resume-workspace
```

然后将**副本**放入 `input/templates/`、`input/materials/` 与 `input/photo/`。原件不直接覆盖；`brief/`、`evidence/`、`draft/`、`output/`、`qa/` 分别存放需求、核实资料、可编辑版本、交付件和渲染检查。

PDF 一页检查：

```powershell
python .\skills\resume-builder\scripts\check_resume_pdf.py D:\resume-workspace\output\resume_v1.pdf --expect-pages 1
```

## 安装到 Codex

```powershell
git clone --branch main https://github.com/haimichenha/resume-skills.git
Copy-Item -Recurse -Force .\resume-skills\skills\resume-builder "$env:USERPROFILE\.codex\skills\resume-builder"
```

随后执行 VS Code 的 **Developer: Reload Window**。
