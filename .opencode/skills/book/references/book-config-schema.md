# `book.config.json` — Single-Source Publishing Contract

Every skill in `book-studio-skills` reads from one `book.config.json` at the book project root so zero titles, author names, ISBNs, trims, or directional flags are ever hardcoded inside Typst, CSS, LaTeX, or EPUB templates.

## Full Schema Example

```json
{
  "slug": "agentic-systems-ar",
  "language": "ar",
  "direction": "rtl",
  "title": "هندسة الأنظمة الوكيلية في الإنتاج",
  "subtitle": "دليل عملي لبناء ونشر البرمجيات الذكية الموثوقة",
  "author": "عبد الله جمال",
  "publisher": "دار النشر التقني",
  "publication_year": 2026,
  "copyright_holder": "عبد الله جمال",
  "isbn": {
    "paperback": "978-977-00000-0-1",
    "hardcover": "978-977-00000-1-8",
    "ebook": "978-977-00000-2-5"
  },
  "style_pack": "technical-code",
  "engines": ["typst", "html", "quarto"],
  "print": {
    "trim": "6x9",
    "paper_stock": "white",
    "ink": "bw",
    "bleed_in": 0.125,
    "min_pages": 24,
    "editions": ["paperback", "hardcover", "large-print"]
  },
  "digital": {
    "epub3": true,
    "web_book": true
  },
  "humanizer": {
    "enabled": true,
    "voice": "clear-thinker"
  }
}
```

## Supported Trade & Academic Trim Sizes

| Trim Key | Inches (`W × H`) | Millimeters (`W × H`) | Primary Use Case |
| :--- | :--- | :--- | :--- |
| `5x8` | `5.0 × 8.0 in` | `127.0 × 203.2 mm` | Compact literary fiction, novellas, essays |
| `5.25x8` | `5.25 × 8.0 in` | `133.35 × 203.2 mm` | Trade fiction & narrative memoirs |
| `5.5x8.5` | `5.5 × 8.5 in` | `139.7 × 215.9 mm` | Standard trade non-fiction & business books |
| `6x9` | `6.0 × 9.0 in` | `152.4 × 228.6 mm` | Industry standard technical, academic & Arabic trade books |
| `7x10` | `7.0 × 10.0 in` | `177.8 × 254.0 mm` | Textbooks, programming manuals & dense workbooks |
| `8.5x11` | `8.5 × 11.0 in` | `215.9 × 279.4 mm` | Executive reports, illustrated guides & courseware |
| `a5` | `5.827 × 8.268 in` | `148.0 × 210.0 mm` | International & Arab-world (`14×21 cm` / `A5`) standard |
| `b5` | `6.929 × 9.843 in` | `176.0 × 250.0 mm` | Classical Arabic heritage (`تراث`) & scholarly editions |

## Paper Stock Spine Calipers (KDP / IngramSpark)

| `paper_stock` | Per-Page Thickness (`in`) | Per-Page Thickness (`mm`) | Notes |
| :--- | :--- | :--- | :--- |
| `white` | `0.002252 in` | `0.05720 mm` | Default for technical, academic & B&W non-fiction |
| `cream` | `0.002500 in` | `0.06350 mm` | Preferred for novels, literary prose & Arabic heritage |
| `color-standard` | `0.002252 in` | `0.05720 mm` | Standard color print-on-demand |
| `color-premium` | `0.002347 in` | `0.05961 mm` | Heavyweight coated color interior |

## Six Built-In Bilingual Style Packs (`style_pack`)

1. `trade-nonfiction` — Clean contemporary chapter headers, subtle callout boxes, balanced margins.
2. `literary-novel` — Warm classic serif/Naskh rhythm, first-paragraph drop caps (EN) / ornamental opener (AR), centered scene-break glyphs.
3. `technical-code` — Crisp modern headings, bordered syntax/code blocks (`LTR`-isolated), wide tables with repeating headers, diagram captions.
4. `academic-monograph` — Numbered sections (`1.1`, `1.2`), dense footnote apparatus, equation numbering, formal running headers.
5. `executive-report` — Asymmetric modern hierarchy, KPI stat callout cards, generous whitespace, high-contrast tables.
6. `classic-arabic-turath` — Traditional Arabic book craft (`الكتاب التراثي والأدبي`), generous vocalization (`تشكيل`) line-height, ornamental `⁂` dividers, poetic/quoted block indents.
