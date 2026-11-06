#!/usr/bin/env python3
"""
import_manuscript.py — Import .docx, .pdf, or .md/.txt manuscripts into Book Studio
and compute the BiDi-aware Content-Integrity Fingerprint Lock (manuscript.lock.json).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

try:
    import pymupdf
except ImportError:  # pragma: no cover
    import fitz as pymupdf  # type: ignore

import docx

FRONTMATTER_TITLES = {
    "preface",
    "foreword",
    "introduction",
    "dedication",
    "acknowledgments",
    "acknowledgements",
    "مقدمة",
    "مقدمة المؤلف",
    "تصدير",
    "تمهيد",
    "إهداء",
    "الإهداء",
    "شكر وتقدير",
}
BACKMATTER_TITLES = {
    "epilogue",
    "afterword",
    "appendix",
    "glossary",
    "bibliography",
    "references",
    "خاتمة",
    "الخاتمة",
    "ملحق",
    "الملاحق",
    "مسرد المصطلحات",
    "المراجع",
}

AR_DIACRITICS_RE = re.compile(r"[\u0640\u064B-\u065F\u0670\u06D6-\u06ED]")
MD_SYNTAX_RE = re.compile(
    r"```[\s\S]*?```|`[^`]*`|!\[[^\]]*\]\([^)]*\)|\[([^\]]+)\]\([^)]*\)|\[\^[^\]]+\]|[#>*_~|-]"
)
NUMBER_TOKEN_RE = re.compile(r"[\d\u0660-\u0669]+(?:[.,][\d\u0660-\u0669]+)*")


def normalize_text(raw: str) -> str:
    text = unicodedata.normalize("NFKC", raw)
    text = text.replace("\u00ad", "").replace("\u200b", "").replace("\r\n", "\n").replace("\r", "\n")
    return text


def compute_content_skeleton(markdown_text: str) -> dict:
    """Compute a BiDi-safe, formatting-agnostic content fingerprint of prose + code + tables."""
    norm = normalize_text(markdown_text)
    # Keep code block contents too (just strip triple-backtick language tag lines)
    cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*$", "", norm, flags=re.MULTILINE)
    cleaned = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r" \1 ", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]*\)", r" \1 ", cleaned)
    cleaned = re.sub(r"\[\^([^\]]+)\]:?", " ", cleaned)
    cleaned = AR_DIACRITICS_RE.sub("", cleaned)

    letters_and_digits = [
        ch.lower()
        for ch in cleaned
        if unicodedata.category(ch)[0] in ("L", "N")
    ]
    freq = Counter(letters_and_digits)
    canonical_freq_json = json.dumps(dict(sorted(freq.items())), ensure_ascii=False, sort_keys=True)
    char_multiset_sha256 = hashlib.sha256(canonical_freq_json.encode("utf-8")).hexdigest()

    # Normalize Eastern Arabic digits to Western for canonical numeric inventory
    digit_trans = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    numbers = [tok.translate(digit_trans).replace(",", "") for tok in NUMBER_TOKEN_RE.findall(cleaned)]
    words = re.findall(r"[\w\u0600-\u06FF]+", cleaned)

    return {
        "total_alnum_chars": len(letters_and_digits),
        "word_count": len(words),
        "char_multiset_sha256": char_multiset_sha256,
        "char_counts": dict(sorted(freq.items())),
        "numeric_tokens": sorted(numbers),
        "numeric_count": len(numbers),
    }


def extract_docx_footnotes(docx_path: Path) -> dict[str, str]:
    footnotes: dict[str, str] = {}
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(docx_path, "r") as zf:
        if "word/footnotes.xml" not in zf.namelist():
            return footnotes
        root = ET.fromstring(zf.read("word/footnotes.xml"))
        for fn in root.findall("w:footnote", ns):
            fn_id = fn.attrib.get(f"{{{ns['w']}}}id", "")
            if fn_id in {"", "0", "-1"}:
                continue
            texts = [t.text for t in fn.findall(".//w:t", ns) if t.text]
            joined = normalize_text("".join(texts)).strip()
            if joined:
                footnotes[fn_id] = joined
    return footnotes


def import_docx_file(docx_path: Path, figures_dir: Path) -> str:
    doc = docx.Document(str(docx_path))
    footnotes_map = extract_docx_footnotes(docx_path)

    # Extract media files if present
    extracted_media: list[str] = []
    with zipfile.ZipFile(docx_path, "r") as zf:
        idx = 1
        for member in sorted(zf.namelist()):
            if member.startswith("word/media/"):
                ext = Path(member).suffix.lower()
                if ext in {".png", ".jpg", ".jpeg", ".svg", ".webp"}:
                    out_name = f"imported-fig-{idx:02d}{ext}"
                    (figures_dir / out_name).write_bytes(zf.read(member))
                    extracted_media.append(out_name)
                    idx += 1

    ns_w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    used_footnotes: list[tuple[str, str]] = []
    lines: list[str] = []

    # Iterate document body elements in exact document order (paragraphs + tables)
    para_map = {p._p: p for p in doc.paragraphs}
    table_map = {t._tbl: t for t in doc.tables}
    media_cursor = 0

    for child in doc.element.body:
        if child in para_map:
            p = para_map[child]
            style_name = (p.style.name if p.style else "").lower()

            # Check for inline footnote references & run formatting
            buf: list[str] = []
            for el in p._p.iter():
                if el.tag == f"{ns_w}t" and el.text:
                    buf.append(el.text)
                elif el.tag == f"{ns_w}footnoteReference":
                    fn_id = el.attrib.get(f"{ns_w}id", "")
                    if fn_id in footnotes_map:
                        buf.append(f"[^{fn_id}]")
                        used_footnotes.append((fn_id, footnotes_map[fn_id]))
                elif el.tag.endswith("}blip") and media_cursor < len(extracted_media):
                    fig_file = extracted_media[media_cursor]
                    media_cursor += 1
                    lines.append(f"\n![Figure {media_cursor}](../../assets/figures/{fig_file})\n")

            text = normalize_text("".join(buf)).strip()
            if not text:
                continue

            if "heading 1" in style_name or style_name == "title":
                lines.append(f"\n# {text}\n")
            elif "heading 2" in style_name:
                lines.append(f"\n## {text}\n")
            elif "heading 3" in style_name:
                lines.append(f"\n### {text}\n")
            elif "quote" in style_name:
                lines.append(f"\n> {text}\n")
            elif "list" in style_name:
                lines.append(f"- {text}")
            else:
                lines.append(f"\n{text}\n")

        elif child in table_map:
            tbl = table_map[child]
            rows = []
            for row in tbl.rows:
                cells = [normalize_text(c.text).replace("\n", " ").strip() for c in row.cells]
                rows.append(cells)
            if rows:
                col_count = max(len(r) for r in rows)
                padded = [r + [""] * (col_count - len(r)) for r in rows]
                lines.append("")
                lines.append("| " + " | ".join(padded[0]) + " |")
                lines.append("| " + " | ".join(["---"] * col_count) + " |")
                for r in padded[1:]:
                    lines.append("| " + " | ".join(r) + " |")
                lines.append("")

    if used_footnotes:
        lines.append("")
        seen = set()
        for fn_id, fn_body in used_footnotes:
            if fn_id not in seen:
                seen.add(fn_id)
                lines.append(f"[^{fn_id}]: {fn_body}")

    return "\n".join(lines).strip() + "\n"


def import_pdf_file(pdf_path: Path, figures_dir: Path) -> str:
    doc = pymupdf.open(str(pdf_path))
    sizes: list[float] = []
    blocks_data: list[tuple[float, str]] = []
    fig_idx = 1

    for page_num, page in enumerate(doc, start=1):
        d = page.get_text("dict")
        for b in d.get("blocks", []):
            if b.get("type") == 0:
                for line in b.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans:
                        continue
                    max_sz = max(float(s.get("size", 11.0)) for s in spans)
                    txt = normalize_text("".join(s.get("text", "") for s in spans)).strip()
                    if txt:
                        sizes.append(max_sz)
                        blocks_data.append((max_sz, txt))
        for img in page.get_images(full=True):
            xref = img[0]
            base = doc.extract_image(xref)
            if base and base.get("width", 0) >= 120 and base.get("height", 0) >= 120:
                ext = base.get("ext", "png")
                fname = f"pdf-fig-p{page_num:02d}-{fig_idx:02d}.{ext}"
                (figures_dir / fname).write_bytes(base["image"])
                blocks_data.append((-1.0, f"![Figure {fig_idx}](../../assets/figures/{fname})"))
                fig_idx += 1

    median_sz = sorted(sizes)[len(sizes) // 2] if sizes else 11.0
    out_lines: list[str] = []
    for sz, txt in blocks_data:
        if sz < 0:
            out_lines.append(f"\n{txt}\n")
        elif sz >= median_sz * 1.45:
            out_lines.append(f"\n# {txt}\n")
        elif sz >= median_sz * 1.2:
            out_lines.append(f"\n## {txt}\n")
        else:
            out_lines.append(txt)
    return "\n\n".join(out_lines).strip() + "\n"


def split_into_sections(full_md: str) -> list[tuple[str, str]]:
    """Split Markdown on top-level '# ' headings (ignoring fenced code blocks)."""
    sections: list[tuple[str, list[str]]] = []
    current_title = "Chapter 1"
    current_lines: list[str] = []
    in_fence = False

    for line in full_md.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("# ") and not line.startswith("## "):
            if current_lines and any(l.strip() for l in current_lines):
                sections.append((current_title, current_lines))
            current_title = line[2:].strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines and any(l.strip() for l in current_lines):
        sections.append((current_title, current_lines))

    result = []
    for title, lns in sections:
        body = "\n".join(lns).strip() + "\n"
        if not body.startswith("# "):
            body = f"# {title}\n\n{body}"
        result.append((title, body))
    return result


def write_lockfile(project_dir: Path) -> dict:
    ms_dir = project_dir / "manuscript"
    ordered_files: list[Path] = []
    for sub in ["frontmatter", "chapters", "backmatter"]:
        d = ms_dir / sub
        if d.is_dir():
            ordered_files.extend(sorted(d.glob("*.md")))

    combined_parts: list[str] = []
    per_file = []
    for f in ordered_files:
        txt = f.read_text(encoding="utf-8")
        combined_parts.append(txt)
        sk = compute_content_skeleton(txt)
        per_file.append(
            {
                "path": str(f.relative_to(project_dir)),
                "word_count": sk["word_count"],
                "total_alnum_chars": sk["total_alnum_chars"],
                "numeric_count": sk["numeric_count"],
                "char_multiset_sha256": sk["char_multiset_sha256"],
            }
        )

    total_sk = compute_content_skeleton("\n\n".join(combined_parts))
    lock_payload = {
        "schema_version": "1.0",
        "file_count": len(per_file),
        "files": per_file,
        "aggregate": total_sk,
    }
    lock_path = project_dir / "manuscript" / "manuscript.lock.json"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(lock_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return lock_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Import .docx/.pdf/.md manuscripts and generate manuscript.lock.json.")
    parser.add_argument("--project", required=True, help="Path to the Book Studio project root.")
    parser.add_argument("--source", default="", help="Path to input .docx, .pdf, .md/.txt file or folder.")
    parser.add_argument("--lock-only", action="store_true", help="Only recompute manuscript/manuscript.lock.json.")
    parser.add_argument("--clean", action="store_true", help="Clear existing manuscript/*.md files before importing.")
    args = parser.parse_args()

    project_dir = Path(args.project).resolve()
    figures_dir = project_dir / "assets" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    for sub in ["frontmatter", "chapters", "backmatter"]:
        (project_dir / "manuscript" / sub).mkdir(parents=True, exist_ok=True)
        if args.clean and not args.lock_only:
            for old in (project_dir / "manuscript" / sub).glob("*.md"):
                old.unlink()

    if not args.lock_only:
        if not args.source:
            raise SystemExit("Error: specify --source PATH or --lock-only")
        src = Path(args.source).resolve()
        if not src.exists():
            raise SystemExit(f"Error: source not found: {src}")

        if src.is_dir():
            raw_chunks = [normalize_text(p.read_text(encoding="utf-8")) for p in sorted(src.glob("*.md")) + sorted(src.glob("*.txt"))]
            full_md = "\n\n".join(raw_chunks)
        elif src.suffix.lower() == ".docx":
            full_md = import_docx_file(src, figures_dir)
        elif src.suffix.lower() == ".pdf":
            full_md = import_pdf_file(src, figures_dir)
        else:
            full_md = normalize_text(src.read_text(encoding="utf-8"))

        sections = split_into_sections(full_md)
        fm_i, ch_i, bm_i = 1, 1, 1
        for title, body in sections:
            low = title.strip().lower()
            if low in FRONTMATTER_TITLES:
                out = project_dir / "manuscript" / "frontmatter" / f"{fm_i:02d}-frontmatter.md"
                fm_i += 1
            elif low in BACKMATTER_TITLES:
                out = project_dir / "manuscript" / "backmatter" / f"{bm_i:02d}-backmatter.md"
                bm_i += 1
            else:
                out = project_dir / "manuscript" / "chapters" / f"ch-{ch_i:02d}.md"
                ch_i += 1
            out.write_text(body, encoding="utf-8")

    lock = write_lockfile(project_dir)
    print(f"[OK] Manuscript locked: {lock['file_count']} section(s), {lock['aggregate']['word_count']} words, "
          f"{lock['aggregate']['numeric_count']} numeric tokens.")
    print(f"     Lock SHA-256: {lock['aggregate']['char_multiset_sha256'][:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
