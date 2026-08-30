#!/usr/bin/env python3
"""Create a non-destructive workspace for a resume production run."""
from __future__ import annotations

import argparse
from pathlib import Path

DIRECTORIES = (
    "input/templates",
    "input/materials",
    "input/photo",
    "brief",
    "evidence",
    "draft",
    "output",
    "qa",
)

LEDGER = """# 简历资料台账

| ID | 分类 | 可写事实 | 证据/完整链接 | 状态 | 简历去向 |
| --- | --- | --- | --- | --- | --- |
"""
BRIEF = """# 简历需求

- 目标岗位：
- 投递语言：
- 目标页数：一页 / 两页
- 是否使用照片：
- 目标地点/到岗时间：
- 必须保留的项目、事实和链接：
- 明确不写入的内容：
"""
FORMAT = """# 格式约束

- 主色：黑 / 深灰 / 浅灰；避免密集蓝线和大面积蓝色填充。
- 版本命名：姓名_方向_实习简历_vN.docx/.pdf。
- 照片：优先嵌入型图片 + 表格单元格水平/垂直居中。
"""
REVISION = """# 修订记录

| 版本 | 用户反馈 | 修改项 | PDF 检查 |
| --- | --- | --- | --- |
"""


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a resume workspace without touching source files.")
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    root = args.workspace.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    for relative in DIRECTORIES:
        (root / relative).mkdir(parents=True, exist_ok=True)
    write_if_missing(root / "evidence" / "material-ledger.md", LEDGER)
    write_if_missing(root / "brief" / "resume-brief.md", BRIEF)
    write_if_missing(root / "brief" / "format-contract.md", FORMAT)
    write_if_missing(root / "qa" / "revision-log.md", REVISION)
    print(f"Workspace ready: {root}")
    print("Copy source files into input/; do not overwrite originals.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
