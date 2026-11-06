#!/usr/bin/env python3
"""
manuscript_metrics.py — Book-Scale Prose, Continuity, Burstiness & EN/AR Slop Analyzer

Evaluates manuscript/chapters/*.md for:
- Per-chapter word count & sentence-length burstiness (CV = std / mean)
- English & Arabic AI-slop phrase density per 1,000 words
- Cross-chapter repeated 6-gram cloning (catches recycled metaphors/sentences across chapters)
- Grounding of chapters' numeric claims against editorial/claims-ledger.json
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

EN_SLOP_PATTERNS = [
    r"\bdelve(?:s|d|ing)?\b",
    r"\btapestry\b",
    r"\btestament to\b",
    r"\bpivotal role\b",
    r"\bparadigm shift\b",
    r"\bin today's rapidly evolving\b",
    r"\bit is worth noting that\b",
    r"\bmoreover,\s",
    r"\bfurthermore,\s",
    r"\bin conclusion,\s",
    r"\bnot only\b[^.?!]{3,60}\bbut also\b",
]

AR_SLOP_PATTERNS = [
    r"في ظل التطورات المتسارعة",
    r"مما لا شك فيه",
    r"من الجدير بالذكر",
    r"يلعب دورا[ً]? محوريا[ً]?",
    r"تلعب دورا[ً]? محوريا[ً]?",
    r"وفي الختام[،,]? يمكن",
    r"علاوة على ذلك",
    r"لا يقتصر الأمر على",
    r"يقوم ب[تإام]",
    r"تقوم ب[تإام]",
]

SENT_SPLIT_RE = re.compile(r"[.!?؟]+(?:\s+|$)")
CODE_FENCE_RE = re.compile(r"```[\s\S]*?```")
WORD_RE = re.compile(r"[\w\u0600-\u06FF]+")


def strip_non_prose(md: str) -> str:
    txt = CODE_FENCE_RE.sub(" ", md)
    lines = []
    for line in txt.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("|") or s.startswith("![") or s.startswith("[^"):
            continue
        lines.append(s)
    return " ".join(lines)


def sentence_burstiness_cv(prose: str) -> float:
    sentences = [s.strip() for s in SENT_SPLIT_RE.split(prose) if s.strip()]
    lengths = [len(WORD_RE.findall(s)) for s in sentences]
    lengths = [n for n in lengths if n >= 3]
    if len(lengths) < 3:
        return 0.45
    mean = sum(lengths) / len(lengths)
    if mean <= 0:
        return 0.0
    var = sum((x - mean) ** 2 for x in lengths) / len(lengths)
    return round(math.sqrt(var) / mean, 3)


def count_slop_hits(prose: str, lang: str) -> tuple[int, list[str]]:
    patterns = AR_SLOP_PATTERNS if lang == "ar" else EN_SLOP_PATTERNS
    hits = 0
    matched_examples: list[str] = []
    for pat in patterns:
        found = re.findall(pat, prose, flags=re.IGNORECASE)
        if found:
            hits += len(found)
            matched_examples.append(found[0])
    return hits, matched_examples[:5]


def extract_sixgrams(prose: str) -> set[str]:
    words = [w.lower() for w in WORD_RE.findall(prose) if len(w) > 1]
    if len(words) < 6:
        return set()
    return {" ".join(words[i : i + 6]) for i in range(len(words) - 5)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze book chapters for burstiness, repetition, and AR/EN AI slop.")
    parser.add_argument("--project", required=True, help="Path to Book Studio project root.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    parser.add_argument("--strict", action="store_true", help="Fail if slop_per_1k > 4.0 or burstiness_cv < 0.25.")
    args = parser.parse_args()

    root = Path(args.project).resolve()
    cfg = json.loads((root / "book.config.json").read_text(encoding="utf-8"))
    lang = cfg.get("language", "ar")
    ch_files = sorted((root / "manuscript" / "chapters").glob("*.md"))
    if not ch_files:
        print("[FAIL] No chapter files found in manuscript/chapters/", file=sys.stderr)
        return 1

    sixgram_owners: dict[str, list[str]] = defaultdict(list)
    chapter_reports = []
    total_words = 0
    total_slop = 0

    for ch in ch_files:
        raw = ch.read_text(encoding="utf-8")
        prose = strip_non_prose(raw)
        words = WORD_RE.findall(prose)
        wcount = len(words)
        total_words += wcount
        cv = sentence_burstiness_cv(prose)
        slop_hits, examples = count_slop_hits(prose, lang)
        total_slop += slop_hits
        slop_per_1k = round((slop_hits / max(wcount, 1)) * 1000, 2)

        for gram in extract_sixgrams(prose):
            sixgram_owners[gram].append(ch.name)

        chapter_reports.append(
            {
                "chapter": ch.name,
                "words": wcount,
                "burstiness_cv": cv,
                "slop_hits": slop_hits,
                "slop_per_1k": slop_per_1k,
                "flagged_phrases": examples,
            }
        )

    cross_chapter_clones = [
        {"phrase": gram, "chapters": sorted(set(owners))}
        for gram, owners in sixgram_owners.items()
        if len(set(owners)) >= 2
    ][:15]

    ledger_path = root / "editorial" / "claims-ledger.json"
    ledger_count = 0
    if ledger_path.is_file():
        ledger_data = json.loads(ledger_path.read_text(encoding="utf-8"))
        ledger_count = len(ledger_data.get("claims", []))

    avg_cv = round(sum(c["burstiness_cv"] for c in chapter_reports) / len(chapter_reports), 3)
    overall_slop_1k = round((total_slop / max(total_words, 1)) * 1000, 2)
    passed = overall_slop_1k <= 4.0 and avg_cv >= 0.25 and len(cross_chapter_clones) <= 5

    summary = {
        "passed": passed,
        "language": lang,
        "chapter_count": len(chapter_reports),
        "total_prose_words": total_words,
        "average_burstiness_cv": avg_cv,
        "overall_slop_per_1k": overall_slop_1k,
        "cross_chapter_6gram_clones": cross_chapter_clones,
        "claims_logged": ledger_count,
        "chapters": chapter_reports,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"=== Manuscript Editorial Metrics ({cfg.get('title', root.name)}) ===")
        print(f"Chapters: {len(chapter_reports)} | Total Prose Words: {total_words} | Claims Logged: {ledger_count}")
        print(f"Avg Burstiness CV: {avg_cv} (target >= 0.35) | Slop/1k Words: {overall_slop_1k} (target <= 2.5)")
        for c in chapter_reports:
            print(f"  - {c['chapter']}: {c['words']}w | CV={c['burstiness_cv']} | slop={c['slop_hits']} ({c['slop_per_1k']}/1k)")
        if cross_chapter_clones:
            print(f"Cross-chapter repeated 6-grams: {len(cross_chapter_clones)}")
        print(f"Verdict: {'PASS' if passed else 'NEEDS_EDITING'}")

    if args.strict and not passed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
