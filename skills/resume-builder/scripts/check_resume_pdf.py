#!/usr/bin/env python3
"""Read-only page-count and link check for a rendered resume PDF."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a resume PDF without modifying it.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--expect-pages", type=int, default=1)
    args = parser.parse_args()
    if not args.pdf.is_file():
        raise SystemExit(f"PDF not found: {args.pdf}")
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise SystemExit("PyMuPDF is required: python -m pip install pymupdf") from exc
    document = fitz.open(args.pdf)
    pages = []
    link_count = 0
    for index, page in enumerate(document):
        rect = page.rect
        links = page.get_links()
        link_count += len(links)
        pages.append({"page": index + 1, "width_pt": round(rect.width, 1), "height_pt": round(rect.height, 1), "links": len(links)})
    result = {"file": str(args.pdf), "pages": len(document), "expected_pages": args.expect_pages, "link_count": link_count, "page_details": pages}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if len(document) == args.expect_pages else 2


if __name__ == "__main__":
    raise SystemExit(main())
