---
name: book-typesetter
description: "Typeset Arabic (RTL) and English (LTR) books across 3 engines (Typst, HTML/CSS Paged Media, LaTeX/Quarto), 6 bilingual style packs, and 4 editions (Paperback, Hardcover, Large-Print 16pt, Screen PDF) with 100% Content-Integrity Fingerprint verification."
---

# `book-typesetter` — Tri-Engine Bilingual Book Typesetter (`AR RTL` & `EN LTR`)

Compile a single `manuscript/` tree + `book.config.json` into press-accurate **Paperback**, **Hardcover**, **Large-Print (`16pt`)**, and **Screen** interiors using **Typst** (primary sub-second PDF engine), **HTML/CSS Paged Media**, and **LaTeX/Quarto**, while mathematically verifying that zero words, numbers, or table cells were lost.

## 1. Tri-Engine Architecture

| Engine | Flag | Output Artifacts | Best For |
| :--- | :--- | :--- | :--- |
| **Typst (Primary)** | `--engine typst` | `dist/interior-{paperback,hardcover,large-print,screen}.pdf` + `.typ` source | Sub-second compilation, native HarfBuzz Arabic `RTL`, math, multi-page tables |
| **HTML/CSS Paged Media** | `--engine html` | `dist/html-paged/book-paged.html` + `paged-print.css` (+ PDF if Chromium installed) | Magazine-like visual spreads, custom CSS grids, Paged.js workflows |
| **LaTeX / Quarto** | `--engine quarto` | `dist/quarto-latex/_quarto.yml` + `preamble.tex` + `.qmd` chapters (+ PDF if Quarto/LuaLaTeX installed) | University press monographs, heavy BibTeX/theorem environments |

See [`references/tri-engine-typography.md`](references/tri-engine-typography.md) for mirrored gutters, Arabic BiDi isolation, multi-page table safety, and screen-vs-print separation.

## 2. Six Bilingual Style Packs (`assets/themes/style_packs.json`)

- `trade-nonfiction` — Crisp contemporary chapter numbers, balanced margins, clean callout sidebars.
- `literary-novel` — Classic book rhythm, warm paragraph indents, ornamental scene breaks (`⁂`), minimal running headers.
- `technical-code` — Isolated `LTR` syntax blocks inside `RTL` or `LTR` prose, repeating multi-page table headers, figure frames.
- `academic-monograph` — Numbered section hierarchy (`1.1`), dense footnotes, formal running headers, equation support.
- `executive-report` — High-contrast tables, KPI callouts, generous outer margins.
- `classic-arabic-turath` — Traditional Arabic book craft (`الكتاب العربي التراثي والأدبي`), generous `leading` for full/partial vocalization (`التشكيل`), ornamental chapter frames.

## 3. Deterministic CLI Usage

```bash
# Compile all configured print + screen editions across all 3 engines + verify Content Fingerprint
python3 skills/book-typesetter/scripts/build_interior.py \
  --project ./my-book \
  --engine all \
  --edition all

# Fast Typst-only Paperback + Screen build during iterative layout tuning
python3 skills/book-typesetter/scripts/build_interior.py \
  --project ./my-book \
  --engine typst \
  --edition paperback screen
```

## 4. Built-In Print Safeguards

1. **Print vs Screen Separation:** Print editions (`paperback`, `hardcover`, `large-print`) strip all screen paper tints (pure white background so B&W KDP presses never halftone!) and strip interactive PDF `/Link` annotations via `pikepdf`.
2. **Multi-Page Table Safety:** Every pipe table compiles inside `block(breakable: true)` with a repeating `table.header(...)` so 150-row tables never stack on a single `y`-coordinate.
3. **Sticky Headings:** Every heading sets `sticky: true` to prevent orphan headings at page bottoms (`G08`).
4. **Even-Page Lock & Manifest:** Pads flyleaves to guarantee an even page count (`>= min_pages`) and writes `dist/interior-manifest.json` with the **actual PDF page count** required by `book-cover-wrap`.
