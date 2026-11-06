# Print-Grade Visual Routing, SVG Hygiene & 300-DPI Math

## 1. Why Browser SVGs Fail in Print Engines

Default Mermaid CLI (`flowchart`) emits `<foreignObject><div>...</div></foreignObject>` HTML inside `<svg>`. Typst, Inkscape PDF/X export, and EPUB 3 Spine renderers either drop `<foreignObject>` text completely or clip Arabic BiDi shaping.
- **Fix:** Always emit pure SVG primitives (`<rect>`, `<line>`, `<polygon>`, `<text>`) or set `htmlLabels: false` before exporting Mermaid, then verify with `prepare_figures.py`.

## 2. Effective Print DPI Formula

For a book trim of `6 × 9 in` with `0.75 in` margins, the maximum content column width is `4.5 in`.
- Full-width figure (`4.5 in` wide) at `300 DPI` requires at least **`1350 px`** horizontal resolution (`4.5 × 300 = 1350`).
- Half-width vignette (`2.2 in` wide) at `300 DPI` requires at least **`660 px`** horizontal resolution.

## 3. Black-and-White (`ink: "bw"`) Halftone Safety

Most trade paperbacks print interiors in 1-color black ink:
- Never rely on red-vs-green color differentiation alone; pair fills with distinct lightness levels (`#1E293B` vs `#E2E8F0`), dashed strokes, or geometric markers.
- Keep fills inside B&W diagrams either pure white (`#FFFFFF`), light tint (`#F1F5F9`), or dark charcoal (`#0F172A` with white text) for crisp laser/inkjet reproduction.
