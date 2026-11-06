#!/usr/bin/env python3
"""
init_book.py — Initialize a standardized Bilingual (AR RTL / EN LTR) Book Studio workspace.

Creates:
- book.config.json
- manuscript/{frontmatter,chapters,backmatter}/
- editorial/{outline.json,book-bible.md,art-bible.md,claims-ledger.json}
- assets/figures/
- dist/
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

VALID_TRIMS = {"5x8", "5.25x8", "5.5x8.5", "6x9", "7x10", "8.5x11", "a5", "b5"}
VALID_STYLES = {
    "trade-nonfiction",
    "literary-novel",
    "technical-code",
    "academic-monograph",
    "executive-report",
    "classic-arabic-turath",
}
VALID_STOCKS = {"white", "cream", "color-standard", "color-premium"}


def slugify(value: str) -> str:
    ascii_slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return ascii_slug or "book-project"


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a new Book Studio project workspace.")
    parser.add_argument("--dir", required=True, help="Target directory for the new book workspace.")
    parser.add_argument("--title", required=True, help="Book main title.")
    parser.add_argument("--subtitle", default="", help="Optional book subtitle.")
    parser.add_argument("--author", required=True, help="Primary author name.")
    parser.add_argument("--publisher", default="", help="Publisher or imprint name.")
    parser.add_argument("--lang", default="ar", choices=["ar", "en"], help="Book primary language (ar or en).")
    parser.add_argument("--style", default="trade-nonfiction", choices=sorted(VALID_STYLES), help="Typography style pack.")
    parser.add_argument("--trim", default="6x9", choices=sorted(VALID_TRIMS), help="Print trim size.")
    parser.add_argument("--paper", default="white", choices=sorted(VALID_STOCKS), help="KDP/IngramSpark paper stock.")
    parser.add_argument("--slug", default="", help="Optional URL/file slug.")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    is_ar = args.lang == "ar"
    direction = "rtl" if is_ar else "ltr"
    slug = args.slug.strip() or (slugify(args.title) if not is_ar else f"arabic-book-{root.name}")
    year = datetime.now(timezone.utc).year

    for sub in [
        "manuscript/frontmatter",
        "manuscript/chapters",
        "manuscript/backmatter",
        "editorial",
        "assets/figures",
        "dist",
    ]:
        (root / sub).mkdir(parents=True, exist_ok=True)

    config = {
        "slug": slug,
        "language": args.lang,
        "direction": direction,
        "title": args.title,
        "subtitle": args.subtitle or ("رؤية عملية متكاملة" if is_ar else "A Practical Field Guide"),
        "author": args.author,
        "publisher": args.publisher or ("دار النشر المستقلة" if is_ar else "Independent Press"),
        "publication_year": year,
        "copyright_holder": args.author,
        "isbn": {
            "paperback": "978-0-000000-00-2",
            "hardcover": "978-0-000000-01-9",
            "ebook": "978-0-000000-02-6",
        },
        "style_pack": args.style,
        "engines": ["typst", "html", "quarto"],
        "print": {
            "trim": args.trim,
            "paper_stock": args.paper,
            "ink": "bw",
            "bleed_in": 0.125,
            "min_pages": 24,
            "editions": ["paperback", "hardcover", "large-print"],
        },
        "digital": {
            "epub3": True,
            "web_book": True,
        },
        "humanizer": {
            "enabled": True,
            "voice": "clear-thinker",
        },
    }

    (root / "book.config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    preface = root / "manuscript/frontmatter/01-preface.md"
    if not preface.exists():
        if is_ar:
            preface.write_text(
                "# مقدمة المؤلف\n\nوضع هذا الكتاب ليكون دليلاً عملياً واضحاً يجمع بين الدقة الهندسية وسلاسة الأسلوب العربي الفصيح.\n",
                encoding="utf-8",
            )
        else:
            preface.write_text(
                "# Preface\n\nThis book was written as a practical, grounded guide uniting rigorous craft with clear prose.\n",
                encoding="utf-8",
            )

    ch1 = root / "manuscript/chapters/ch-01.md"
    if not ch1.exists():
        if is_ar:
            ch1.write_text(
                "# الفصل الأول: نقطة الانطلاق\n\nابدأ كتابة متن الفصل الأول هنا، أو استخدم مهارة `book-intake` لاستيراد مخطوطتك الجاهزة.\n",
                encoding="utf-8",
            )
        else:
            ch1.write_text(
                "# Chapter 1: Starting Point\n\nDraft your opening chapter here, or run `book-intake` to import an existing manuscript.\n",
                encoding="utf-8",
            )

    (root / "editorial/claims-ledger.json").write_text(
        json.dumps({"claims": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "editorial/book-bible.md").write_text(
        "# Book Bible & Terminology Lock\n\n- Maintain consistent terminology, character/concept definitions, and tone across all chapters.\n",
        encoding="utf-8",
    )
    (root / "editorial/art-bible.md").write_text(
        "# Art & Diagram Bible\n\n- Zero embedded text inside raster illustrations.\n- Minimum 300 effective DPI at print trim width.\n",
        encoding="utf-8",
    )

    print(f"[OK] Initialized Book Studio project at: {root}")
    print(f"     Language/Direction : {args.lang} ({direction.upper()})")
    print(f"     Style Pack / Trim  : {args.style} @ {args.trim}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
