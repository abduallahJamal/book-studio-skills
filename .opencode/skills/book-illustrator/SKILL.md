---
name: book-illustrator
description: "Prepare, generate, and audit print-grade SVG vector diagrams and 300-DPI raster book illustrations with SVG foreignObject hygiene, Pillow chroma-key background stripping, No-Text art rules, and SHA-256 snapshot manifests."
---

# `book-illustrator` — Print-Safe Vector Diagrams, Chapter Openers & Asset Hygiene

Bad book graphics break print builds silently: Mermaid `<foreignObject>` labels disappear inside Typst/LaTeX PDFs, 72-DPI web screenshots print blurry on paper, and AI-generated raster art mangles Arabic or English lettering.

## 1. Two-Tier Visual Routing Policy

1. **Tier A — Technical Diagrams, Pipelines & Data Charts (Pure Vector `SVG`):**
   - Author diagrams as pure `<svg>` with explicit `viewBox`, `<rect>`, `<path>`, and native `<text>` elements — **never `<foreignObject>` HTML wrappers** and never remote `http://` linked stylesheets or fonts.
   - Match stroke colors and accents to `editorial/art-bible.md` (high-contrast grayscale-safe for `ink: "bw"` interiors!).
2. **Tier B — Chapter Openers & Spot Illustrations (`PNG` >= 300 DPI):**
   - **Strict No-Text Rule:** Raster art prompts must specify *"pure visual illustration, zero letters, zero words, zero numbers, zero watermarks"*. Titles and captions belong in Typst/CSS typography, never baked into pixels.
   - **Chroma-Key Transparency:** Strip solid white/green studio backgrounds (`--chroma-key`) so line-art vignettes sit cleanly on both screen cream and print white pages.
   - **Snapshot-Diff Guard:** Record every figure's SHA-256 digest in `assets/figures/figures-manifest.json` so failed image generations never silently reuse a previous chapter's PNG.

See [`references/visual-routing-rules.md`](references/visual-routing-rules.md) for DPI math, B&W halftone safety, and SVG rules.

## 2. Deterministic CLI Usage

```bash
# Audit all SVGs & PNGs in assets/figures/ (bans <foreignObject>, checks >= 300 DPI at trim width, writes manifest)
python3 skills/book-illustrator/scripts/prepare_figures.py --project ./my-book

# Render a print-safe pure-SVG pipeline diagram from a declarative JSON spec (zero <foreignObject>)
python3 skills/book-illustrator/scripts/prepare_figures.py \
  --project ./my-book \
  --render-pipeline-svg ./assets/figures/pipeline.spec.json \
  --out ./assets/figures/fig-01-pipeline.svg

# Strip solid white/near-white background from a chapter-opener PNG using Pillow chroma-key
python3 skills/book-illustrator/scripts/prepare_figures.py \
  --project ./my-book \
  --chroma-key ./assets/figures/opener-raw.png \
  --out ./assets/figures/opener-clean.png
```
