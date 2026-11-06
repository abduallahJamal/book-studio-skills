#!/usr/bin/env python3
"""
scaffold_outline.py — Generate or validate editorial/outline.json, voice-lock.md,
book-bible.md, art-bible.md, and optional chapter stub files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HOOK_ROTATION = [
    "concrete-incident",
    "counterintuitive-paradox",
    "historical-origin",
    "field-observation",
    "diagnostic-question",
    "failure-postmortem",
]


def build_default_outline(cfg: dict, num_chapters: int, words_per_chapter: int) -> dict:
    is_ar = cfg.get("language", "ar") == "ar"
    chapters = []
    for idx in range(1, num_chapters + 1):
        hook = HOOK_ROTATION[(idx - 1) % len(HOOK_ROTATION)]
        if is_ar:
            title = f"الفصل {idx}: محور البحث والتطبيق ({idx})"
            question = f"ما المشكلة الجوهرية التي يحسمها الفصل {idx} دون تكرار ما سبقه؟"
            takeaway = f"قاعدة عملية قابلة للتطبيق المباشر من الفصل {idx}."
            sections = [f"مدخل الفصل {idx}", f"التحليل البنيوي والآليات", f"دراسة حالة وتطبيق عملي"]
        else:
            title = f"Chapter {idx}: Core Mechanism & Practice ({idx})"
            question = f"What specific problem does Chapter {idx} resolve without repeating prior chapters?"
            takeaway = f"Concrete operational principle established in Chapter {idx}."
            sections = [f"Opening Frame", f"Core Architecture & Trade-offs", f"Field Case Study"]

        chapters.append(
            {
                "number": idx,
                "id": f"ch-{idx:02d}",
                "file": f"manuscript/chapters/ch-{idx:02d}.md",
                "title": title,
                "opening_hook_type": hook,
                "core_question": question,
                "key_takeaway": takeaway,
                "target_words": words_per_chapter,
                "sections": sections,
                "planned_figures": [f"fig-{idx:02d}-diagram.svg"] if idx <= 3 else [],
            }
        )

    return {
        "title": cfg.get("title", ""),
        "language": cfg.get("language", "ar"),
        "direction": cfg.get("direction", "rtl"),
        "style_pack": cfg.get("style_pack", "trade-nonfiction"),
        "total_target_words": num_chapters * words_per_chapter,
        "voice_locked": True,
        "chapters": chapters,
    }


def validate_outline(outline_path: Path) -> list[str]:
    errors: list[str] = []
    if not outline_path.is_file():
        return [f"Missing outline file: {outline_path}"]
    data = json.loads(outline_path.read_text(encoding="utf-8"))
    chapters = data.get("chapters", [])
    if not chapters:
        errors.append("outline.json contains zero chapters")
        return errors

    seen_ids: set[str] = set()
    seen_titles: set[str] = set()
    prev_hook = None
    for ch in chapters:
        cid = ch.get("id", "")
        title = ch.get("title", "").strip()
        hook = ch.get("opening_hook_type", "")
        if not cid or cid in seen_ids:
            errors.append(f"Duplicate or empty chapter id: '{cid}'")
        seen_ids.add(cid)
        if not title or title in seen_titles:
            errors.append(f"Duplicate or empty chapter title: '{title}'")
        seen_titles.add(title)
        if hook and hook == prev_hook:
            errors.append(f"Consecutive identical opening_hook_type '{hook}' in {cid}")
        prev_hook = hook
        if int(ch.get("target_words", 0)) < 150:
            errors.append(f"target_words too small (<150) in {cid}")
        if not ch.get("core_question"):
            errors.append(f"Missing core_question in {cid}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold or validate Book Studio editorial architecture.")
    parser.add_argument("--project", required=True, help="Path to Book Studio project root.")
    parser.add_argument("--chapters", type=int, default=6, help="Number of chapters to scaffold.")
    parser.add_argument("--words-per-chapter", type=int, default=2000, help="Target word count per chapter.")
    parser.add_argument("--scaffold-chapters", action="store_true", help="Create stub chapter Markdown files if absent.")
    parser.add_argument("--validate-only", action="store_true", help="Validate existing editorial/outline.json.")
    args = parser.parse_args()

    root = Path(args.project).resolve()
    cfg_path = root / "book.config.json"
    if not cfg_path.is_file():
        raise SystemExit(f"Error: missing {cfg_path} (run init_book.py first)")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    editorial = root / "editorial"
    editorial.mkdir(parents=True, exist_ok=True)
    outline_path = editorial / "outline.json"

    if args.validate_only:
        errs = validate_outline(outline_path)
        if errs:
            for e in errs:
                print(f"[FAIL] {e}")
            return 1
        data = json.loads(outline_path.read_text(encoding="utf-8"))
        print(f"[OK] Validated outline.json: {len(data['chapters'])} chapters, "
              f"target {data.get('total_target_words', 0)} words.")
        return 0

    if not outline_path.exists():
        outline = build_default_outline(cfg, args.chapters, args.words_per_chapter)
        outline_path.write_text(json.dumps(outline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        outline = json.loads(outline_path.read_text(encoding="utf-8"))

    voice_path = editorial / "voice-lock.md"
    if not voice_path.exists():
        is_ar = cfg.get("language", "ar") == "ar"
        voice_path.write_text(
            "# قفل الهوية الصوتية والأسلوبية (Voice Lock)\n\n"
            "- **النبرة:** رصينة، مباشرة، مدعومة بالأمثلة الميدانية والأرقام الموثقة.\n"
            "- **إيقاع الجمل:** المزج بين الجمل التقريرية القصيرة والجمل التحليلية المركبة (`Burstiness CV >= 0.40`).\n"
            "- **التراكيب الممنوعة:** يمنع استخدام مقدمات الذكاء الاصطناعي المعلبة («في ظل التطورات المتسارعة»، «مما لا شك فيه»، والإفراط في «تم + المصدر»).\n"
            if is_ar
            else "# Voice Lock Specification\n\n"
            "- **Register:** Clear, grounded practitioner voice with concrete mechanisms over abstract hype.\n"
            "- **Cadence:** Deliberate variation in sentence length (`Burstiness CV >= 0.40`).\n"
            "- **Banned Slop:** Zero 'delve', 'tapestry', 'Moreover,' stacks, or 'Not only X, but also Y' cliches.\n",
            encoding="utf-8",
        )

    if args.scaffold_chapters:
        ch_dir = root / "manuscript" / "chapters"
        ch_dir.mkdir(parents=True, exist_ok=True)
        for ch in outline["chapters"]:
            p = root / ch["file"]
            if not p.exists():
                secs = "\n\n".join(f"## {s}\n\n<!-- Draft section: {s} -->" for s in ch.get("sections", []))
                p.write_text(f"# {ch['title']}\n\n{secs}\n", encoding="utf-8")

    errs = validate_outline(outline_path)
    if errs:
        for e in errs:
            print(f"[FAIL] {e}")
        return 1

    print(f"[OK] Book architecture ready at {editorial} ({len(outline['chapters'])} chapters).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
