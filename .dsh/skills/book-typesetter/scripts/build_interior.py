#!/usr/bin/env python3
"""
build_interior.py — Tri-Engine Bilingual (AR RTL / EN LTR) Book Interior Compiler

Supports:
- Engines  : typst (primary fast PDF compiler), html (CSS Paged Media), quarto (LaTeX/Quarto academic)
- Editions : paperback, hardcover, large-print (16pt), screen
- Features :
  * Dynamic font resolution against installed fonts (zero missing-font warnings)
  * Arabic RTL mirrored gutters, recto chapter openings, isolated LTR code & math blocks
  * Multi-page tables (`breakable: true` + repeating `table.header`) preventing y-collision
  * Sticky headings preventing bottom-of-page heading widows (G08)
  * Print mode strips screen background tints & strips PDF `/Annots` via pikepdf + sets exact TrimBox
  * Pads print page count to exact even page >= min_pages
  * Verifies BiDi-aware Content-Integrity Fingerprint against manuscript/
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

import pikepdf

try:
    import pymupdf
except ImportError:  # pragma: no cover
    import fitz as pymupdf  # type: ignore

SCRIPT_DIR = Path(__file__).resolve().parent
STYLE_PACKS_PATH = SCRIPT_DIR.parent / "assets" / "themes" / "style_packs.json"

TRIMS_IN: dict[str, tuple[float, float]] = {
    "5x8": (5.0, 8.0),
    "5.25x8": (5.25, 8.0),
    "5.5x8.5": (5.5, 8.5),
    "6x9": (6.0, 9.0),
    "7x10": (7.0, 10.0),
    "8.5x11": (8.5, 11.0),
    "a5": (5.8268, 8.2677),
    "b5": (6.9291, 9.8425),
}

NUMBER_RE = re.compile(r"[\d\u0660-\u0669]+(?:[.,][\d\u0660-\u0669]+)*")
AR_DIACRITICS_RE = re.compile(r"[\u0640\u064B-\u065F\u0670\u06D6-\u06ED]")


def get_installed_fonts() -> dict[str, str]:
    fonts: dict[str, str] = {}
    if shutil.which("typst"):
        proc = subprocess.run(["typst", "fonts"], capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                name = line.strip()
                if name:
                    fonts[name.lower()] = name
    return fonts


def choose_font(candidates: list[str], installed: dict[str, str], fallback: str = "DejaVu Sans") -> str:
    for c in candidates:
        if c.lower() in installed:
            return installed[c.lower()]
    if fallback.lower() in installed:
        return installed[fallback.lower()]
    return next(iter(installed.values()), fallback)


def typst_escape(text: str) -> str:
    """Escape plain prose characters that have special meaning in Typst markup."""
    out = (
        text.replace("\\", "\\\\")
        .replace("#", "\\#")
        .replace("@", "\\@")
        .replace("<", "\\<")
        .replace(">", "\\>")
        .replace("$", "\\$")
        .replace("_", "\\_")
        .replace("*", "\\*")
        .replace("`", "\\`")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )
    return out


def convert_inline_md_to_typst(line: str, footnotes: dict[str, str], mono_font: str) -> str:
    """Convert inline Markdown (**bold**, *italic*, `code`, $math$, [text](url), [^fn]) safely to Typst."""
    tokens: list[str] = []

    def stash(typ_code: str) -> str:
        idx = len(tokens)
        tokens.append(typ_code)
        return f"%%TYPTOK{idx}%%"

    # 1. Inline code `...` (isolate LTR so code inside Arabic never flips!)
    line = re.sub(
        r"`([^`]+)`",
        lambda m: stash(
            f'#box(inset: (x: 3pt, y: 0pt), outset: (y: 2pt), radius: 2pt, fill: rgb("#F1F5F9"))['
            f'#text(dir: ltr, lang: "en", font: "{mono_font}", size: 0.88em)[{typst_escape(m.group(1))}]]'
        ),
        line,
    )

    # 2. Inline math $...$
    def render_inline_math(m: re.Match) -> str:
        expr = m.group(1).strip()
        # Keep simple mathematical notation safe in Typst math or clean LTR italic math box
        return stash(f'#box[#text(dir: ltr, lang: "en", style: "italic")[{typst_escape(expr)}]]')

    line = re.sub(r"\$([^$\n]+)\$", render_inline_math, line)

    # 3. Footnotes [^id]
    def render_fn(m: re.Match) -> str:
        fid = m.group(1)
        body = footnotes.get(fid, "")
        if body:
            return stash(f"#footnote[{typst_escape(body)}]")
        return ""

    line = re.sub(r"\[\^([^\]]+)\]", render_fn, line)

    # 4. Links [label](url)
    line = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: stash(f'#link("{m.group(2).strip()}")[{typst_escape(m.group(1))}]'),
        line,
    )

    # 5. Bold **...** and Italic *...*
    line = re.sub(r"\*\*([^*]+)\*\*", lambda m: stash(f"#strong[{typst_escape(m.group(1))}]"), line)
    line = re.sub(r"\*([^*]+)\*", lambda m: stash(f"#emph[{typst_escape(m.group(1))}]"), line)

    # Escape remaining plain text
    escaped = typst_escape(line)

    # Restore stashed Typst fragments in reverse order so nested tokens (**bold `code`**) resolve cleanly
    for idx in range(len(tokens) - 1, -1, -1):
        escaped = escaped.replace(f"%%TYPTOK{idx}%%", tokens[idx])
    return escaped


def parse_markdown_chapter_to_typst(
    md_text: str,
    md_file: Path,
    typ_out_dir: Path,
    mono_font: str,
    scene_ornament: str,
    is_ar: bool = False,
    is_front_or_back: bool = False,
) -> str:
    """Convert a full Markdown chapter/section into clean, collision-proof Typst markup."""
    raw_lines = md_text.splitlines()
    footnotes: dict[str, str] = {}
    body_lines: list[str] = []

    for ln in raw_lines:
        fn_match = re.match(r"^\[\^([^\]]+)\]:\s*(.+)$", ln.strip())
        if fn_match:
            footnotes[fn_match.group(1)] = fn_match.group(2).strip()
        else:
            body_lines.append(ln)

    out: list[str] = []
    i = 0
    n = len(body_lines)

    while i < n:
        line = body_lines[i]
        stripped = line.strip()

        if not stripped:
            out.append("")
            i += 1
            continue

        # HTML comments
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            i += 1
            continue

        # Fenced code blocks ```lang ... ```
        if stripped.startswith("```"):
            i += 1
            code_buf: list[str] = []
            while i < n and not body_lines[i].strip().startswith("```"):
                code_buf.append(body_lines[i])
                i += 1
            i += 1  # skip closing ```
            escaped_code = "\n".join(code_buf).replace("\\", "\\\\").replace('"', '\\"')
            out.append(
                f'#block(width: 100%, breakable: true, fill: rgb("#F8FAFC"), stroke: 0.6pt + rgb("#CBD5E1"), '
                f'inset: 9pt, radius: 4pt, above: 0.9em, below: 0.9em)[\n'
                f'  #set align(left)\n'
                f'  #set text(dir: ltr, lang: "en", font: "{mono_font}", size: 8.5pt)\n'
                f'  #raw(block: true, "{escaped_code}")\n'
                f']'
            )
            continue

        # Display math $$ ... $$
        if stripped.startswith("$$"):
            if stripped.endswith("$$") and len(stripped) > 4:
                expr = stripped[2:-2].strip()
                i += 1
            else:
                i += 1
                mbuf = []
                while i < n and not body_lines[i].strip().startswith("$$"):
                    mbuf.append(body_lines[i])
                    i += 1
                i += 1
                expr = " ".join(mbuf).strip()
            out.append(
                f'#align(center)[#block(inset: 8pt, above: 0.8em, below: 0.8em)['
                f'#text(dir: ltr, lang: "en", style: "italic", size: 1.05em)[{typst_escape(expr)}]]]'
            )
            continue

        # Scene break
        if stripped in {"* * *", "***", "---", "___"}:
            out.append(f'#align(center)[#v(0.8em)#text(size: 1.1em)[{typst_escape(scene_ornament)}]#v(0.8em)]')
            i += 1
            continue

        # Image ![caption](path)
        img_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", stripped)
        if img_match:
            cap, rel_img = img_match.group(1).strip(), img_match.group(2).strip()
            resolved_img = (md_file.parent / rel_img).resolve()
            if resolved_img.is_file():
                rel_from_typ = Path(shutil.os.path.relpath(resolved_img, typ_out_dir)).as_posix()
                if cap:
                    out.append(
                        f'#figure(\n'
                        f'  image("{rel_from_typ}", width: 88%),\n'
                        f'  caption: [{convert_inline_md_to_typst(cap, footnotes, mono_font)}]\n'
                        f')'
                    )
                else:
                    out.append(f'#align(center)[#image("{rel_from_typ}", width: 88%)]')
            i += 1
            continue

        # Pipe tables | a | b |
        if stripped.startswith("|") and stripped.endswith("|") and i + 1 < n and re.match(r"^\|\s*[-:]+", body_lines[i + 1].strip()):
            header_cells = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2  # skip header + separator
            data_rows: list[list[str]] = []
            while i < n and body_lines[i].strip().startswith("|") and body_lines[i].strip().endswith("|"):
                row_cells = [c.strip() for c in body_lines[i].strip().strip("|").split("|")]
                data_rows.append(row_cells)
                i += 1

            col_count = max(len(header_cells), *(len(r) for r in data_rows)) if data_rows else len(header_cells)
            header_cells += [""] * (col_count - len(header_cells))
            cols_spec = ", ".join(["1fr"] * col_count)
            hdr_typ = ", ".join(f"[*#{ '{{' }* {convert_inline_md_to_typst(c, footnotes, mono_font)}]" for c in header_cells)
            # Clean bold header cells
            hdr_typ = ", ".join(
                f"[#strong[{convert_inline_md_to_typst(c, footnotes, mono_font)}]]" for c in header_cells
            )
            body_typ_items: list[str] = []
            for r in data_rows:
                padded = r + [""] * (col_count - len(r))
                for c in padded:
                    body_typ_items.append(f"[{convert_inline_md_to_typst(c, footnotes, mono_font)}]")

            out.append(
                f'#block(breakable: true, width: 100%, above: 0.9em, below: 0.9em)[\n'
                f'  #set text(size: 0.90em)\n'
                f'  #table(\n'
                f'    columns: ({cols_spec}),\n'
                f'    stroke: 0.5pt + rgb("#94A3B8"),\n'
                f'    inset: 6pt,\n'
                f'    fill: (_, y) => if y == 0 {{ rgb("#F1F5F9") }} else {{ none }},\n'
                f'    table.header({hdr_typ}),\n'
                f'    {", ".join(body_typ_items)}\n'
                f'  )\n'
                f']'
            )
            continue

        # Blockquote / Callout > ...
        if stripped.startswith(">"):
            q_lines = []
            while i < n and body_lines[i].strip().startswith(">"):
                q_lines.append(re.sub(r"^>\s?", "", body_lines[i].strip()))
                i += 1
            q_typ = " ".join(convert_inline_md_to_typst(ql, footnotes, mono_font) for ql in q_lines if ql)
            border_side = "right" if is_ar else "left"
            out.append(
                f'#block(width: 100%, breakable: true, fill: rgb("#F8FAFC"), '
                f'stroke: ({border_side}: 2.5pt + rgb("#334155")), inset: (x: 10pt, y: 8pt), above: 0.9em, below: 0.9em)[\n'
                f'  {q_typ}\n'
                f']'
            )
            continue

        # Headings #, ##, ###
        h_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if h_match:
            level = len(h_match.group(1))
            htext = convert_inline_md_to_typst(h_match.group(2).strip(), footnotes, mono_font)
            if level == 1:
                if is_front_or_back:
                    out.append(f'#heading(level: 1, numbering: none)[{htext}]')
                else:
                    out.append(f"= {htext}")
            else:
                eqs = "=" * level
                out.append(f"{eqs} {htext}")
            i += 1
            continue

        # Unordered list - / *
        if re.match(r"^[-*]\s+", stripped):
            item_txt = re.sub(r"^[-*]\s+", "", stripped)
            out.append(f"- {convert_inline_md_to_typst(item_txt, footnotes, mono_font)}")
            i += 1
            continue

        # Ordered list 1.
        if re.match(r"^\d+\.\s+", stripped):
            item_txt = re.sub(r"^\d+\.\s+", "", stripped)
            out.append(f"+ {convert_inline_md_to_typst(item_txt, footnotes, mono_font)}")
            i += 1
            continue

        # Regular paragraph (join consecutive wrapped prose lines)
        p_lines = [stripped]
        i += 1
        while i < n:
            nxt = body_lines[i].strip()
            if (
                not nxt
                or nxt.startswith(("#", "```", "$$", "|", ">", "![", "<!--"))
                or nxt in {"* * *", "***", "---", "___"}
                or re.match(r"^([-*]|\d+\.)\s+", nxt)
            ):
                break
            p_lines.append(nxt)
            i += 1
        joined_para = " ".join(p_lines)
        out.append(convert_inline_md_to_typst(joined_para, footnotes, mono_font))
        out.append("")

    return "\n".join(out)


def build_typst_document(
    cfg: dict,
    style: dict,
    edition: str,
    installed_fonts: dict[str, str],
    front_files: list[Path],
    chapter_files: list[Path],
    back_files: list[Path],
    typ_out_dir: Path,
) -> tuple[str, dict]:
    is_ar = cfg.get("language", "ar") == "ar"
    direction = "rtl" if is_ar else "ltr"
    trim_key = cfg.get("print", {}).get("trim", "6x9").lower()
    w_in, h_in = TRIMS_IN.get(trim_key, (6.0, 9.0))
    if edition == "large-print" and w_in < 6.0:
        w_in, h_in = (6.0, 9.0)

    is_screen = edition == "screen"
    body_pt = 16.0 if edition == "large-print" else float(style["body_pt"])
    inside_in = 0.95 if edition == "hardcover" else 0.85
    outside_in = 0.70 if edition == "hardcover" else 0.65
    top_in = 0.78
    bottom_in = 0.85

    body_font = choose_font(
        style["ar_body_fonts"] if is_ar else style["en_body_fonts"],
        installed_fonts,
        "DejaVu Sans" if is_ar else "Libertinus Serif",
    )
    heading_font = choose_font(
        style["ar_heading_fonts"] if is_ar else style["en_heading_fonts"],
        installed_fonts,
        body_font,
    )
    mono_font = choose_font(style["mono_fonts"], installed_fonts, "DejaVu Sans Mono")

    leading_em = style["ar_leading_em"] if is_ar else style["leading_em"]
    indent_em = style["first_line_indent_em"]
    par_space_em = style["par_spacing_em"]
    numbered = bool(style["numbered_sections"])
    accent = style["screen_accent"] if is_screen else "#0F172A"
    page_fill = 'fill: rgb("#FAF8F5"),' if is_screen else ""

    title = typst_escape(cfg.get("title", "Untitled Book"))
    subtitle = typst_escape(cfg.get("subtitle", ""))
    author = typst_escape(cfg.get("author", ""))
    publisher = typst_escape(cfg.get("publisher", ""))
    year = cfg.get("publication_year", 2026)
    isbn_map = cfg.get("isbn", {})
    isbn_str = typst_escape(isbn_map.get(edition if edition in isbn_map else "paperback", ""))
    toc_title = "فهرس المحتويات" if is_ar else "Table of Contents"
    rights_text = (
        f"جميع الحقوق محفوظة © {year} {author}\nالناشر: {publisher}"
        if is_ar
        else f"Copyright © {year} {author}. All rights reserved.\nPublished by {publisher}."
    )
    edition_badge = {
        "paperback": "الطبعة الورقية" if is_ar else "Paperback Edition",
        "hardcover": "طبعة الغلاف المقوى" if is_ar else "Hardcover Edition",
        "large-print": "طبعة الخط الكبير (16pt)" if is_ar else "Large Print Edition (16pt)",
        "screen": "النسخة الرقمية التفاعلية" if is_ar else "Interactive Screen Edition",
    }[edition]

    numbering_rule = '"1.1"' if numbered else "none"
    link_rule = (
        f'#show link: set text(fill: rgb("{accent}"))'
        if is_screen
        else "#show link: it => it.body"
    )

    parts: list[str] = [
        f'// Generated by book-studio-skills (edition: {edition}, dir: {direction})',
        f'#set document(title: "{title}", author: "{author}")',
        f'#set page(',
        f'  width: {w_in}in,',
        f'  height: {h_in}in,',
        f'  {page_fill}',
        f'  margin: (inside: {inside_in}in, outside: {outside_in}in, top: {top_in}in, bottom: {bottom_in}in),',
        f'  header: context {{',
        f'    let p = here().page()',
        f'    if p > 4 {{',
        f'      set text(size: 8.5pt, fill: rgb("#475569"))',
        f'      if calc.rem(p, 2) == 0 [{title}] else [#align(left)[{author}]]' if is_ar else
        f'      if calc.rem(p, 2) == 0 [{author}] else [#align(right)[{title}]]',
        f'    }}',
        f'  }},',
        f'  footer: context {{',
        f'    let p = here().page()',
        f'    if p > 4 {{',
        f'      align(center)[#text(size: 9pt, fill: rgb("#334155"))[#p]]',
        f'    }}',
        f'  }}',
        f')',
        f'#set text(lang: "{cfg.get("language", "ar")}", dir: {direction}, font: "{body_font}", size: {body_pt}pt, fallback: true)',
        f'#set par(justify: true, leading: {leading_em}em, spacing: {par_space_em}em, first-line-indent: {indent_em}em)',
        f'#set heading(numbering: {numbering_rule})',
        f'#show heading: set block(sticky: true, above: 1.45em, below: 0.75em)',
        f'#show heading: set text(font: "{heading_font}", fill: rgb("{accent}"))',
        f'#show heading.where(level: 1): it => {{',
        f'  v(1.2em)',
        f'  text(size: 1.55em, weight: "bold")[#it]',
        f'  v(0.55em)',
        f'  line(length: 38%, stroke: 1.2pt + rgb("{accent}"))',
        f'  v(0.65em)',
        f'}}',
        link_rule,
        "",
        "// 1. Half-Title Page (p.1 Recto)",
        "#page(header: none, footer: none)[",
        "  #v(28%)",
        f"  #align(center)[#text(font: \"{heading_font}\", size: 1.6em, weight: \"bold\")[{title}]]",
        "]",
        "// 2. Blank Verso (p.2)",
        "#page(header: none, footer: none)[#v(1pt)]",
        "// 3. Full Title Page (p.3 Recto)",
        "#page(header: none, footer: none)[",
        "  #v(20%)",
        f"  #align(center)[#text(font: \"{heading_font}\", size: 2.05em, weight: \"bold\", fill: rgb(\"{accent}\"))[{title}]]",
        f"  #v(0.8em)",
        f"  #align(center)[#text(size: 1.15em, fill: rgb(\"#334155\"))[{subtitle}]]" if subtitle else "",
        "  #v(2.4em)",
        f"  #align(center)[#line(length: 28%, stroke: 1pt + rgb(\"#94A3B8\"))]",
        "  #v(2.0em)",
        f"  #align(center)[#text(size: 1.2em, weight: \"bold\")[{author}]]",
        "  #v(1fr)",
        f"  #align(center)[#text(size: 0.95em, fill: rgb(\"#475569\"))[{publisher} · {year}]]",
        "]",
        "// 4. Copyright / Colophon Page (p.4 Verso)",
        "#page(header: none, footer: none)[",
        "  #v(1fr)",
        "  #set par(first-line-indent: 0em)",
        f"  #text(size: 0.85em, fill: rgb(\"#334155\"))[{typst_escape(rights_text)}]",
        "  #v(0.6em)",
        f"  #text(size: 0.85em, fill: rgb(\"#334155\"))[{typst_escape(edition_badge)}]",
        f"  #v(0.4em)\n  #text(dir: ltr, lang: \"en\", size: 0.85em)[ISBN: {isbn_str}]" if isbn_str else "",
        "]",
        "// 5. Table of Contents",
        "#pagebreak()",
        f'#outline(title: "{toc_title}", depth: 2, indent: 1.2em)',
    ]

    for fm in front_files:
        parts.append('\n#pagebreak(to: "odd")')
        parts.append(
            parse_markdown_chapter_to_typst(
                fm.read_text(encoding="utf-8"), fm, typ_out_dir, mono_font, style["scene_ornament"], is_ar=is_ar, is_front_or_back=True
            )
        )

    for ch in chapter_files:
        parts.append('\n#pagebreak(to: "odd")')
        parts.append(
            parse_markdown_chapter_to_typst(
                ch.read_text(encoding="utf-8"), ch, typ_out_dir, mono_font, style["scene_ornament"], is_ar=is_ar, is_front_or_back=False
            )
        )

    for bm in back_files:
        parts.append('\n#pagebreak(to: "odd")')
        parts.append(
            parse_markdown_chapter_to_typst(
                bm.read_text(encoding="utf-8"), bm, typ_out_dir, mono_font, style["scene_ornament"], is_ar=is_ar, is_front_or_back=True
            )
        )

    meta = {
        "trim": trim_key,
        "width_in": w_in,
        "height_in": h_in,
        "width_pt": round(w_in * 72.0, 2),
        "height_pt": round(h_in * 72.0, 2),
        "body_pt": body_pt,
        "inside_margin_in": inside_in,
        "outside_margin_in": outside_in,
        "top_margin_in": top_in,
        "bottom_margin_in": bottom_in,
        "fonts": {"body": body_font, "heading": heading_font, "mono": mono_font},
    }
    return "\n".join(parts) + "\n", meta


def normalize_print_pdf_boxes_and_even_pages(pdf_path: Path, w_pt: float, h_pt: float, min_pages: int, strip_annots: bool) -> int:
    """Strip annotations on print editions, enforce exact TrimBox/MediaBox, and pad blank flyleaves to even >= min_pages."""
    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        box = pikepdf.Array([0, 0, round(w_pt, 3), round(h_pt, 3)])
        for page in pdf.pages:
            if strip_annots and "/Annots" in page:
                del page["/Annots"]
            page["/MediaBox"] = box
            page["/TrimBox"] = box

        target_pages = max(len(pdf.pages), min_pages)
        if target_pages % 2 == 1:
            target_pages += 1

        while len(pdf.pages) < target_pages:
            blank = pdf.add_blank_page(page_size=(round(w_pt, 3), round(h_pt, 3)))
            blank["/MediaBox"] = box
            blank["/TrimBox"] = box

        final_count = len(pdf.pages)
        pdf.save(pdf_path)
    return final_count


def simple_md_to_html_body(md_text: str) -> str:
    """Lightweight clean Markdown-to-HTML converter for CSS Paged Media track."""
    lines = md_text.splitlines()
    out: list[str] = []
    in_code = False
    for ln in lines:
        s = ln.strip()
        if s.startswith("```"):
            if not in_code:
                out.append('<pre dir="ltr"><code>')
                in_code = True
            else:
                out.append("</code></pre>")
                in_code = False
            continue
        if in_code:
            out.append(html.escape(ln))
            continue
        if re.match(r"^\[\^[^\]]+\]:", s) or (s.startswith("<!--") and s.endswith("-->")):
            continue
        if not s:
            continue
        if s.startswith("### "):
            out.append(f"<h3>{html.escape(s[4:])}</h3>")
        elif s.startswith("## "):
            out.append(f"<h2>{html.escape(s[3:])}</h2>")
        elif s.startswith("# "):
            out.append(f"<h1>{html.escape(s[2:])}</h1>")
        elif s.startswith("> "):
            out.append(f"<blockquote>{html.escape(s[2:])}</blockquote>")
        else:
            esc = html.escape(s)
            esc = re.sub(r"`([^`]+)`", r'<code dir="ltr">\1</code>', esc)
            esc = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", esc)
            esc = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", esc)
            out.append(f"<p>{esc}</p>")
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)


def emit_html_paged_track(cfg: dict, style: dict, all_sections: list[Path], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    is_ar = cfg.get("language", "ar") == "ar"
    direction = "rtl" if is_ar else "ltr"
    trim_key = cfg.get("print", {}).get("trim", "6x9").lower()
    w_in, h_in = TRIMS_IN.get(trim_key, (6.0, 9.0))

    css = f"""/* Generated Paged Media Print Stylesheet ({trim_key}, {direction.upper()}) */
@page {{
  size: {w_in}in {h_in}in;
  margin-top: 0.78in;
  margin-bottom: 0.85in;
}}
@page :left {{
  margin-left: {"0.85in" if is_ar else "0.65in"};
  margin-right: {"0.65in" if is_ar else "0.85in"};
}}
@page :right {{
  margin-left: {"0.65in" if is_ar else "0.85in"};
  margin-right: {"0.85in" if is_ar else "0.65in"};
}}
html, body {{
  direction: {direction};
  font-size: {style["body_pt"]}pt;
  line-height: 1.65;
  color: #0F172A;
  background: #FFFFFF;
}}
section.chapter {{
  break-before: {"left" if is_ar else "right"};
}}
h1, h2, h3 {{
  break-after: avoid;
}}
p {{
  orphans: 2;
  widows: 2;
  text-align: justify;
}}
pre, code {{
  direction: ltr;
  text-align: left;
  font-family: "DejaVu Sans Mono", monospace;
}}
"""
    (out_dir / "paged-print.css").write_text(css, encoding="utf-8")

    chapters_html = []
    for sec in all_sections:
        chapters_html.append(f'<section class="chapter">\n{simple_md_to_html_body(sec.read_text(encoding="utf-8"))}\n</section>')

    doc_html = f"""<!DOCTYPE html>
<html lang="{cfg.get('language', 'ar')}" dir="{direction}">
<head>
  <meta charset="utf-8"/>
  <title>{html.escape(cfg.get('title', ''))}</title>
  <link rel="stylesheet" href="paged-print.css"/>
</head>
<body>
  <section class="title-page">
    <h1>{html.escape(cfg.get('title', ''))}</h1>
    <p class="subtitle">{html.escape(cfg.get('subtitle', ''))}</p>
    <p class="author">{html.escape(cfg.get('author', ''))}</p>
  </section>
  {"".join(chapters_html)}
</body>
</html>
"""
    html_file = out_dir / "book-paged.html"
    html_file.write_text(doc_html, encoding="utf-8")
    return html_file


def emit_quarto_latex_track(cfg: dict, all_sections: list[Path], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    is_ar = cfg.get("language", "ar") == "ar"
    trim_key = cfg.get("print", {}).get("trim", "6x9").lower()
    w_in, h_in = TRIMS_IN.get(trim_key, (6.0, 9.0))

    qmd_names = ["index.qmd"]
    (out_dir / "index.qmd").write_text(
        f"# {'تصدير الكتاب' if is_ar else 'Preface'} {{.unnumbered}}\n\n"
        f"{cfg.get('subtitle', '')}\n",
        encoding="utf-8",
    )
    for idx, sec in enumerate(all_sections, start=1):
        qname = f"sec-{idx:02d}.qmd"
        shutil.copy2(sec, out_dir / qname)
        qmd_names.append(qname)

    preamble = (
        "\\usepackage{booktabs}\n"
        "\\usepackage{needspace}\n"
        + (
            "\\usepackage[bidi=basic,layout=counters.tabular]{babel}\n"
            "\\babelprovide[import,main]{arabic}\n"
            "\\babelprovide[import]{english}\n"
            if is_ar
            else "\\usepackage{microtype}\n"
        )
    )
    (out_dir / "preamble.tex").write_text(preamble, encoding="utf-8")

    chapters_yaml = "\n".join(f"    - {n}" for n in qmd_names)
    quarto_yml = f"""project:
  type: book
  output-dir: _book

book:
  title: "{cfg.get('title', '').replace('"', "'")}"
  author: "{cfg.get('author', '').replace('"', "'")}"
  chapters:
{chapters_yaml}

format:
  pdf:
    documentclass: scrbook
    pdf-engine: lualatex
    geometry:
      - paperwidth={w_in}in
      - paperheight={h_in}in
      - inner=0.85in
      - outer=0.65in
      - top=0.78in
      - bottom=0.85in
    include-in-header: preamble.tex
"""
    yml_path = out_dir / "_quarto.yml"
    yml_path.write_text(quarto_yml, encoding="utf-8")
    return yml_path


def verify_pdf_content_integrity(pdf_path: Path, section_files: list[Path]) -> dict:
    """Verify BiDi-aware numeric token & character inventory retention between Markdown Master and compiled PDF."""
    raw_md = "\n\n".join(p.read_text(encoding="utf-8") for p in section_files)
    # Strip markdown syntax to get pure source alnum characters and numeric tokens
    clean_md = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r" \1 ", raw_md)
    clean_md = re.sub(r"\[([^\]]+)\]\([^)]*\)", r" \1 ", clean_md)
    clean_md = re.sub(r"^```[a-zA-Z0-9_-]*\s*$", "", clean_md, flags=re.MULTILINE)
    clean_md = re.sub(r"\[\^([^\]]+)\]:?", " ", clean_md)
    clean_md = AR_DIACRITICS_RE.sub("", unicodedata.normalize("NFKC", clean_md))

    doc = pymupdf.open(str(pdf_path))
    pdf_text = "\n".join(page.get_text() for page in doc)
    clean_pdf = AR_DIACRITICS_RE.sub("", unicodedata.normalize("NFKC", pdf_text))

    digit_trans = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    md_nums = [t.translate(digit_trans).replace(",", "") for t in NUMBER_RE.findall(clean_md)]
    pdf_nums_str = clean_pdf.translate(digit_trans).replace(",", "")

    missing_nums = [num for num in md_nums if num not in pdf_nums_str]

    md_letters = sum(1 for c in clean_md if unicodedata.category(c)[0] in ("L", "N"))
    pdf_letters = sum(1 for c in clean_pdf if unicodedata.category(c)[0] in ("L", "N"))
    # PDF has extra running headers/TOC/title page text so pdf_letters >= md_letters * 0.96
    retention_ratio = round(pdf_letters / max(md_letters, 1), 4)
    verified = len(missing_nums) == 0 and retention_ratio >= 0.96

    return {
        "verified": verified,
        "source_alnum_chars": md_letters,
        "pdf_alnum_chars": pdf_letters,
        "alnum_retention_ratio": retention_ratio,
        "source_numeric_tokens": len(md_nums),
        "missing_numeric_tokens": missing_nums[:10],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile book interiors across Typst, HTML/CSS, and LaTeX/Quarto.")
    parser.add_argument("--project", required=True, help="Path to Book Studio project root.")
    parser.add_argument(
        "--engine",
        nargs="+",
        choices=["all", "typst", "html", "quarto"],
        default=["all"],
        help="Typesetting engine(s) to run.",
    )
    parser.add_argument(
        "--edition",
        nargs="+",
        choices=["all", "paperback", "hardcover", "large-print", "screen"],
        default=["all"],
        help="Book edition(s) to compile.",
    )
    args = parser.parse_args()

    root = Path(args.project).resolve()
    cfg = json.loads((root / "book.config.json").read_text(encoding="utf-8"))
    styles = json.loads(STYLE_PACKS_PATH.read_text(encoding="utf-8"))
    style_key = cfg.get("style_pack", "trade-nonfiction")
    if style_key not in styles:
        raise SystemExit(f"Unknown style_pack '{style_key}'. Choices: {sorted(styles)}")
    style = styles[style_key]

    front_files = sorted((root / "manuscript" / "frontmatter").glob("*.md"))
    chapter_files = sorted((root / "manuscript" / "chapters").glob("*.md"))
    back_files = sorted((root / "manuscript" / "backmatter").glob("*.md"))
    if not chapter_files:
        raise SystemExit("Error: zero chapter .md files in manuscript/chapters/")

    all_sections = front_files + chapter_files + back_files
    engines = {"typst", "html", "quarto"} if "all" in args.engine else set(args.engine)
    if "all" in args.edition:
        editions = list(cfg.get("print", {}).get("editions", ["paperback"])) + ["screen"]
    else:
        editions = list(dict.fromkeys(args.edition))

    dist = root / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    min_pages = int(cfg.get("print", {}).get("min_pages", 24))

    manifest: dict = {
        "title": cfg.get("title"),
        "language": cfg.get("language"),
        "direction": cfg.get("direction"),
        "style_pack": style_key,
        "editions": {},
        "tracks": {},
    }

    if "typst" in engines:
        if not shutil.which("typst"):
            raise SystemExit("Error: 'typst' binary not found on PATH (run skills/book/scripts/doctor.py)")
        installed_fonts = get_installed_fonts()
        typ_dir = dist / "typst"
        typ_dir.mkdir(parents=True, exist_ok=True)

        for ed in editions:
            typ_src, meta = build_typst_document(
                cfg, style, ed, installed_fonts, front_files, chapter_files, back_files, typ_dir
            )
            typ_file = typ_dir / f"interior-{ed}.typ"
            pdf_file = dist / f"interior-{ed}.pdf"
            typ_file.write_text(typ_src, encoding="utf-8")

            proc = subprocess.run(
                ["typst", "compile", "--root", str(root), str(typ_file), str(pdf_file)],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                print(proc.stderr, file=sys.stderr)
                raise SystemExit(f"Typst compilation failed for edition '{ed}'")

            is_print_ed = ed != "screen"
            final_pages = normalize_print_pdf_boxes_and_even_pages(
                pdf_file,
                meta["width_pt"],
                meta["height_pt"],
                min_pages=min_pages if is_print_ed else 2,
                strip_annots=is_print_ed,
            )
            integrity = verify_pdf_content_integrity(pdf_file, all_sections)
            if not integrity["verified"]:
                raise SystemExit(f"[CONTENT GUARD FAIL] Edition '{ed}' failed content fingerprint check: {integrity}")

            meta["page_count"] = final_pages
            meta["pdf_path"] = str(pdf_file.relative_to(root))
            meta["content_integrity"] = integrity
            manifest["editions"][ed] = meta
            print(f"[OK] Typst {ed:11s} -> {pdf_file.relative_to(root)} ({final_pages} pages, content lock VERIFIED)")

    if "html" in engines:
        html_out = emit_html_paged_track(cfg, style, all_sections, dist / "html-paged")
        manifest["tracks"]["html_paged"] = str(html_out.relative_to(root))
        print(f"[OK] HTML/CSS Paged Media bundle -> {html_out.relative_to(root)}")

    if "quarto" in engines:
        q_out = emit_quarto_latex_track(cfg, all_sections, dist / "quarto-latex")
        manifest["tracks"]["quarto_latex"] = str(q_out.relative_to(root))
        print(f"[OK] Quarto/LaTeX bundle -> {q_out.relative_to(root)}")

    primary_ed = "paperback" if "paperback" in manifest["editions"] else next(iter(manifest["editions"]), None)
    if primary_ed:
        manifest["primary_print_edition"] = primary_ed
        manifest["actual_print_page_count"] = manifest["editions"][primary_ed]["page_count"]

    manifest_path = dist / "interior-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
