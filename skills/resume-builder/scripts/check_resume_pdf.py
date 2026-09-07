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
    parser.add_argument("--expect-url", action="append", default=[], help="Require URL in both visible text and URI annotations; repeatable.")
    parser.add_argument("--forbid-text", action="append", default=[], help="Reject production notes in extracted text; repeatable.")
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
    visible_text = []
    uris = set()
    for index, page in enumerate(document):
        rect = page.rect
        links = page.get_links()
        link_count += len(links)
        visible_text.append(page.get_text())
        uris.update(link.get("uri") for link in links if link.get("uri"))
        pages.append({"page": index + 1, "width_pt": round(rect.width, 1), "height_pt": round(rect.height, 1), "links": len(links)})
    text = "\n".join(visible_text)
    missing_visible = [url for url in args.expect_url if url not in text]
    missing_clickable = [url for url in args.expect_url if url not in uris]
    forbidden_found = [phrase for phrase in args.forbid_text if phrase in text]
    ok = len(document) == args.expect_pages and not (missing_visible or missing_clickable or forbidden_found)
    result = {"file": str(args.pdf), "pages": len(document), "expected_pages": args.expect_pages, "link_count": link_count, "page_details": pages, "missing_visible_urls": missing_visible, "missing_clickable_urls": missing_clickable, "forbidden_text_found": forbidden_found, "passed": ok}
    document.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
