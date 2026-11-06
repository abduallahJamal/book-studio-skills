---
name: book
description: "Orchestrate end-to-end Arabic (RTL) and English (LTR) book creation, manuscript intake, Tri-Engine typesetting (Typst, HTML/CSS, LaTeX/Quarto), KDP/IngramSpark cover wrap, EPUB 3 + Web Book, and 15-gate preflight QC via a strict dependency graph."
---

# `book` — Master Book Studio Orchestrator (`/book`)

You are the chief publishing engineer for `book-studio-skills`. Route every user book request to the right specialist skill while enforcing **non-negotiable physical print dependencies**.

## 1. Non-Negotiable Cross-Bench Dependency Law

Never violate physical print causality:

```text
book.config.json (trim + language + direction + style_pack)
   ├─► Path A (Existing .docx/.pdf/.md) ──► book-intake (manuscript/ + manuscript.lock.json)
   └─► Path B (Topic / Raw Idea) ─────────► book-architect ──► book-drafter (+ humanizer-skills)
                                                    │
                                                    ▼
                                            book-illustrator (300 DPI + clean SVGs)
                                                    │
                                                    ▼
                                            book-typesetter (interior-paperback.pdf + actual page count N)
                                                    │
                        ┌───────────────────────────┴───────────────────────────┐
                        ▼ (reads ACTUAL N from PDF!)                            ▼ (parallel from Markdown Master)
                book-cover-wrap                                         book-ebook-web
        (KDP caliper spine + RTL/LTR mirror)                    (EPUB 3 + MathML + Static Web Book)
                        │                                                       │
                        └───────────────────────────┬───────────────────────────┘
                                                    ▼
                                            book-preflight-qc
                            (pikepdf PDF/X-1a + 15 PyMuPDF Gates + Contact Sheets)
                                                    │
                                                    ▼
                                           dist/press-ready/
```

**Hard Rule:** Never generate a final print wraparound cover (`book-cover-wrap`) before `book-typesetter` has compiled the final interior PDF and locked its exact even page count `N`. Guessing page count shifts spine hinges onto the front cover and triggers immediate KDP/IngramSpark rejection.

## 2. Environment Check & Project Initialization

Before starting a new workspace or diagnosing build issues, run the bundled CLIs:

```bash
# 1. Inspect Python pro packages (pymupdf, pikepdf, Pillow, python-docx), Typst, Ghostscript & AR/EN fonts
python3 skills/book/scripts/doctor.py

# 2. Initialize a new Arabic (RTL) or English (LTR) book workspace
python3 skills/book/scripts/init_book.py \
  --dir ./my-book \
  --title "هندسة الأنظمة الوكيلية" \
  --author "عبد الله جمال" \
  --lang ar \
  --style technical-code \
  --trim 6x9
```

See [`references/book-config-schema.md`](references/book-config-schema.md) for the complete `book.config.json` contract, trim table, and paper stock calipers.

## 3. Routing Table (`One Skill, One Job`)

| User Intent | Target Skill | Deterministic CLI |
| :--- | :--- | :--- |
| Import `.docx`, `.pdf`, or scattered `.md` drafts without losing footnotes or words | `book-intake` | `skills/book-intake/scripts/import_manuscript.py` |
| Turn a topic/idea into a chapter outline, Voice Lock sample, Book Bible & Art Bible | `book-architect` | `skills/book-architect/scripts/scaffold_outline.py` |
| Write chapters, ground facts in a Claim Ledger, remove AI slop & run Beta-Reader gate | `book-drafter` | `skills/book-drafter/scripts/manuscript_metrics.py` |
| Prepare SVG diagrams, Mermaid charts, 300 DPI figures & transparent chapter openers | `book-illustrator` | `skills/book-illustrator/scripts/prepare_figures.py` |
| Typeset `Paperback`, `Hardcover`, `Large-Print 16pt` or `Screen` via Typst, HTML/CSS, or Quarto/LaTeX | `book-typesetter` | `skills/book-typesetter/scripts/build_interior.py` |
| Calculate exact spine width, mirror RTL/LTR panels & render KDP full-wrap + eBook cover | `book-cover-wrap` | `skills/book-cover-wrap/scripts/calc_and_render_cover.py` |
| Export validated `EPUB 3` (`MathML`, RTL spine) and searchable Static HTML Web Book | `book-ebook-web` | `skills/book-ebook-web/scripts/build_epub_and_web.py` |
| Distill `CMYK PDF/X-1a`, run all 15 physical geometry/font/TOC gates & render contact sheets | `book-preflight-qc` | `skills/book-preflight-qc/scripts/preflight_qc.py` |

## 4. Bilingual Arabic (`RTL`) & English (`LTR`) Guardrails

- When `language` starts with `ar` (`direction: "rtl"`):
  1. Interior gutters mirror for right-side binding; odd (`recto`) chapter openings land on the **left** side of an open spread.
  2. Fenced code blocks, URLs, and mathematical formulas inside Arabic prose are isolated in `dir="ltr"` containers.
  3. Full-wrap covers **invert horizontally**: **Front Cover sits LEFT of the spine** and **Back Cover (with barcode keepout) sits RIGHT of the spine**.
  4. `EPUB 3` `content.opf` sets `<spine toc="ncx" page-progression-direction="rtl">`.
