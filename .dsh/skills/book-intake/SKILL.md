---
name: book-intake
description: "Import and normalize Word (.docx), legacy PDF, or scattered Markdown/text manuscripts into a clean multi-chapter Book Studio workspace with footnotes, tables, extracted figures, and a Content-Integrity Fingerprint Lock."
---

# `book-intake` — Manuscript Intake, Normalization & Content Lock

Turn messy real-world manuscripts (`.docx`, `.pdf`, or scattered `.md`/`.txt` drafts) into a clean, single-source `manuscript/` tree **without altering a single word of the author's prose**.

## 1. Core Responsibilities

1. **Structural Splitting:** Split monolithic manuscripts on top-level chapter headings (`Heading 1` / `# `) into `manuscript/chapters/ch-01.md`, `ch-02.md`, etc., routing frontmatter (`Preface`, `Foreword`, `مقدمة`, `إهداء`) to `manuscript/frontmatter/`.
2. **Footnote & Table Preservation:** Extract Word `word/footnotes.xml` entries into standard Markdown `[^1]` footnotes, convert `.docx` tables into pipe tables, and export embedded media (`word/media/*`) into `assets/figures/` with lifted alt-text captions.
3. **Ligature & BiDi Normalization:** Repair broken PDF extraction ligatures (`ﬁ` -> `fi`, `ﬂ` -> `fl`) and normalize Arabic presentation forms (`U+FB50–U+FDFF`, `U+FE70–U+FEFF`) to canonical UTF-8 codepoints (`NFKC`).
4. **Content-Integrity Fingerprint Lock (`manuscript.lock.json`):** Record exact character-skeleton multisets, numeric token inventories (`0-9` and `٠-٩`), table counts, and chapter word counts so `book-typesetter` and `book-preflight-qc` (`G14`) halt immediately if formatting ever drops a paragraph, number, or table cell.

See [`references/intake-normalization-rules.md`](references/intake-normalization-rules.md) for ligature, footnote, and Arabic Unicode normalization rules.

## 2. Deterministic CLI Usage

```bash
# Import a Word (.docx), PDF (.pdf), or single/folder Markdown manuscript into a Book Studio project
python3 skills/book-intake/scripts/import_manuscript.py \
  --source ./raw-draft.docx \
  --project ./my-book

# Lock or refresh manuscript.lock.json on an already-organized manuscript/ folder
python3 skills/book-intake/scripts/import_manuscript.py \
  --project ./my-book \
  --lock-only
```

## 3. Hard Guardrails

- **Zero Silent Editing:** Intake normalizes structure and Unicode encoding only. Never rewrite prose, "fix" style, or summarize during `book-intake` — prose editing belongs strictly to `book-drafter` or `humanizer-skills`.
- **Inspect Image DPI Early:** After extracting embedded `.docx`/`.pdf` images into `assets/figures/`, run `book-illustrator`'s `prepare_figures.py` before print typesetting to flag sub-300 DPI graphics.
