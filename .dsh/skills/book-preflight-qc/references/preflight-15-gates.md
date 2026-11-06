# Remediation Guide for the 15 Physical Preflight Gates

- **`G01` (Trim/Bleed Mismatch):** Re-run `build_interior.py` and `calc_and_render_cover.py` so both read the identical `print.trim` and `print.bleed_in` from `book.config.json`.
- **`G02` (Odd or Short Page Count):** Print books bind 2 pages per leaf (`recto` + `verso`). `build_interior.py` pads flyleaves automatically to an even count `>= min_pages`.
- **`G03` (Unembedded or `Type3` Font):** Occurs when a missing glyph falls back to a bitmap font or Matplotlib/LaTeX emits `Type3` paths. Install proper OpenType/TrueType fonts (`fonts-amiri`, `fonts-noto-core`) and check with `doctor.py`.
- **`G04` (Interactive `/Annots` Present):** Run `press_pdfx.py` before Ghostscript/upload to strip `/Link` annotations.
- **`G05` (Missing `/TrimBox` or `/OutputIntents`):** Run `press_pdfx.py` to normalize boxes and attach `GTS_PDFX` OutputIntent dictionary.
- **`G06` (Safe-Margin Overflow):** A long unbreakable URL, wide code line, or fixed-width table spilled into the trim margin. Wrap long code lines (`<= 78` chars) or allow table column wrapping (`1fr`).
- **`G07` (Vertical Line `y`-Collision):** Caused by unbreakable multi-page containers or negative `v()` spacing. Wrap tables in `block(breakable: true)`.
- **`G08` (Orphan Heading at Page Bottom):** Ensure headings carry `sticky: true` in Typst or `break-after: avoid` in CSS.
- **`G09` (TOC Folio Desync):** Recompile from scratch rather than concatenating external cover/frontmatter PDFs ahead of the interior PDF.
- **`G10` (`< 300` Effective DPI):** Replace low-res raster PNG/JPG with pure SVG vector art or upscale/re-export at `>= 1500 px` width.
- **`G11` (Screen Tint on B&W Interior):** Never pass `--edition screen` to a print upload; use `interior-paperback.pdf` (pure white canvas).
- **`G12` (Ungrounded Callout Number):** Every KPI/percentage highlighted in a `>` callout box must appear in the chapter body or `editorial/claims-ledger.json`.
- **`G13` (Cover Spine `<79pp` Text or Barcode Overlap):** Re-run `calc_and_render_cover.py` after final interior compilation; shorten back-cover blurb if it approaches the `2.0" × 1.2"` barcode keepout box.
- **`G14` (Content-Integrity Fingerprint Mismatch):** Refresh `manuscript.lock.json` (`import_manuscript.py --lock-only`) if you intentionally edited the manuscript, or inspect truncated syntax if words/numbers were dropped during compilation.
- **`G15` (Visual Contact Sheet):** Inspect `dist/qc/contact-sheet-interior.png` and `dist/qc/contact-sheet-cover.png` visually as the final human/vision-model sign-off.
