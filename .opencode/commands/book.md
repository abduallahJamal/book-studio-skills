---
description: "Orchestrate end-to-end Arabic (RTL) or English (LTR) book creation, manuscript intake, Tri-Engine typesetting (Typst, HTML/CSS, LaTeX/Quarto), KDP/IngramSpark cover wrap, EPUB 3 + Web Book, and 15-gate press preflight QC."
---

Load and follow the `book` orchestrator skill immediately to route the user's request across the exact specialist publishing bench while enforcing strict physical dependency order (`trim -> interior PDF -> actual page count -> spine & cover wrap -> 15-gate preflight QC`):

1. **Environment check or new project (`book`):** Run `doctor.py` to check tools/fonts/deps and `init_book.py` to initialize `book.config.json` and workspace folders.
2. **Existing `.docx` / `.pdf` / `.md` manuscript (`book-intake`):** Normalize chapters, footnotes, and figures into `manuscript/` and lock content integrity via `import_manuscript.py`.
3. **New book from topic or idea (`book-architect` -> `book-drafter`):** Build `outline.json`, `book-bible.md`, `art-bible.md`, lock voice on a sample, draft chapters with a `claims-ledger.json`, clean AI slop via `humanizer-skills`, and audit with `manuscript_metrics.py`.
4. **Diagrams & chapter art (`book-illustrator`):** Validate/render vector SVGs, enforce 300 DPI + No-Text raster openers, and run `prepare_figures.py`.
5. **Print & screen interiors (`book-typesetter`):** Compile `Paperback`, `Hardcover`, `Large-Print 16pt`, or `Screen` editions via **Typst**, **HTML/CSS Paged Media**, or **LaTeX/Quarto** across 6 AR/EN style packs using `build_interior.py` with 100% Content Fingerprint verification.
6. **Full-wrap print cover & store thumbnail (`book-cover-wrap`):** Read actual compiled PDF page count, compute KDP/IngramSpark caliper spine, automatically mirror **RTL** (Front LEFT / Back RIGHT) vs **LTR** (Back LEFT / Front RIGHT), and render via `calc_and_render_cover.py`.
7. **Digital editions (`book-ebook-web`):** Generate valid `EPUB 3` (`MathML` + RTL/LTR spine progression) and a zero-dependency searchable Static Web Book via `build_epub_and_web.py`.
8. **Press preflight & `CMYK PDF/X-1a` (`book-preflight-qc`):** Strip annotations with `pikepdf` (`press_pdfx.py`), run all 15 physical PyMuPDF geometry/font/TOC/DPI gates (`preflight_qc.py`), and generate visual contact sheets before promoting to `dist/press-ready/`.

User request:
$ARGUMENTS
