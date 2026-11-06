# Changelog

All notable changes to `book-studio-skills` will be documented in this file.

## [1.0.0] - 2026-11-06

### Added
- **9-Skill Modular Publishing Architecture** (`book`, `book-intake`, `book-architect`, `book-drafter`, `book-illustrator`, `book-typesetter`, `book-cover-wrap`, `book-ebook-web`, `book-preflight-qc`) + `/book` OpenCode slash command.
- **Tri-Engine Typesetting Support:** Primary `Typst` engine (Paperback, Hardcover, Large-Print `16pt`, Screen PDF), `HTML/CSS Paged Media` visual print track, and `LaTeX/Quarto` academic export bundle across 6 bilingual style packs.
- **Native Arabic (`RTL`) & English (`LTR`) Print Engineering:** Automatic RTL wraparound cover mirroring (Front Cover LEFT of spine, Back Cover + Barcode RIGHT of spine), mirrored inside gutters, isolated LTR code/math blocks inside RTL prose, and `page-progression-direction="rtl"` EPUB 3 spines.
- **BiDi-Aware Content Integrity Fingerprint Guard** ensuring zero dropped words, numbers, or table cells during layout compilation.
- **15 Physical Preflight QC Gates (`preflight_qc.py` + `press_pdfx.py`)** powered by `PyMuPDF`, `pikepdf`, and `Pillow` (Trim/Bleed geometry, Type3 font ban, annotation stripping prior to Ghostscript `CMYK PDF/X-1a`, overflow & y-collision detection, TOC folio sync, 300 DPI check, `<79pp` spine-text guard, and contact-sheet PNG rendering).
- **Direct Bridge with `humanizer-skills`** inside `book-drafter` for prose anti-slop cleanup before typesetting.
- **4-Harness Parity & Installers:** Synchronized trees and cross-platform installers (`install.sh`, `install.py`, `install.ps1`) for OpenCode, Claude Code, Codex CLI, and DeepSeek Harness (`dsh`), plus full end-to-end Arabic & English sample books tested in GitHub Actions.
