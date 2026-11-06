---
name: book-ebook-web
description: "Build and validate standards-compliant EPUB 3.3 eBooks (with Arabic RTL page-progression-direction, MathML equations, cover image, and accessible nav.xhtml) plus a zero-dependency searchable Static HTML Web Book."
---

# `book-ebook-web` — Standards-Compliant `EPUB 3` (`RTL`/`LTR` + `MathML`) & Static Web Book

Generate digital editions from the exact same `manuscript/` tree and `book.config.json` without duplicating prose.

## 1. Native Arabic `RTL` & `MathML` EPUB 3.3 Engineering

1. **Uncompressed `mimetype` First Entry:** Writes `application/epub+zip` with `ZIP_STORED` at byte offset 0 so Apple Books, Kindle Previewer, Kobo, and `epubcheck` recognize the container immediately.
2. **Arabic Right-to-Left Spine Progression:** Sets `page-progression-direction="rtl"` on `<spine>` inside `OEBPS/content.opf` and `dir="rtl" xml:lang="ar"` on every `.xhtml` document so e-readers flip pages naturally from right to left.
3. **BiDi Code & MathML Isolation:** Wraps `<pre dir="ltr">` code blocks and converts `$...$` / `$$...$$` formulas into native `MathML` (`properties="mathml"` declared in `<manifest>`).
4. **Strict XML Gate:** Every `.xhtml`, `nav.xhtml`, and `.opf` file is parsed via `ElementTree` XML validation before packaging, followed by a post-pack structural archive audit.

## 2. Multi-Page Static HTML Web Book (`dist/web-book/`)

Builds a self-contained static web edition (zero external CDNs, works offline or on GitHub Pages / Cloudflare Pages):
- Multi-page chapter navigation (`prev` / `next` + collapsible TOC sidebar)
- Instant client-side full-text search (`search-index.json`) supporting Arabic and English queries
- Reader appearance switcher (`Light`, `Sepia`, `Dark`)

See [`references/epub3-and-web-specs.md`](references/epub3-and-web-specs.md) for OPF metadata, Kindle/Abjjad BiDi CSS, and validation checks.

## 3. Deterministic CLI Usage

```bash
# Build both EPUB 3 (dist/<slug>.epub) and Static Web Book (dist/web-book/) + run structural validator
python3 skills/book-ebook-web/scripts/build_epub_and_web.py --project ./my-book

# Validate an existing .epub file for OPF/XHTML XML well-formedness, mimetype store rule & RTL spine
python3 skills/book-ebook-web/scripts/build_epub_and_web.py --project ./my-book --validate-only
```
