---
name: robot-report-suite
description: 面向机器人实训高级报告与技术答辩 PPT 的模板保护、证据整理、流程/信号图制作、证据化写作、视觉重构和渲染质检工作流。用户提供实验图片、日志、视频、报告模板、PPT 或分章节/分页面要求时使用。
---

# 机器人实训报告套件

本技能服务于本项目的 `机器人工程实训高级报告模板.doc`。目标是把可核查的实验材料组织成一份可编辑、可复现、可审阅的报告；不是在没有证据时虚构实验结论。

## 核心约束

1. **保护模板**：绝不直接改写根目录的原始 `.doc`。所有编辑都在 `report-workspace/output/` 的副本中进行；先记录原始模板的路径、大小和修改时间。
2. **先证据、后表述**：每项陈述标注为 `实测证据`、`用户确认`、`推导/待验证` 三者之一。没有日志、照片或用户确认的数据不写成已完成结果。
3. **图源可编辑**：流程图/结构图保存 Mermaid 或 Graphviz 源文件；曲线和信号图保存生成脚本与数据来源。交付图仅是导出物，不能是唯一源文件。
4. **小步交付**：一次只完成用户指定的一个章节或图组，完成后提供该部分的证据清单、待补材料和渲染检查结果。
5. **报告优先，PPT 复用**：先固定报告的论点、图和数据，再按同一证据清单提炼答辩 PPT；PPT 不引入报告中没有根据的新结论。
6. **摘要后置**：摘要、关键词和摘要中的定量结论必须在全部正文、图表、结论和局限性定稿后编写；正文阶段仅保留摘要位置和待写标记。
7. **自然实验文风**：使用具体的实验对象、操作、参数、观察和限制来叙述，避免空泛模板句、重复连接词和无证据的“显著/有效/先进”等评价。详见 `references/writing-style.md`。

## 推荐工作区

首次开始实际写报告时，在项目内建立如下工作区（仅在用户确认开始生成时创建）：

```text
report-workspace/
  input/                 # 原模板副本、用户提供的原始材料（只读保留）
  evidence/              # 图片、串口日志、测量表与来源说明
  figures/source/        # .mmd/.dot/.py/.csv 等可编辑图源
  figures/export/        # 插入 Word/PPT 的 .svg/.png/.pdf
  sections/              # 各章节草稿与引用清单
  output/                # 可交付 .docx/.pdf/.pptx，绝不覆盖模板
  manifest.json          # 材料、图号、结论状态、版本和待办
  ppt/                   # 答辩 PPT 专用工作区（报告稳定后再建立）
    input/               # 原 PPT、用户素材副本及其哈希/只读说明
    brief/               # 受众、时长、叙事与答辩问题
    assets/              # 素材清单、视频关键帧与来源说明
    page-locks/          # 每页结论、裁切和视觉锁定卡
    source/              # 可编辑图、图表和 PPT 源
    output/              # 版本化 .pptx/.pdf 交付物，绝不覆盖输入
    preview/             # 最多保留最近三个可丢弃预览版本
    render/              # 单页渲染图和整套 contact sheet
    qa/                  # 结构检查、审稿记录和页序检查
    notes/               # 讲述节拍、证据回指和 Q&A 提示
```

## 执行顺序

### 阶段 A：预检和模板盘点

1. 运行 `scripts/preflight_report_tools.ps1`，只读取模板和本机工具状态。
2. 对旧式 `.doc`，优先转换为保留原布局的 `.docx` 副本后再编辑；不要用 `python-docx` 直接修改 `.doc`。
3. 建立章节清单、图表编号和证据台账。详细规则见 `references/core.md`。

### 阶段 B：证据到章节

每个章节先建立以下最小卡片，再写正文：

```text
章节：
目标/问题：
可用证据（文件路径 + 来源 + 时间）：
允许使用的参数：
需要制作的图/表：
仍待用户确认的内容：
```

正文使用“目的 → 方案 → 实现 → 测试证据 → 结果与限制”的顺序。硬件连接、PWM、蓝牙控制、舵机串口、陀螺仪/LADRC 等内容应只以当前代码、日志和实测照片能够支持的粒度描述。

### 阶段 C：图、表与信号

按 `references/figures.md` 和 `references/figure-workflow.md` 选择工具。图形制作采用 `create-figure` 的“先确认意图/证据，再选择后端，最后保留可复现导出物”思想；流程和结构图采用官方 Draw.io 的可编辑 `.drawio` 格式作为优先源。两者均只借鉴经核验的工作流，不依赖其私有运行时或未安装命令：

- 过程、硬件结构、通信时序、软件状态：Draw.io；
- 未安装 Draw.io 时的简洁过程/时序：Mermaid；
- 无额外安装的结构关系图：Graphviz；
- PWM、串口、姿态、响应等定量曲线：Matplotlib；
- 用户照片：只做裁剪、标注和统一编号，保留原图。

每幅图必须有图号、标题、图源路径、输入数据来源和结论状态。不要把示意图误标为实测波形。

### 阶段 D：文档质检

采用“生成 → 渲染 → 目视检查 → 修正”的循环。检查页边距、标题层级、目录、中文字体、图表编号、跨页表格、图片清晰度、引用与结论是否一一对应。工具优先级及回退方案见 `references/toolchain.md`。

### 阶段 D.5：摘要门

只有同时满足下列条件，才开始写摘要：

- 正文各章节、图表和结论已经定稿；
- 文中所有数值、测试条件、局限性已核验；
- 摘要中的“完成内容、方法、结果、结论”均能回链到正文；
- 摘要放回模板规定的摘要位置，并与关键词一起进行一次渲染检查。

在此之前，摘要位置只能显示“正文定稿后编写”，不得提前生成看似完整的摘要。

### 阶段 E：PPT 衔接与技术答辩生产（可选）

报告章节稳定后，先读 `references/presentation-bridge.md`，再执行下列顺序：

1. 在 `report-workspace/ppt/brief/` 确定受众、总时长、页数、报告版本、必须回答的问题和已知限制。
2. 用 `references/ppt-asset-manifest-template.md` 盘点照片、视频关键帧、日志、曲线、流程图和外部氛围素材；明确每项素材能证明与不能证明什么。
3. 用 `references/ppt-production-system.md` 建立“单页结论—证据—讲解节奏”映射；常规整套先校准封面、最难技术页、最强验证页三张，再扩展整套；1—3 页短 deck 按其中的短 deck 例外执行。
4. 用 `references/ppt-page-lock-template.md` 固定每页的 Hero 主证据、Support 支撑材料、Finish 编辑收尾层、裁切、比例、配色角色和相邻页差异，不能先堆卡片再补装饰。
5. 按 `references/ppt-design-language.md` 选择页面视觉语法，并按 `references/ppt-review-rubric.md` 导出逐页审稿；不通过时先纠正结论和证据，再修正布局、裁切和材质，最后才加装饰。
6. 依 `references/ppt-validation-plan.md` 核对输入保护、素材追溯、投影可读性、渲染工件和前向测试；未通过硬门的版本不得作为交付候选。

PPT 使用与报告相同的图源、编号和数据，不与报告形成两套相互矛盾的结论。外部或生成图仅能承担氛围/解释层，不能伪装成实车或实测证据。

## 用户后续提供材料时的输入格式

用户可按如下格式一次提供一个部分；缺项可留空：

```text
章节/小节：
想说明的内容：
图片、日志、代码或数据路径：
必须保留的文字/参数：
希望的图或表：
尚不确定、需要我标为待验证的内容：
```

收到材料后，先返回该部分的证据卡片和拟制图表清单；得到确认或材料充分时再写入报告副本。

## 参考文件

- `references/core.md`：证据、章节和验收规则。
- `references/writing-style.md`：自然、具体、实验记录式的中文写作与摘要后置规则。
- `references/figures.md`：流程图、结构图、信号图的选型与交付格式。
- `references/figure-workflow.md`：基于 `create-figure` 适配的本地证据门、后端路由和图形验收。
- `references/upstream-selection.md`：已锁定的 Figure/Office 两个仓库及补充资源的采用边界。
- `references/toolchain.md`：OfficeCLI、Office/LibreOffice 与 Python 的职责边界。
- `references/resource-radar.md`：已核验的外部技能/工具候选、采用范围与暂不安装原因。
- `references/presentation-bridge.md`：从报告到答辩 PPT 的叙事与证据映射。
- `references/ppt-production-system.md`：PPT 资产先行、页面锁定、逐页渲染审稿与交付工作流。
- `references/ppt-asset-manifest-template.md`：全套素材、页面资产映射、视频与缺料队列模板。
- `references/ppt-design-language.md`：高质量技术答辩的色彩、网格、字体、图片处理与反重复规则。
- `references/ppt-page-lock-template.md`：单页视觉与证据锁定卡。
- `references/ppt-review-rubric.md`：100 分审稿量表、硬失败项和修订顺序。
- `references/ppt-validation-plan.md`：输入保护、可交付工件、QA 门禁与前向测试合同。
