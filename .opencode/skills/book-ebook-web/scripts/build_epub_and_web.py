#!/usr/bin/env python3
"""
build_epub_and_web.py — Validated EPUB 3.3 (RTL/LTR + MathML) & Static Web Book Builder

Outputs:
- dist/<slug>.epub (EPUB 3.3 compliant, XML-verified, uncompressed mimetype, RTL/LTR spine)
- dist/web-book/   (Multi-page offline-capable HTML reader with instant search & Light/Sepia/Dark modes)
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import uuid
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def latex_expr_to_mathml(expr: str, display: bool = False) -> str:
    """Convert lightweight inline/display math expressions into valid XHTML MathML."""
    mode = ' display="block"' if display else ""
    tokens = re.findall(r"[A-Za-z]+|\d+(?:\.\d+)?|[+\-*/=<>≤≥≈×÷()]+|\S", expr.strip())
    inner: list[str] = []
    for tok in tokens:
        esc = html.escape(tok)
        if tok.replace(".", "", 1).isdigit():
            inner.append(f"<mn>{esc}</mn>")
        elif tok.isalpha():
            inner.append(f"<mi>{esc}</mi>")
        else:
            inner.append(f"<mo>{esc}</mo>")
    return f'<math xmlns="http://www.w3.org/1998/Math/MathML" dir="ltr"{mode}><mrow>{"".join(inner)}</mrow></math>'


def convert_inline_xhtml(text: str, footnotes: dict[str, str], used_fns: list[tuple[str, str]]) -> tuple[str, bool]:
    has_math = False
    stashed: list[str] = []

    def put(fragment: str) -> str:
        idx = len(stashed)
        stashed.append(fragment)
        return f"%%XHTMLTOK{idx}%%"

    # Inline code
    text = re.sub(
        r"`([^`]+)`",
        lambda m: put(f'<code dir="ltr" class="inline-code">{html.escape(m.group(1))}</code>'),
        text,
    )

    # Inline math $...$
    def sub_math(m: re.Match) -> str:
        nonlocal has_math
        has_math = True
        return put(latex_expr_to_mathml(m.group(1), display=False))

    text = re.sub(r"\$([^$\n]+)\$", sub_math, text)

    # Footnotes [^id]
    def sub_fn(m: re.Match) -> str:
        fid = re.sub(r"[^a-zA-Z0-9_-]", "", m.group(1))
        if m.group(1) in footnotes:
            used_fns.append((fid, footnotes[m.group(1)]))
            return put(f'<sup class="fn-ref"><a href="#fn-{fid}" id="fnref-{fid}">[{html.escape(fid)}]</a></sup>')
        return ""

    text = re.sub(r"\[\^([^\]]+)\]", sub_fn, text)

    # Links [label](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: put(f'<a href="{html.escape(m.group(2).strip())}">{html.escape(m.group(1))}</a>'),
        text,
    )

    # Bold & Italic
    text = re.sub(r"\*\*([^*]+)\*\*", lambda m: put(f"<strong>{html.escape(m.group(1))}</strong>"), text)
    text = re.sub(r"\*([^*]+)\*", lambda m: put(f"<em>{html.escape(m.group(1))}</em>"), text)

    escaped = html.escape(text)
    for idx in range(len(stashed) - 1, -1, -1):
        escaped = escaped.replace(f"%%XHTMLTOK{idx}%%", stashed[idx])
    return escaped, has_math


def markdown_to_xhtml_fragment(
    md_text: str,
    md_file: Path,
    img_collector: dict[str, Path],
    img_prefix: str = "images/",
) -> tuple[str, str, bool]:
    """Return (chapter_title, xhtml_body_inner, uses_mathml)."""
    raw_lines = md_text.splitlines()
    footnotes: dict[str, str] = {}
    body_lines: list[str] = []
    chapter_title = md_file.stem

    for ln in raw_lines:
        fm = re.match(r"^\[\^([^\]]+)\]:\s*(.+)$", ln.strip())
        if fm:
            footnotes[fm.group(1)] = fm.group(2).strip()
        else:
            body_lines.append(ln)

    used_fns: list[tuple[str, str]] = []
    uses_math = False
    out: list[str] = []
    i = 0
    n = len(body_lines)

    while i < n:
        s = body_lines[i].strip()
        if not s or (s.startswith("<!--") and s.endswith("-->")):
            i += 1
            continue

        if s.startswith("```"):
            i += 1
            cbuf = []
            while i < n and not body_lines[i].strip().startswith("```"):
                cbuf.append(body_lines[i])
                i += 1
            i += 1
            out.append(f'<pre dir="ltr" class="code-block"><code>{html.escape(chr(10).join(cbuf))}</code></pre>')
            continue

        if s.startswith("$$"):
            uses_math = True
            if s.endswith("$$") and len(s) > 4:
                expr = s[2:-2].strip()
                i += 1
            else:
                i += 1
                mbuf = []
                while i < n and not body_lines[i].strip().startswith("$$"):
                    mbuf.append(body_lines[i])
                    i += 1
                i += 1
                expr = " ".join(mbuf)
            out.append(f'<div class="math-block" dir="ltr">{latex_expr_to_mathml(expr, display=True)}</div>')
            continue

        if s in {"* * *", "***", "---", "___"}:
            out.append('<hr class="scene-break"/>')
            i += 1
            continue

        img_m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", s)
        if img_m:
            cap, rel_p = img_m.group(1).strip(), img_m.group(2).strip()
            src_img = (md_file.parent / rel_p).resolve()
            if src_img.is_file():
                img_collector[src_img.name] = src_img
                cap_html, mflag = convert_inline_xhtml(cap, footnotes, used_fns)
                uses_math = uses_math or mflag
                fig_cap = f"<figcaption>{cap_html}</figcaption>" if cap else ""
                out.append(
                    f'<figure class="book-figure"><img src="{img_prefix}{html.escape(src_img.name)}" '
                    f'alt="{html.escape(cap or src_img.stem)}"/>{fig_cap}</figure>'
                )
            i += 1
            continue

        if s.startswith("|") and s.endswith("|") and i + 1 < n and re.match(r"^\|\s*[-:]+", body_lines[i + 1].strip()):
            hdrs = [c.strip() for c in s.strip("|").split("|")]
            i += 2
            rows = []
            while i < n and body_lines[i].strip().startswith("|") and body_lines[i].strip().endswith("|"):
                rows.append([c.strip() for c in body_lines[i].strip().strip("|").split("|")])
                i += 1
            col_n = max(len(hdrs), *(len(r) for r in rows)) if rows else len(hdrs)
            th_cells = []
            for c in hdrs + [""] * (col_n - len(hdrs)):
                ch, mf = convert_inline_xhtml(c, footnotes, used_fns)
                uses_math = uses_math or mf
                th_cells.append(f"<th>{ch}</th>")
            tr_rows = []
            for r in rows:
                tds = []
                for c in r + [""] * (col_n - len(r)):
                    ch, mf = convert_inline_xhtml(c, footnotes, used_fns)
                    uses_math = uses_math or mf
                    tds.append(f"<td>{ch}</td>")
                tr_rows.append(f"<tr>{''.join(tds)}</tr>")
            out.append(f'<table><thead><tr>{"".join(th_cells)}</tr></thead><tbody>{"".join(tr_rows)}</tbody></table>')
            continue

        if s.startswith(">"):
            qlines = []
            while i < n and body_lines[i].strip().startswith(">"):
                qlines.append(re.sub(r"^>\s?", "", body_lines[i].strip()))
                i += 1
            qtxt, mf = convert_inline_xhtml(" ".join(qlines), footnotes, used_fns)
            uses_math = uses_math or mf
            out.append(f"<blockquote><p>{qtxt}</p></blockquote>")
            continue

        hm = re.match(r"^(#{1,4})\s+(.+)$", s)
        if hm:
            lvl = len(hm.group(1))
            raw_h = hm.group(2).strip()
            if lvl == 1:
                chapter_title = re.sub(r"[*_`]", "", raw_h)
            htxt, mf = convert_inline_xhtml(raw_h, footnotes, used_fns)
            uses_math = uses_math or mf
            out.append(f"<h{lvl}>{htxt}</h{lvl}>")
            i += 1
            continue

        if re.match(r"^[-*]\s+", s):
            items = []
            while i < n and re.match(r"^[-*]\s+", body_lines[i].strip()):
                it_raw = re.sub(r"^[-*]\s+", "", body_lines[i].strip())
                it_h, mf = convert_inline_xhtml(it_raw, footnotes, used_fns)
                uses_math = uses_math or mf
                items.append(f"<li>{it_h}</li>")
                i += 1
            out.append(f"<ul>{''.join(items)}</ul>")
            continue

        if re.match(r"^\d+\.\s+", s):
            items = []
            while i < n and re.match(r"^\d+\.\s+", body_lines[i].strip()):
                it_raw = re.sub(r"^\d+\.\s+", "", body_lines[i].strip())
                it_h, mf = convert_inline_xhtml(it_raw, footnotes, used_fns)
                uses_math = uses_math or mf
                items.append(f"<li>{it_h}</li>")
                i += 1
            out.append(f"<ol>{''.join(items)}</ol>")
            continue

        p_buf = [s]
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
            p_buf.append(nxt)
            i += 1
        ptxt, mf = convert_inline_xhtml(" ".join(p_buf), footnotes, used_fns)
        uses_math = uses_math or mf
        out.append(f"<p>{ptxt}</p>")

    if used_fns:
        seen = set()
        fn_items = []
        for fid, fbody in used_fns:
            if fid not in seen:
                seen.add(fid)
                fb_html = html.escape(fbody)
                fn_items.append(f'<li id="fn-{fid}">{fb_html} <a href="#fnref-{fid}">↩</a></li>')
        out.append(f'<aside class="footnotes"><hr/><ol>{"".join(fn_items)}</ol></aside>')

    return chapter_title, "\n".join(out), uses_math


def build_epub3(cfg: dict, section_files: list[Path], dist_dir: Path) -> Path:
    is_ar = cfg.get("language", "ar") == "ar"
    lang = cfg.get("language", "ar")
    direction = "rtl" if is_ar else "ltr"
    slug = cfg.get("slug", "book")
    epub_path = dist_dir / f"{slug}.epub"
    book_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"book-studio.{slug}.{cfg.get('title', '')}"))
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    img_collector: dict[str, Path] = {}
    chapters_meta = []

    for idx, sec in enumerate(section_files, start=1):
        ch_title, inner_xhtml, uses_math = markdown_to_xhtml_fragment(
            sec.read_text(encoding="utf-8"), sec, img_collector, img_prefix="images/"
        )
        fname = f"sec-{idx:02d}.xhtml"
        full_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{lang}" lang="{lang}" dir="{direction}">
<head>
  <meta charset="utf-8"/>
  <title>{html.escape(ch_title)}</title>
  <link rel="stylesheet" type="text/css" href="styles/book.css"/>
</head>
<body>
  <section epub:type="chapter">
{inner_xhtml}
  </section>
</body>
</html>
"""
        # Parse XML strictly before packaging!
        ET.fromstring(full_xhtml.encode("utf-8"))
        chapters_meta.append({"id": f"sec-{idx:02d}", "href": fname, "title": ch_title, "xhtml": full_xhtml, "mathml": uses_math})

    epub_css = f"""/* Reflowable E-Reader Safe Stylesheet ({direction.upper()}) */
html, body {{
  direction: {direction};
  line-height: 1.7;
  margin: 0;
  padding: 0 2%;
}}
h1, h2, h3 {{
  line-height: 1.3;
  margin-top: 1.4em;
  margin-bottom: 0.6em;
}}
p {{
  margin: 0 0 0.85em 0;
  text-align: justify;
}}
pre.code-block, code.inline-code, .math-block {{
  direction: ltr;
  text-align: left;
  unicode-bidi: embed;
  font-family: monospace;
}}
pre.code-block {{
  padding: 0.75em;
  border: 1px solid #94A3B8;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.88em;
}}
table {{
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
  font-size: 0.92em;
}}
th, td {{
  border: 1px solid #94A3B8;
  padding: 0.45em;
}}
blockquote {{
  margin: 1em 0;
  padding: 0.5em 1em;
  border-inline-start: 3px solid #64748B;
}}
figure.book-figure {{
  text-align: center;
  margin: 1.2em 0;
}}
figure.book-figure img {{
  max-width: 100%;
  height: auto;
}}
hr.scene-break {{
  border: none;
  border-top: 1px solid #94A3B8;
  width: 35%;
  margin: 1.5em auto;
}}
"""

    toc_title = "فهرس المحتويات" if is_ar else "Table of Contents"
    nav_links = "\n".join(
        f'        <li><a href="{c["href"]}">{html.escape(c["title"])}</a></li>' for c in chapters_meta
    )
    nav_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{lang}" lang="{lang}" dir="{direction}">
<head>
  <meta charset="utf-8"/>
  <title>{toc_title}</title>
  <link rel="stylesheet" type="text/css" href="styles/book.css"/>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>{toc_title}</h1>
    <ol>
{nav_links}
    </ol>
  </nav>
</body>
</html>
"""
    ET.fromstring(nav_xhtml.encode("utf-8"))

    manifest_items = [
        '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '    <item id="css" href="styles/book.css" media-type="text/css"/>',
    ]
    cover_png = dist_dir / "cover-ebook.png"
    if cover_png.is_file():
        manifest_items.append('    <item id="cover-img" href="images/cover-ebook.png" media-type="image/png" properties="cover-image"/>')

    mime_by_ext = {
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    for idx, (img_name, img_path) in enumerate(sorted(img_collector.items()), start=1):
        mtype = mime_by_ext.get(img_path.suffix.lower(), "application/octet-stream")
        manifest_items.append(f'    <item id="img-{idx:02d}" href="images/{html.escape(img_name)}" media-type="{mtype}"/>')

    spine_items = ['    <itemref idref="nav"/>']
    for c in chapters_meta:
        props = ' properties="mathml"' if c["mathml"] else ""
        manifest_items.append(
            f'    <item id="{c["id"]}" href="{c["href"]}" media-type="application/xhtml+xml"{props}/>'
        )
        spine_items.append(f'    <itemref idref="{c["id"]}"/>')

    isbn_ebook = cfg.get("isbn", {}).get("ebook", f"urn:uuid:{book_uuid}")
    opf_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id" xml:lang="{lang}" dir="{direction}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">{html.escape(isbn_ebook)}</dc:identifier>
    <dc:title>{html.escape(cfg.get("title", "Untitled"))}</dc:title>
    <dc:creator>{html.escape(cfg.get("author", "Unknown"))}</dc:creator>
    <dc:publisher>{html.escape(cfg.get("publisher", ""))}</dc:publisher>
    <dc:language>{lang}</dc:language>
    <meta property="dcterms:modified">{modified}</meta>
  </metadata>
  <manifest>
{chr(10).join(manifest_items)}
  </manifest>
  <spine page-progression-direction="{direction}">
{chr(10).join(spine_items)}
  </spine>
</package>
"""
    ET.fromstring(opf_xml.encode("utf-8"))

    container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

    with zipfile.ZipFile(epub_path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container_xml, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/styles/book.css", epub_css, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/nav.xhtml", nav_xhtml, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/content.opf", opf_xml, compress_type=zipfile.ZIP_DEFLATED)
        if cover_png.is_file():
            zf.write(cover_png, "OEBPS/images/cover-ebook.png", compress_type=zipfile.ZIP_DEFLATED)
        for img_name, img_path in sorted(img_collector.items()):
            zf.write(img_path, f"OEBPS/images/{img_name}", compress_type=zipfile.ZIP_DEFLATED)
        for c in chapters_meta:
            zf.writestr(f"OEBPS/{c['href']}", c["xhtml"], compress_type=zipfile.ZIP_DEFLATED)

    return epub_path


def validate_epub_archive(epub_path: Path, expected_direction: str) -> list[str]:
    errors: list[str] = []
    if not epub_path.is_file():
        return [f"Missing EPUB file: {epub_path}"]

    with zipfile.ZipFile(epub_path, "r") as zf:
        infos = zf.infolist()
        if not infos or infos[0].filename != "mimetype":
            errors.append("First ZIP entry in EPUB must be 'mimetype'")
        elif infos[0].compress_type != zipfile.ZIP_STORED:
            errors.append("'mimetype' entry must be stored uncompressed (ZIP_STORED)")
        elif zf.read("mimetype") != b"application/epub+zip":
            errors.append("Invalid 'mimetype' content")

        names = set(zf.namelist())
        for req in ["META-INF/container.xml", "OEBPS/content.opf", "OEBPS/nav.xhtml"]:
            if req not in names:
                errors.append(f"Missing required EPUB entry: {req}")

        if "OEBPS/content.opf" in names:
            opf_root = ET.fromstring(zf.read("OEBPS/content.opf"))
            ns = {"opf": "http://www.idpf.org/2007/opf"}
            spine = opf_root.find("opf:spine", ns)
            if spine is None:
                errors.append("Missing <spine> in content.opf")
            else:
                ppd = spine.attrib.get("page-progression-direction", "")
                if ppd != expected_direction:
                    errors.append(f"Spine page-progression-direction='{ppd}' != expected '{expected_direction}'")

            for item in opf_root.findall("opf:manifest/opf:item", ns):
                href = item.attrib.get("href", "")
                full_member = f"OEBPS/{href}"
                if full_member not in names:
                    errors.append(f"Broken manifest href in EPUB: {full_member}")
                elif full_member.endswith(".xhtml"):
                    try:
                        ET.fromstring(zf.read(full_member))
                    except ET.ParseError as exc:
                        errors.append(f"XML parse error in {full_member}: {exc}")

    return errors


def build_static_web_book(cfg: dict, section_files: list[Path], dist_dir: Path) -> Path:
    is_ar = cfg.get("language", "ar") == "ar"
    lang = cfg.get("language", "ar")
    direction = "rtl" if is_ar else "ltr"
    web_dir = dist_dir / "web-book"
    assets_out = web_dir / "assets"
    assets_out.mkdir(parents=True, exist_ok=True)

    img_collector: dict[str, Path] = {}
    pages = []
    search_docs = []

    for idx, sec in enumerate(section_files, start=1):
        raw_md = sec.read_text(encoding="utf-8")
        ch_title, body_html, _ = markdown_to_xhtml_fragment(raw_md, sec, img_collector, img_prefix="assets/")
        slug_html = f"chapter-{idx:02d}.html"
        plain_txt = re.sub(r"<[^>]+>", " ", body_html)
        plain_txt = re.sub(r"\s+", " ", plain_txt).strip()
        pages.append({"index": idx, "file": slug_html, "title": ch_title, "html": body_html})
        search_docs.append({"file": slug_html, "title": ch_title, "text": plain_txt[:4000]})

    for img_name, img_path in img_collector.items():
        shutil.copy2(img_path, assets_out / img_name)

    cover_png = dist_dir / "cover-ebook.png"
    has_cover = cover_png.is_file()
    if has_cover:
        shutil.copy2(cover_png, assets_out / "cover-ebook.png")

    reader_css = f""":root {{
  --bg: #F8FAFC; --panel: #FFFFFF; --fg: #0F172A; --muted: #475569; --border: #E2E8F0; --accent: #2563EB;
}}
[data-theme="sepia"] {{
  --bg: #FBF5E8; --panel: #F5ECD8; --fg: #291D12; --muted: #6B533B; --border: #E2D3B5; --accent: #B45309;
}}
[data-theme="dark"] {{
  --bg: #0B1220; --panel: #111B2E; --fg: #E2E8F0; --muted: #94A3B8; --border: #1E293B; --accent: #38BDF8;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--bg); color: var(--fg); direction: {direction};
  font-family: system-ui, -apple-system, "Segoe UI", "DejaVu Sans", sans-serif; line-height: 1.78;
}}
.layout {{ display: grid; grid-template-columns: 290px 1fr; min-height: 100vh; }}
@media (max-width: 840px) {{ .layout {{ grid-template-columns: 1fr; }} }}
aside.sidebar {{
  background: var(--panel); border-inline-end: 1px solid var(--border); padding: 1.25rem;
}}
aside.sidebar h2 {{ font-size: 1.05rem; margin-top: 0; }}
aside.sidebar nav a {{
  display: block; padding: 0.45rem 0.6rem; border-radius: 6px; color: var(--fg); text-decoration: none; font-size: 0.92rem;
}}
aside.sidebar nav a.active, aside.sidebar nav a:hover {{ background: var(--bg); color: var(--accent); font-weight: 600; }}
main.reader {{ max-width: 760px; margin: 0 auto; padding: 2.2rem 1.5rem 4rem; width: 100%; }}
.toolbar {{ display: flex; gap: 0.5rem; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; flex-wrap: wrap; }}
.toolbar input {{
  padding: 0.45rem 0.75rem; border: 1px solid var(--border); border-radius: 6px; background: var(--panel); color: var(--fg); min-width: 210px;
}}
.theme-btns button {{
  border: 1px solid var(--border); background: var(--panel); color: var(--fg); padding: 0.35rem 0.65rem; border-radius: 6px; cursor: pointer;
}}
pre.code-block, code.inline-code, .math-block {{ direction: ltr; text-align: left; unicode-bidi: embed; font-family: monospace; }}
pre.code-block {{ background: var(--panel); border: 1px solid var(--border); padding: 0.9rem; border-radius: 8px; overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; margin: 1.2rem 0; }}
th, td {{ border: 1px solid var(--border); padding: 0.5rem; }}
figure.book-figure img {{ max-width: 100%; height: auto; border-radius: 6px; }}
.pager {{ display: flex; justify-content: space-between; margin-top: 3rem; padding-top: 1.2rem; border-top: 1px solid var(--border); }}
.pager a {{ color: var(--accent); text-decoration: none; font-weight: 600; }}
#search-results {{ margin-bottom: 1rem; }}
#search-results a {{ display: block; padding: 0.5rem; background: var(--panel); border: 1px solid var(--border); border-radius: 6px; margin-bottom: 0.4rem; color: var(--accent); text-decoration: none; }}
"""
    (web_dir / "reader.css").write_text(reader_css, encoding="utf-8")
    (web_dir / "search-index.json").write_text(json.dumps(search_docs, ensure_ascii=False), encoding="utf-8")

    search_js = """const DOCS = __DOCS__;
function setTheme(mode) {
  document.documentElement.setAttribute('data-theme', mode);
  try { localStorage.setItem('bookTheme', mode); } catch (_) {}
}
(function init() {
  try {
    const saved = localStorage.getItem('bookTheme');
    if (saved) document.documentElement.setAttribute('data-theme', saved);
  } catch (_) {}
  const input = document.getElementById('book-search');
  const box = document.getElementById('search-results');
  if (!input || !box) return;
  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    box.innerHTML = '';
    if (q.length < 2) return;
    DOCS.filter(d => d.title.toLowerCase().includes(q) || d.text.toLowerCase().includes(q))
        .slice(0, 6)
        .forEach(d => {
          const a = document.createElement('a');
          a.href = d.file;
          a.textContent = d.title;
          box.appendChild(a);
        });
  });
})();
""".replace("__DOCS__", json.dumps(search_docs, ensure_ascii=False))
    (web_dir / "reader.js").write_text(search_js, encoding="utf-8")

    search_ph = "ابحث في الكتاب..." if is_ar else "Search inside book..."
    home_label = "غلاف الكتاب والفهرس" if is_ar else "Book Home & TOC"

    def sidebar_for(active_file: str) -> str:
        links = [f'<a href="index.html" class="{"active" if active_file == "index.html" else ""}">{home_label}</a>']
        for p in pages:
            cls = "active" if p["file"] == active_file else ""
            links.append(f'<a href="{p["file"]}" class="{cls}">{html.escape(p["title"])}</a>')
        return f'<aside class="sidebar"><h2>{html.escape(cfg.get("title", ""))}</h2><nav>{"".join(links)}</nav></aside>'

    toolbar_html = f"""<div class="toolbar">
  <input id="book-search" type="search" placeholder="{search_ph}"/>
  <div class="theme-btns">
    <button onclick="setTheme('light')">☀</button>
    <button onclick="setTheme('sepia')">📜</button>
    <button onclick="setTheme('dark')">🌙</button>
  </div>
</div>
<div id="search-results"></div>"""

    cover_tag = '<img src="assets/cover-ebook.png" alt="Cover" style="max-width:240px;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,0.18);"/>' if has_cover else ""
    toc_cards = "".join(f'<li><a href="{p["file"]}">{html.escape(p["title"])}</a></li>' for p in pages)
    index_html = f"""<!DOCTYPE html>
<html lang="{lang}" dir="{direction}">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(cfg.get("title", ""))}</title>
  <link rel="stylesheet" href="reader.css"/>
</head>
<body>
  <div class="layout">
    {sidebar_for("index.html")}
    <main class="reader">
      {toolbar_html}
      <div style="text-align:center;margin:1.5rem 0;">
        {cover_tag}
        <h1>{html.escape(cfg.get("title", ""))}</h1>
        <p>{html.escape(cfg.get("subtitle", ""))}</p>
        <p><strong>{html.escape(cfg.get("author", ""))}</strong></p>
      </div>
      <ol>{toc_cards}</ol>
    </main>
  </div>
  <script src="reader.js"></script>
</body>
</html>
"""
    (web_dir / "index.html").write_text(index_html, encoding="utf-8")

    for i, p in enumerate(pages):
        prev_link = f'<a href="{pages[i - 1]["file"]}">← {html.escape(pages[i - 1]["title"])}</a>' if i > 0 else '<span></span>'
        next_link = f'<a href="{pages[i + 1]["file"]}">{html.escape(pages[i + 1]["title"])} →</a>' if i + 1 < len(pages) else '<span></span>'
        ch_doc = f"""<!DOCTYPE html>
<html lang="{lang}" dir="{direction}">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(p["title"])} — {html.escape(cfg.get("title", ""))}</title>
  <link rel="stylesheet" href="reader.css"/>
</head>
<body>
  <div class="layout">
    {sidebar_for(p["file"])}
    <main class="reader">
      {toolbar_html}
      <article>
{p["html"]}
      </article>
      <div class="pager">{prev_link}{next_link}</div>
    </main>
  </div>
  <script src="reader.js"></script>
</body>
</html>
"""
        (web_dir / p["file"]).write_text(ch_doc, encoding="utf-8")

    return web_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and validate EPUB 3.3 + Static HTML Web Book.")
    parser.add_argument("--project", required=True, help="Path to Book Studio project root.")
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing dist/<slug>.epub.")
    args = parser.parse_args()

    root = Path(args.project).resolve()
    cfg = json.loads((root / "book.config.json").read_text(encoding="utf-8"))
    is_ar = cfg.get("language", "ar") == "ar"
    direction = "rtl" if is_ar else "ltr"
    dist = root / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    slug = cfg.get("slug", "book")
    epub_path = dist / f"{slug}.epub"

    if not args.validate_only:
        sections = (
            sorted((root / "manuscript" / "frontmatter").glob("*.md"))
            + sorted((root / "manuscript" / "chapters").glob("*.md"))
            + sorted((root / "manuscript" / "backmatter").glob("*.md"))
        )
        if not sections:
            raise SystemExit("Error: no manuscript .md files found.")
        epub_path = build_epub3(cfg, sections, dist)
        web_dir = build_static_web_book(cfg, sections, dist)
        print(f"[OK] Built Static Web Book -> {web_dir.relative_to(root)}/index.html")

    errs = validate_epub_archive(epub_path, direction)
    if errs:
        for e in errs:
            print(f"[FAIL] {e}")
        return 1
    print(f"[OK] Validated EPUB 3.3 ({direction.upper()} spine, uncompressed mimetype, XML verified) -> {epub_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
