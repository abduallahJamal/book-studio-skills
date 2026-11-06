# Tri-Engine Typography, Arabic RTL Print Rules & Anti-Collision Engineering

## 1. Inside Gutter & Recto/Verso Mirroring (`RTL` vs `LTR`)

- **Binding Margin (`inside`) > Outer Margin (`outside`):** Glued perfect-bound spines consume `0.125"–0.20"` of visual gutter. Never set symmetrical left/right margins on a printed book!
  - `Paperback`: `inside = 0.85 in`, `outside = 0.65 in`
  - `Hardcover` (case-laminate hinge): `inside = 0.95 in`, `outside = 0.70 in`
  - `Large-Print (16pt)`: `16pt` body text, `inside = 0.85 in`, `outside = 0.65 in`, wider `leading` for low-vision accessibility.
- **Arabic (`RTL`) Spread Physics:**
  - Odd pages (`1, 3, 5` — chapter `recto` openings) lie on the **left** side of an open Arabic book; their `inside` binding gutter is on the **right** edge of the page.
  - Even pages (`2, 4, 6` — `verso`) lie on the **right** side of an open Arabic book; their `inside` binding gutter is on the **left** edge.
  - Typst's `#set page(margin: (inside: ..., outside: ...))` paired with `#set text(dir: rtl)` handles this mirroring natively.

## 2. BiDi Code, Math & Identifier Isolation Inside Arabic Prose

When an Arabic paragraph embeds Python code, CLI flags (`--strict`), or equations, naive RTL layout reverses brackets, operators, and indentation:
- Every fenced code block renders inside `#block(dir: ltr)[#set text(dir: ltr, lang: "en", font: mono_font) ...]` (Typst), `<pre dir="ltr">` (HTML/EPUB), and `\begin{english}...\end{english}` (LuaLaTeX).
- Inline code spans (` `code` `) wrap in `LTR` directional isolates.

## 3. Preventing the 4 Classic Automated Typesetting Failures

1. **150-Row Table Vertical Collision (`gongnyang/bookforge`):** Unbreakable table containers overflow a page and collapse rows on top of one another. Always wrap tables in `breakable: true` with `table.header(...)`.
2. **B&W Halftone Mud (`felipefontoura/book-kit`):** Never leave a `#FAF8F5` cream fill on a `--print` PDF; KDP's black-only laser press converts `#FAF8F5` into a speckled gray dot screen over every page. Print cream comes from choosing `"paper_stock": "cream"`, not tinting the PDF!
3. **Orphan Headings (`G08`):** Apply `sticky: true` (Typst) / `break-after: avoid` (CSS) / `\needspace{4\baselineskip}` (LaTeX) to all headings.
4. **Silent Word Loss (`paper_format_agent`):** Always compare post-compile PDF extracted text & numeric inventory against `manuscript.lock.json`.
