# Manuscript Intake & Normalization Rules

## 1. Heading Hierarchy Repair

Authors frequently style headings manually in Word using bold `16pt` text or jump from `Heading 1` straight to `Heading 4`.
- Map chapter titles strictly to `# Chapter Title` (`H1`, one per chapter file).
- Normalize internal hierarchy sequentially (`##` -> `###` -> `####`) with no skipped heading levels (required for valid EPUB 3 `<nav epub:type="toc">` accessibility).

## 2. Word `.docx` Footnotes, Alt-Text & Tables

- Extract `word/footnotes.xml` footnote IDs (`w:id >= 1`, skipping separator IDs `0` and `-1`) and emit inline `[^n]` markers at exact run positions with `[^n]: ...` definitions at chapter end.
- Lift `wp:docPr[@descr]` alt-text attributes as figure captions (`![Caption](../../assets/figures/fig-01.png)`).
- Convert every `w:tbl` into a clean Markdown pipe table so `book-typesetter` renders native repeating `table.header` multi-page tables.

## 3. Legacy PDF & Arabic Unicode Normalization

- Normalize Latin typographic ligatures (`ﬁ` `U+FB01`, `ﬂ` `U+FB02`, `ﬀ` `U+FB00`, `ﬃ` `U+FB03`, `ﬄ` `U+FB04`) via `unicodedata.normalize("NFKC", text)`.
- Normalize Arabic Presentation Forms-A/B (`U+FB50–U+FDFF`, `U+FE70–U+FEFF`, such as isolated/final `ﻻ`/`ﻷ` glyph codepoints) into standard logical Arabic sequence (`ل` + `ا` / `أ`) so HarfBuzz inside Typst and EPUB readers shapes glyphs cleanly in any font.
- Strip stray `U+00AD` soft hyphens and zero-width space artifacts left behind by PDF copy/paste.

## 4. Content-Integrity Fingerprint (`manuscript.lock.json`)

Inspired by `paper_format_agent` and `cdeistopened/book-studio`:
- Computes a BiDi-resilient **Base Letter & Digit Skeleton** (stripping Markdown syntax, Tatweel `ـ`, and optional vocalization while preserving every base Arabic/Latin letter and every Western `0-9` / Eastern Arabic `٠-٩` digit).
- Records per-chapter word counts, total numeric tokens, and character-frequency digest so downstream PDF verification (`G14`) detects even a 0.1% text truncation or missing table row without false positives from Arabic Lam-Alef shaping or line-wrap hyphenation.
