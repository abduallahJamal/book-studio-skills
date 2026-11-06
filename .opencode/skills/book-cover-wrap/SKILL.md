---
name: book-cover-wrap
description: "Calculate exact KDP and IngramSpark spine width from the compiled interior PDF page count and render press-ready Arabic (RTL-mirrored) and English (LTR) wraparound print covers plus 1600x2560 eBook store covers."
---

# `book-cover-wrap` — KDP/IngramSpark Caliper Spine & `RTL`/`LTR` Wraparound Cover Engine

Never build a print book cover from an estimated page count or apply an English (`LTR`) template to an Arabic (`RTL`) book.

## 1. Non-Negotiable Print Cover Laws

1. **Read Actual Page Count (`N`) From Final Interior PDF:**
   - `calc_and_render_cover.py` inspects `dist/interior-paperback.pdf` directly via `pikepdf`.
2. **Exact Paper Caliper Spine Formula:**
   - White (`white`): `N × 0.002252 in` (`0.0572 mm`)
   - Cream (`cream`): `N × 0.002500 in` (`0.0635 mm`)
   - Premium Color (`color-premium`): `N × 0.002347 in` (`0.0596 mm`)
   - Full width = `0.125" bleed + trim_w + spine_w + trim_w + 0.125" bleed`; Full height = `0.125" + trim_h + 0.125"`.
3. **KDP `<79` Pages Spine-Text Ban:**
   - If `N < 79`, KDP rejects ANY text or logo on the spine due to `±0.0625"` fold variance. Our engine suppresses spine text automatically whenever `N < 79`.
4. **Automatic `RTL` vs `LTR` Full-Wrap Mirroring:**
   - **English (`LTR`):** `[Bleed] [Back Cover + Barcode] [Spine] [Front Cover] [Bleed]`
   - **Arabic (`RTL`):** `[Bleed] [Front Cover] [Spine] [Back Cover + Barcode] [Bleed]` — mirrored automatically when `direction == "rtl"` so right-bound Arabic books open from the front!

See [`references/cover-geometry-specs.md`](references/cover-geometry-specs.md) for mechanical diagrams, hardcover wrap allowances, and barcode keepout coordinates.

## 2. Deterministic CLI Usage

```bash
# Read dist/interior-paperback.pdf, compute spine & mirror layout, and render proof SVG + print PDF + eBook PNG
python3 skills/book-cover-wrap/scripts/calc_and_render_cover.py \
  --project ./my-book \
  --blurb "وصف الغلاف الخلفي للكتاب..."

# Pre-interior mechanical calculator only (explicit --pages override for early planning; never use for final press!)
python3 skills/book-cover-wrap/scripts/calc_and_render_cover.py \
  --project ./my-book \
  --pages 240 \
  --spec-only
```

## 3. Generated Deliverables

- `dist/cover-spec.json` — Exact dimensions (`in`, `mm`, `pt`), `front_panel`, `spine_panel`, `back_panel`, and `barcode_keepout` coordinates.
- `dist/cover-wrap-proof.svg` — Visual proof with trim, bleed, spine fold dashed guides, and barcode box.
- `dist/cover-wrap-print.pdf` — Clean press-ready full-wrap PDF (guide lines stripped, zero annotations, exact `MediaBox`).
- `dist/cover-ebook.png` — `1600 × 2560 px` digital store thumbnail for Kindle, Apple Books, Kobo & Abjjad.
