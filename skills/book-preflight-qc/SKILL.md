---
name: book-preflight-qc
description: "Distill press-ready CMYK/PDF-X files (stripping PDF annotations via pikepdf before Ghostscript) and enforce 15 physical PyMuPDF/Pillow preflight QC gates plus visual contact sheets before promoting deliverables to dist/press-ready/."
---

# `book-preflight-qc` — Safe `PDF/X-1a` Press Prep & 15 Physical Geometry Gates

Never trust a PDF just because the compiler exited with code `0`. No file enters `dist/press-ready/` until it passes `press_pdfx.py` and all **15 physical gates** in `preflight_qc.py`.

## 1. The Ghostscript `PDF/X-1a` Annotation Trap (`press_pdfx.py`)

If a PDF contains even one `/Link` annotation from a Table of Contents or cross-reference, Ghostscript (`gs -dPDFX`) prints a quiet warning (`reverting to normal PDF output`) and drops `PDF/X-1a` compliance while still exiting `0`!
- **`press_pdfx.py` Sequence:**
  1. Open PDF with `pikepdf` and delete all `/Annots` across every page **before** Ghostscript runs.
  2. Normalize `MediaBox`, `BleedBox`, and `TrimBox` to `0.01pt` accuracy and attach `GTS_PDFX` `/OutputIntents` metadata.
  3. When Ghostscript (`gs`) is installed and `--cmyk` is passed, convert color space to `DeviceCMYK` and re-apply `TrimBox` via `pikepdf`.

## 2. The 15 Physical Preflight Gates (`preflight_qc.py`)

| Gate | Physical Check | Engine |
| :--- | :--- | :--- |
| `G01` | Exact `MediaBox` / `TrimBox` dimensions (`±0.5pt`) on interior & cover | `pikepdf` |
| `G02` | Even page count & `>= min_pages` (`24pp` KDP floor) | `pikepdf` |
| `G03` | 100% embedded font subsets & **zero `Type3` fallback bitmap fonts** | `PyMuPDF` |
| `G04` | **Zero interactive `/Annots`** on print interior & wrap cover | `pikepdf` |
| `G05` | `/TrimBox` + `/OutputIntents` (`GTS_PDFX`) press dictionary present | `pikepdf` |
| `G06` | Safe-margin overflow scan across all text & table bounding boxes | `PyMuPDF` |
| `G07` | Vertical line `y`-collision detector (catches stacked table rows) | `PyMuPDF` |
| `G08` | Bottom-of-page orphan heading detector | `PyMuPDF` |
| `G09` | Printed Table of Contents folio sync vs actual chapter pages | `PyMuPDF` |
| `G10` | Embedded raster image effective resolution `>= 300 DPI` | `PyMuPDF` |
| `G11` | B&W interior screen-tint guard (blocks full-page `#FAF8F5` gray halftone) | `PyMuPDF` |
| `G12` | Callout / stat box numeric grounding against chapter prose & ledger | Python |
| `G13` | Cover RTL/LTR side check, `<79pp` empty-spine verification & barcode keepout | `PyMuPDF` |
| `G14` | BiDi-aware Content-Integrity Fingerprint parity vs `manuscript.lock.json` | `PyMuPDF` |
| `G15` | High-resolution `contact-sheet-interior.png` & `contact-sheet-cover.png` | `Pillow` |

See [`references/preflight-15-gates.md`](references/preflight-15-gates.md) for failure diagnostics and exact fixes for each gate.

## 3. Deterministic CLI Usage

```bash
# 1. Strip annotations, normalize TrimBox/BleedBox, tag GTS_PDFX OutputIntent (+ optional Ghostscript CMYK)
python3 skills/book-preflight-qc/scripts/press_pdfx.py --project ./my-book --cmyk

# 2. Run all 15 physical gates, render PNG contact sheets & promote verified files to dist/press-ready/
python3 skills/book-preflight-qc/scripts/preflight_qc.py --project ./my-book
```
