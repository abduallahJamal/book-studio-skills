<div align="center">

<img src="assets/banner.svg" alt="book-studio-skills — Bilingual AR RTL & EN LTR End-to-End Book Authoring, Tri-Engine Typesetting, KDP Cover Wrap, EPUB 3 & 15-Gate Press QC Suite" width="100%"/>

<br/>

**Bilingual (Arabic `RTL` + English `LTR`) end-to-end book creation, Tri-Engine typesetting (`Typst` · `HTML/CSS Paged Media` · `LaTeX/Quarto`), KDP/IngramSpark wraparound cover engineering, `EPUB 3` + Static Web Book, and 15-gate physical preflight QC — 9 [Agent Skills](https://agentskills.io), `/book` router command, and 10 Python publishing CLIs for OpenCode, Claude Code, Codex CLI, and DeepSeek Harness (`dsh`).**

[![CI](https://github.com/abduallahJamal/book-studio-skills/actions/workflows/validate.yml/badge.svg?label=CI)](https://github.com/abduallahJamal/book-studio-skills/actions/workflows/validate.yml)
[![Skills](https://img.shields.io/badge/Skills-9%20%2B%20%2Fbook-38BDF8)](#the-nine-agent-skills)
[![Engines](https://img.shields.io/badge/Engines-Typst%20%C2%B7%20Paged%20CSS%20%C2%B7%20Quarto%2FLaTeX-818CF8)](#tri-engine-typesetting--editions)
[![Languages](https://img.shields.io/badge/Print%20%26%20EPUB-Arabic%20RTL%20%26%20English%20LTR-A78BFA)](#native-arabic-rtl--english-ltr-engineering)
[![QC Gates](https://img.shields.io/badge/Preflight-15%20Physical%20Gates-22C55E)](#the-15-physical-preflight-qc-gates)
[![OpenCode](https://img.shields.io/badge/OpenCode-ready-111827)](#installation)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-ready-D97757)](#installation)
[![Codex CLI](https://img.shields.io/badge/Codex%20CLI-ready-10A37F)](#installation)
[![DeepSeek Harness](https://img.shields.io/badge/DeepSeek%20Harness-ready-2563EB)](#installation)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E.svg)](LICENSE)
[![Arabic Docs](https://img.shields.io/badge/%D8%A7%D9%84%D8%AA%D9%88%D8%AB%D9%8A%D9%82-%D8%A7%D9%84%D8%B9%D8%B1%D8%A8%D9%8A%D8%A9-1E293B)](README.ar.md)

**🇬🇧 English** · **[🇪🇬 العربية](README.ar.md)**

</div>

---

## 📌 Why a 9-Bench Publishing Suite?

Single-script book generators break down in physical production: guessing page counts before typesetting shifts the spine fold onto the front cover; leaving TOC `/Link` annotations inside a PDF causes Ghostscript `-dPDFX` to silently drop `PDF/X-1a` compliance; unbreakable 100-row tables stack rows on top of each other; and applying left-to-right (`LTR`) templates to an Arabic (`RTL`) book prints the front cover on the back!

`book-studio-skills` distills the strongest engineering ideas from **9 open-source book & academic publishing projects** into **9 modular, non-conflicting skills** governed by a strict physical dependency chain (`trim -> interior PDF -> actual page count -> spine & RTL/LTR cover wrap -> 15-gate PyMuPDF/pikepdf QC`), paired with [`abduallahJamal/humanizer-skills`](https://github.com/abduallahJamal/humanizer-skills) for AI-slop cleanup during drafting.

## 🧩 The Nine Agent Skills

| Skill | Studio Bench Role | Bundled Python CLI(s) | Upstream Engineering Distilled |
| :--- | :--- | :--- | :--- |
| **[`book`](skills/book/SKILL.md)** | Master router (`/book`), environment doctor, workspace initializer & dependency-order guard | `doctor.py`, `init_book.py` | `cdeistopened/book-studio` (`book-workshop` dependency chain) |
| **[`book-intake`](skills/book-intake/SKILL.md)** | Word (`.docx`), legacy `.pdf` & Markdown normalization, footnote/table extraction & Content Lock | `import_manuscript.py` | `yoelf22/book-typesetting-skill` (`import-docx.py`), `markitright`, `paper_format_agent` |
| **[`book-architect`](skills/book-architect/SKILL.md)** | Topic-to-outline contract (`outline.json`), Book Bible, Art Bible & Voice Lock sample gate | `scaffold_outline.py` | `epicsagas/Velith` (Phases 0–2), `chesley-veko/book_skill` (`toc.json`) |
| **[`book-drafter`](skills/book-drafter/SKILL.md)** | Full-context chapter drafting, Claim Ledger fact tracking, 7-stage editing + `humanizer-skills` bridge | `manuscript_metrics.py` | `epicsagas/Velith` (Phases 3–4, Cold Beta-Reader) + `humanizer-skills` |
| **[`book-illustrator`](skills/book-illustrator/SKILL.md)** | Pure-vector `SVG` pipeline renderer (no `<foreignObject>`), 300-DPI audit & Pillow chroma-key | `prepare_figures.py` | `chesley-veko/book_skill` (`chroma_key.py`, snapshot-diff), `bookforge` (`G0`) |
| **[`book-typesetter`](skills/book-typesetter/SKILL.md)** | **Tri-Engine** (`Typst` + `Paged CSS` + `Quarto/LaTeX`), 6 themes, 4 editions + Content Fingerprint | `build_interior.py` | `felipefontoura/book-kit`, `rxpelle/book-formatter`, `gongnyang/bookforge` |
| **[`book-cover-wrap`](skills/book-cover-wrap/SKILL.md)** | Exact KDP/IngramSpark paper caliper spine math, automatic **RTL/LTR mirroring** & `1600×2560` eBook cover | `calc_and_render_cover.py` | `cdeistopened/book-studio` (`kdp-cover-wrap`), `yoelf22`, `book-kit` |
| **[`book-ebook-web`](skills/book-ebook-web/SKILL.md)** | Validated `EPUB 3.3` (`MathML`, uncompressed `mimetype`, RTL spine) + offline searchable Static Web Book | `build_epub_and_web.py` | `rxpelle/book-formatter`, `felipefontoura/book-kit` |
| **[`book-preflight-qc`](skills/book-preflight-qc/SKILL.md)** | `pikepdf` annotation strip + `CMYK PDF/X-1a` prep + **15 physical PyMuPDF gates** & PNG contact sheets | `press_pdfx.py`, `preflight_qc.py` | `gongnyang/bookforge` (`qc_gate.py`, `contact_sheet.py`), `yoelf22` (`verify-pdfx.py`) |

---

## 🌍 Native Arabic (`RTL`) & English (`LTR`) Engineering

Unlike Latin-only formatters, every template and geometry formula natively adapts to `"direction": "rtl"` and `"direction": "ltr"`:

1. **Automatic Wraparound Cover Panel Mirroring (`book-cover-wrap`):**
   - **English (`LTR`):** `[Bleed] ← [Back Cover + Barcode] ← [Spine] ← [Front Cover] ← [Bleed]`
   - **Arabic (`RTL`):** `[Bleed] ← [Front Cover] ← [Spine] ← [Back Cover + Barcode] ← [Bleed]` — right-bound Arabic print books place the Front Cover on the **left** of the flat press sheet and the Back Cover on the **right**!
2. **Mirrored Binding Gutters & Recto Openings (`book-typesetter`):**
   - Inside binding margins (`0.85"` paperback / `0.95"` hardcover) mirror automatically across odd/even spreads; fenced code blocks, CLI commands, and equations inside Arabic chapters are isolated in `LTR` containers.
3. **Right-to-Left E-Reader Page Progression (`book-ebook-web`):**
   - Sets `<spine page-progression-direction="rtl">` in `OEBPS/content.opf` and `dir="rtl" xml:lang="ar"` across all XHTML chapters for Kindle, Apple Books, Kobo, and Abjjad.

---

## ⚙️ Tri-Engine Typesetting & Editions

From one `book.config.json` and `manuscript/` folder, `build_interior.py` emits:

- **3 Engines:** **Typst** (sub-second primary PDF compiler), **HTML/CSS Paged Media** (`book-paged.html` + `@page :left/:right` stylesheet), and **LaTeX/Quarto** (`_quarto.yml` + `LuaLaTeX` `babel` Arabic/English preamble).
- **4 Simultaneous Targets:** `paperback`, `hardcover`, `large-print` (`16pt` accessible edition), and interactive `screen` PDF (retaining warm paper tint and clickable links while print targets strip tints and `/Annots`).
- **6 Built-In Bilingual Style Packs:** `trade-nonfiction`, `literary-novel`, `technical-code`, `academic-monograph`, `executive-report`, and `classic-arabic-turath` (`الكتاب التراثي والأدبي`).

---

## 🛡️ The 15 Physical Preflight QC Gates

No deliverable reaches `dist/press-ready/` until `preflight_qc.py` passes all 15 deterministic checks:

| Gate | Inspection | Engine |
| :--- | :--- | :--- |
| `G01` | Exact `MediaBox` / `TrimBox` dimensions (`±0.5pt`) on interior & cover | `pikepdf` |
| `G02` | Even page count & `>= min_pages` (`24pp` KDP floor) | `pikepdf` |
| `G03` | 100% embedded font subsets & **zero `Type3` bitmap fallback fonts** | `PyMuPDF` |
| `G04` | **Zero interactive `/Annots`** prior to & after press distillation | `pikepdf` |
| `G05` | `/TrimBox` + `GTS_PDFX` `/OutputIntents` press profile dictionary | `pikepdf` |
| `G06` | Safe-margin horizontal/vertical overflow scan across all text blocks | `PyMuPDF` |
| `G07` | Vertical line `y`-collision detector (catches stacked multi-page table rows) | `PyMuPDF` |
| `G08` | Bottom-of-page orphan heading guard (`sticky: true` verification) | `PyMuPDF` |
| `G09` | Printed Table of Contents folio sync against actual PDF pages | `PyMuPDF` |
| `G10` | Embedded raster image effective print resolution `>= 300 DPI` | `PyMuPDF` |
| `G11` | B&W print screen-tint guard (prevents full-page gray halftone mud) | `PyMuPDF` |
| `G12` | Callout / KPI stat numeric grounding against chapter prose | Python |
| `G13` | Cover RTL/LTR panel mirror, `<79pp` empty-spine rule & barcode keepout check | `PyMuPDF` |
| `G14` | BiDi Content-Integrity Fingerprint parity vs `manuscript.lock.json` (zero lost words/digits) | `PyMuPDF` |
| `G15` | High-res visual inspection sheets (`contact-sheet-interior.png` & `contact-sheet-cover.png`) | `Pillow` |

---

## 🚀 Installation

Requires `Python 3.9+`, [`typst`](https://github.com/typst/typst/releases) CLI, and the Python publishing packages in `requirements.txt` (`pymupdf`, `pikepdf`, `Pillow`, `python-docx`):

```bash
git clone https://github.com/abduallahJamal/book-studio-skills.git
cd book-studio-skills

# Install Python pro publishing libraries + install all 9 skills globally across all 4 harnesses
./install.sh --all --global --install-deps

# Verify Python libraries, Typst, Ghostscript & Arabic/English fonts
python3 skills/book/scripts/doctor.py

# Or install into a single project workspace
./install.sh --all --project /path/to/your-book
```

**Windows PowerShell:**

```powershell
pip install -r requirements.txt
.\install.ps1 --target all --scope global
```

---

## 🛠️ Multi-Harness Compatibility Matrix

| Agent Harness | Project Path | Global Path | Invocation | Platform Specifics Included |
| :--- | :--- | :--- | :--- | :--- |
| **OpenCode** | `.opencode/skills/` | `~/.config/opencode/skills/` | `/book` or auto-trigger | Quoted YAML frontmatter + `.opencode/commands/book.md` |
| **Claude Code** | `.claude/skills/` | `~/.claude/skills/` | `/book`, `/book-typesetter`, … | `.claude-plugin/plugin.json` & `marketplace.json` |
| **OpenAI Codex CLI** | `.agents/skills/` & `.codex/skills/` | `~/.agents/skills/` & `~/.codex/skills/` | `$book`, `$book-cover-wrap`, … | `agents/openai.yaml` sidecar per skill + `.agents/plugins/marketplace.json` |
| **DeepSeek Harness (`dsh`)** | `.dsh/skills/` (rank 100) | `~/.dsh/skills/` (`$DSH_HOME/skills`) | `skill({ name })` / Palette | Strict **depth-1 flat layout** for `@deepseek-ai/dsh-skill-filesystem` |

---

## 🧪 End-to-End Quickstart (Try on Bundled AR & EN Demo Books)

Two complete starter books ship in [`examples/arabic-rtl-book`](examples/arabic-rtl-book/book.config.json) and [`examples/english-ltr-book`](examples/english-ltr-book/book.config.json):

```bash
# 1. Render pure-SVG vector diagrams & lock manuscript content fingerprint
python3 skills/book-illustrator/scripts/prepare_figures.py \
  --project examples/arabic-rtl-book \
  --render-pipeline-svg examples/arabic-rtl-book/assets/figures/pipeline.spec.json \
  --out examples/arabic-rtl-book/assets/figures/fig-01-pipeline.svg
python3 skills/book-intake/scripts/import_manuscript.py --project examples/arabic-rtl-book --lock-only

# 2. Audit prose burstiness, cross-chapter repetition & Arabic/English AI slop
python3 skills/book-drafter/scripts/manuscript_metrics.py --project examples/arabic-rtl-book --strict

# 3. Compile Paperback, Hardcover, Large-Print (16pt), Screen, Paged HTML & Quarto/LaTeX
python3 skills/book-typesetter/scripts/build_interior.py --project examples/arabic-rtl-book --engine all --edition all

# 4. Compute exact spine width from compiled PDF & render RTL-mirrored wrap cover + eBook PNG
python3 skills/book-cover-wrap/scripts/calc_and_render_cover.py --project examples/arabic-rtl-book

# 5. Build validated EPUB 3.3 (RTL spine + MathML) & searchable Static Web Book
python3 skills/book-ebook-web/scripts/build_epub_and_web.py --project examples/arabic-rtl-book

# 6. Strip annotations, tag GTS_PDFX & run all 15 physical QC gates -> dist/press-ready/
python3 skills/book-preflight-qc/scripts/press_pdfx.py --project examples/arabic-rtl-book --cmyk
python3 skills/book-preflight-qc/scripts/preflight_qc.py --project examples/arabic-rtl-book
```

---

## 📂 Repository Structure

```text
book-studio-skills/
├── assets/banner.svg                    # Suite header graphic
├── requirements.txt                     # pymupdf, pikepdf, Pillow, python-docx
├── skills/                              # Canonical depth-1 flat skills source
│   ├── book/                            # 0. /book router + doctor.py + init_book.py
│   ├── book-intake/                     # 1. .docx/.pdf/.md importer + manuscript.lock.json
│   ├── book-architect/                  # 2. outline.json + Voice Lock + Book/Art Bibles
│   ├── book-drafter/                    # 3. Continuity drafting + Claim Ledger + Humanizer bridge
│   ├── book-illustrator/                # 4. Pure-SVG diagrams + 300-DPI & chroma-key
│   ├── book-typesetter/                 # 5. Tri-Engine (Typst/CSS/Quarto) + 6 themes + Content Guard
│   ├── book-cover-wrap/                 # 6. KDP spine math + RTL/LTR wrap cover + eBook PNG
│   ├── book-ebook-web/                  # 7. EPUB 3.3 (RTL + MathML) + Static HTML Web Book
│   └── book-preflight-qc/               # 8. pikepdf PDF/X-1a + 15 PyMuPDF gates + Contact Sheets
├── examples/
│   ├── arabic-rtl-book/                 # Full Arabic RTL technical book demo
│   └── english-ltr-book/                # Full English LTR trade non-fiction book demo
├── .opencode/ .claude/ .agents/ .dsh/   # SHA-256 synchronized multi-harness skill trees
├── scripts/
│   ├── sync-platforms.sh                # Mirror & verify SHA-256 digests across all 4 harnesses
│   └── validate.py                      # Schema, link & live AR/EN end-to-end build + 15-gate CI suite
└── install.sh / install.py / install.ps1
```

---

## 🙏 Acknowledgments & Upstream Inspiration

Synthesized and extended with native Arabic `RTL` print/cover/EPUB engineering from:
- [`yoelf22/book-typesetting-skill`](https://github.com/yoelf22/book-typesetting-skill) · [`chesley-veko/book_skill`](https://github.com/chesley-veko/book_skill) · [`cdeistopened/book-studio`](https://github.com/cdeistopened/book-studio) · [`rxpelle/book-formatter`](https://github.com/rxpelle/book-formatter) · [`felipefontoura/book-kit`](https://github.com/felipefontoura/book-kit) · [`epicsagas/Velith`](https://github.com/epicsagas/Velith) · [`gongnyang/bookforge`](https://github.com/gongnyang/bookforge) · [`zxyasfas/paper_format_agent`](https://github.com/zxyasfas/paper_format_agent) · [`abduallahJamal/humanizer-skills`](https://github.com/abduallahJamal/humanizer-skills).

## 📄 License

Released under the [MIT License](LICENSE).
