#!/usr/bin/env python3
"""
calc_and_render_cover.py — Exact KDP/IngramSpark Spine Calculator & RTL/LTR Full-Wrap Cover Renderer

Reads ACTUAL page count from dist/interior-paperback.pdf (unless --pages explicitly passed with --spec-only),
mirrors Front/Back cover panels automatically for Arabic (RTL) vs English (LTR), suppresses spine text
if pages < 79, reserves the 2.0" x 1.2" barcode keepout zone, and emits:
- dist/cover-spec.json
- dist/cover-wrap-proof.svg
- dist/cover-wrap-print.pdf
- dist/cover-ebook.png (1600x2560)
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pikepdf
from PIL import Image

try:
    import pymupdf
except ImportError:  # pragma: no cover
    import fitz as pymupdf  # type: ignore

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

CALIPER_IN: dict[str, float] = {
    "white": 0.002252,
    "cream": 0.002500,
    "color-standard": 0.002252,
    "color-premium": 0.002347,
}

COVER_THEMES: dict[str, tuple[str, str, str]] = {
    "trade-nonfiction": ("#0F172A", "#38BDF8", "#F8FAFC"),
    "literary-novel": ("#1C1917", "#F59E0B", "#FAFAF9"),
    "technical-code": ("#0B1220", "#22C55E", "#F1F5F9"),
    "academic-monograph": ("#1E293B", "#94A3B8", "#F8FAFC"),
    "executive-report": ("#1E1B4B", "#818CF8", "#EEF2FF"),
    "classic-arabic-turath": ("#291D12", "#D97706", "#FEF3C7"),
}


def in_to_mm(v: float) -> float:
    return round(v * 25.4, 3)


def in_to_pt(v: float) -> float:
    return round(v * 72.0, 3)


def compute_cover_geometry(cfg: dict, page_count: int) -> dict:
    is_ar = cfg.get("language", "ar") == "ar"
    direction = cfg.get("direction", "rtl" if is_ar else "ltr")
    print_cfg = cfg.get("print", {})
    trim_key = print_cfg.get("trim", "6x9").lower()
    stock = print_cfg.get("paper_stock", "white").lower()
    bleed = float(print_cfg.get("bleed_in", 0.125))

    trim_w, trim_h = TRIMS_IN.get(trim_key, (6.0, 9.0))
    caliper = CALIPER_IN.get(stock, 0.002252)
    spine_w = round(page_count * caliper, 4)
    full_w = round(2 * bleed + 2 * trim_w + spine_w, 4)
    full_h = round(2 * bleed + trim_h, 4)

    spine_x = round(bleed + trim_w, 4)
    if direction == "rtl":
        # Arabic right-bound book: Front Cover is LEFT of spine; Back Cover is RIGHT of spine!
        front_x = round(bleed, 4)
        back_x = round(bleed + trim_w + spine_w, 4)
    else:
        # English left-bound book: Back Cover is LEFT of spine; Front Cover is RIGHT of spine!
        back_x = round(bleed, 4)
        front_x = round(bleed + trim_w + spine_w, 4)

    # Barcode keepout: 2.0" x 1.2", 0.35" inside bottom trim and 0.35" from outer/inner safe margin of Back Cover
    barcode_w, barcode_h = 2.0, 1.2
    barcode_x = round(back_x + trim_w - 0.35 - barcode_w, 4) if direction == "ltr" else round(back_x + 0.35, 4)
    barcode_y = round(bleed + trim_h - 0.35 - barcode_h, 4)

    return {
        "language": cfg.get("language", "ar"),
        "direction": direction,
        "trim": trim_key,
        "paper_stock": stock,
        "page_count": page_count,
        "caliper_in": caliper,
        "spine_text_allowed": page_count >= 79,
        "bleed_in": bleed,
        "trim_width_in": trim_w,
        "trim_height_in": trim_h,
        "spine_width_in": spine_w,
        "spine_width_mm": in_to_mm(spine_w),
        "full_width_in": full_w,
        "full_height_in": full_h,
        "full_width_mm": in_to_mm(full_w),
        "full_height_mm": in_to_mm(full_h),
        "full_width_pt": in_to_pt(full_w),
        "full_height_pt": in_to_pt(full_h),
        "panels_in": {
            "front": {"x": front_x, "y": bleed, "width": trim_w, "height": trim_h},
            "spine": {"x": spine_x, "y": bleed, "width": spine_w, "height": trim_h},
            "back": {"x": back_x, "y": bleed, "width": trim_w, "height": trim_h},
            "barcode_keepout": {"x": barcode_x, "y": barcode_y, "width": barcode_w, "height": barcode_h},
        },
    }


def render_proof_svg(cfg: dict, spec: dict, blurb: str, out_svg: Path) -> None:
    scale = 96.0  # 96 SVG user units per inch
    fw = round(spec["full_width_in"] * scale, 2)
    fh = round(spec["full_height_in"] * scale, 2)
    bg_hex, accent_hex, text_hex = COVER_THEMES.get(cfg.get("style_pack", "trade-nonfiction"), ("#0F172A", "#38BDF8", "#F8FAFC"))

    fp = spec["panels_in"]["front"]
    sp = spec["panels_in"]["spine"]
    bp = spec["panels_in"]["back"]
    bc = spec["panels_in"]["barcode_keepout"]
    bleed_px = round(spec["bleed_in"] * scale, 2)
    tw_px = round( (spec["full_width_in"] - 2 * spec["bleed_in"]) * scale, 2 )
    th_px = round( spec["trim_height_in"] * scale, 2 )

    fcx = round((fp["x"] + fp["width"] / 2) * scale, 2)
    bcx = round((bp["x"] + bp["width"] / 2) * scale, 2)
    scx = round((sp["x"] + sp["width"] / 2) * scale, 2)
    scy = round((sp["y"] + sp["height"] / 2) * scale, 2)

    title = html.escape(cfg.get("title", ""))
    subtitle = html.escape(cfg.get("subtitle", ""))
    author = html.escape(cfg.get("author", ""))
    isbn = html.escape(cfg.get("isbn", {}).get("paperback", ""))
    safe_blurb = html.escape(blurb[:220])

    spine_svg = ""
    if spec["spine_text_allowed"]:
        spine_svg = (
            f'  <text x="{scx}" y="{scy}" text-anchor="middle" dominant-baseline="central" '
            f'transform="rotate(90 {scx} {scy})" font-family="DejaVu Sans, sans-serif" font-size="11" '
            f'fill="{text_hex}">{title} — {author}</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fw} {fh}" width="{fw}" height="{fh}">
  <rect x="0" y="0" width="{fw}" height="{fh}" fill="{bg_hex}"/>
  <!-- Accent band on Front Cover -->
  <rect x="{round((fp['x'] + 0.6) * scale, 2)}" y="{round((fp['y'] + 1.35) * scale, 2)}" width="{round((fp['width'] - 1.2) * scale, 2)}" height="5" rx="2.5" fill="{accent_hex}"/>
  <text x="{fcx}" y="{round((fp['y'] + 2.2) * scale, 2)}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="24" font-weight="bold" fill="{text_hex}">{title}</text>
  <text x="{fcx}" y="{round((fp['y'] + 2.8) * scale, 2)}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="14" fill="#CBD5E1">{subtitle}</text>
  <text x="{fcx}" y="{round((fp['y'] + fp['height'] - 1.1) * scale, 2)}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="16" font-weight="bold" fill="{accent_hex}">{author}</text>

  <!-- Back Cover Blurb & Barcode Keepout -->
  <text x="{bcx}" y="{round((bp['y'] + 1.6) * scale, 2)}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="13" fill="#E2E8F0">{safe_blurb[:75]}</text>
  <rect x="{round(bc['x'] * scale, 2)}" y="{round(bc['y'] * scale, 2)}" width="{round(bc['width'] * scale, 2)}" height="{round(bc['height'] * scale, 2)}" rx="4" fill="#FFFFFF"/>
  <text x="{round((bc['x'] + bc['width'] / 2) * scale, 2)}" y="{round((bc['y'] + bc['height'] / 2) * scale, 2)}" text-anchor="middle" font-family="DejaVu Sans Mono, monospace" font-size="11" fill="#0F172A">ISBN {isbn}</text>

  {spine_svg}

  <!-- Mechanical Proof Guides (Trim + Spine Folds) -->
  <rect x="{bleed_px}" y="{bleed_px}" width="{tw_px}" height="{th_px}" fill="none" stroke="#EF4444" stroke-width="1.2" stroke-dasharray="6,4"/>
  <line x1="{round(sp['x'] * scale, 2)}" y1="0" x2="{round(sp['x'] * scale, 2)}" y2="{fh}" stroke="#38BDF8" stroke-width="1.2" stroke-dasharray="5,4"/>
  <line x1="{round((sp['x'] + sp['width']) * scale, 2)}" y1="0" x2="{round((sp['x'] + sp['width']) * scale, 2)}" y2="{fh}" stroke="#38BDF8" stroke-width="1.2" stroke-dasharray="5,4"/>
</svg>
"""
    out_svg.write_text(svg, encoding="utf-8")


def choose_cover_font() -> str:
    proc = subprocess.run(["typst", "fonts"], capture_output=True, text=True, check=False)
    installed = {ln.strip().lower(): ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}
    for cand in ["IBM Plex Sans Arabic", "Amiri", "Noto Naskh Arabic", "DejaVu Sans"]:
        if cand.lower() in installed:
            return installed[cand.lower()]
    return "DejaVu Sans"


def typst_esc(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("#", "\\#")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("$", "\\$")
        .replace("@", "\\@")
        .replace("*", "\\*")
        .replace("_", "\\_")
    )


def render_press_cover_and_ebook_via_typst(cfg: dict, spec: dict, blurb: str, dist_dir: Path) -> None:
    if not shutil.which("typst"):
        raise SystemExit("Error: 'typst' binary required to compile press PDF cover.")

    font_name = choose_cover_font()
    is_ar = spec["language"] == "ar"
    direction = spec["direction"]
    bg_hex, accent_hex, text_hex = COVER_THEMES.get(cfg.get("style_pack", "trade-nonfiction"), ("#0F172A", "#38BDF8", "#F8FAFC"))

    fp = spec["panels_in"]["front"]
    sp = spec["panels_in"]["spine"]
    bp = spec["panels_in"]["back"]
    bc = spec["panels_in"]["barcode_keepout"]

    title = typst_esc(cfg.get("title", ""))
    subtitle = typst_esc(cfg.get("subtitle", ""))
    author = typst_esc(cfg.get("author", ""))
    publisher = typst_esc(cfg.get("publisher", ""))
    isbn = typst_esc(cfg.get("isbn", {}).get("paperback", ""))
    blurb_esc = typst_esc(blurb)

    spine_block = ""
    if spec["spine_text_allowed"]:
        spine_block = f"""
#place(top + left, dx: {sp['x']}in, dy: {sp['y']}in)[
  #box(width: {sp['width']}in, height: {sp['height']}in)[
    #align(center + horizon)[
      #rotate(90deg, reflow: true)[
        #text(size: 8.5pt, weight: "bold", fill: rgb("{text_hex}"))[{title} · {author}]
      ]
    ]
  ]
]
"""

    wrap_typ = f"""// Press-Ready Full-Wrap Cover (Guide-Free, Exact Cartesian Bleed Geometry, {direction.upper()})
#set page(width: {spec['full_width_in']}in, height: {spec['full_height_in']}in, margin: 0pt, fill: rgb("{bg_hex}"))
#set text(font: "{font_name}", fill: rgb("{text_hex}"), fallback: true)

// Front Cover Panel ({'LEFT of spine (RTL)' if direction == 'rtl' else 'RIGHT of spine (LTR)'})
#place(top + left, dx: {fp['x'] + 0.55}in, dy: {fp['y'] + 1.1}in)[
  #box(width: {fp['width'] - 1.1}in, height: {fp['height'] - 2.0}in)[
    #set text(lang: "{spec['language']}", dir: {direction})
    #align(center)[
      #rect(width: 45%, height: 3.5pt, radius: 2pt, fill: rgb("{accent_hex}"))
      #v(0.45in)
      #text(size: 22pt, weight: "bold", fill: rgb("{text_hex}"))[{title}]
      #v(0.22in)
      #text(size: 12pt, fill: rgb("#CBD5E1"))[{subtitle}]
      #v(1fr)
      #line(length: 30%, stroke: 0.8pt + rgb("#64748B"))
      #v(0.2in)
      #text(size: 13.5pt, weight: "bold", fill: rgb("{accent_hex}"))[{author}]
      #v(0.12in)
      #text(size: 9.5pt, fill: rgb("#94A3B8"))[{publisher}]
    ]
  ]
]

// Back Cover Blurb (strictly above Barcode Keepout Zone!)
#place(top + left, dx: {bp['x'] + 0.55}in, dy: {bp['y'] + 0.9}in)[
  #box(width: {bp['width'] - 1.1}in, height: {bp['height'] - 2.8}in)[
    #set text(lang: "{spec['language']}", dir: {direction})
    #set par(justify: true, leading: 0.88em)
    #text(size: 10.5pt, fill: rgb("#E2E8F0"))[{blurb_esc}]
  ]
]

// White Barcode Keepout Zone (2.0in x 1.2in)
#place(top + left, dx: {bc['x']}in, dy: {bc['y']}in)[
  #rect(width: {bc['width']}in, height: {bc['height']}in, radius: 3pt, fill: rgb("#FFFFFF"))[
    #align(center + horizon)[
      #text(dir: ltr, lang: "en", font: "DejaVu Sans Mono", size: 8.5pt, fill: rgb("#0F172A"))[ISBN {isbn}]
    ]
  ]
]
{spine_block}
"""
    typ_dir = dist_dir / "typst"
    typ_dir.mkdir(parents=True, exist_ok=True)
    wrap_typ_path = typ_dir / "cover-wrap-print.typ"
    wrap_pdf_path = dist_dir / "cover-wrap-print.pdf"
    wrap_typ_path.write_text(wrap_typ, encoding="utf-8")

    subprocess.run(["typst", "compile", str(wrap_typ_path), str(wrap_pdf_path)], check=True)

    # Normalize MediaBox (full bleed) & TrimBox (trimmed spread) + strip annotations via pikepdf
    bleed_pt = in_to_pt(spec["bleed_in"])
    fw_pt = spec["full_width_pt"]
    fh_pt = spec["full_height_pt"]
    with pikepdf.open(wrap_pdf_path, allow_overwriting_input=True) as pdf:
        for p in pdf.pages:
            if "/Annots" in p:
                del p["/Annots"]
            p["/MediaBox"] = pikepdf.Array([0, 0, fw_pt, fh_pt])
            p["/BleedBox"] = pikepdf.Array([0, 0, fw_pt, fh_pt])
            p["/TrimBox"] = pikepdf.Array([bleed_pt, bleed_pt, round(fw_pt - bleed_pt, 3), round(fh_pt - bleed_pt, 3)])
        pdf.save(wrap_pdf_path)

    # Render standalone 1600x2560 eBook store front cover
    ebook_typ = f"""#set page(width: 5in, height: 8in, margin: 0.45in, fill: rgb("{bg_hex}"))
#set text(lang: "{spec['language']}", dir: {direction}, font: "{font_name}", fill: rgb("{text_hex}"), fallback: true)
#align(center)[
  #v(0.55in)
  #rect(width: 48%, height: 4pt, radius: 2pt, fill: rgb("{accent_hex}"))
  #v(0.45in)
  #text(size: 21pt, weight: "bold")[{title}]
  #v(0.22in)
  #text(size: 11.5pt, fill: rgb("#CBD5E1"))[{subtitle}]
  #v(1fr)
  #line(length: 32%, stroke: 0.8pt + rgb("#64748B"))
  #v(0.2in)
  #text(size: 13pt, weight: "bold", fill: rgb("{accent_hex}"))[{author}]
  #v(0.1in)
  #text(size: 9pt, fill: rgb("#94A3B8"))[{publisher}]
  #v(0.25in)
]
"""
    ebook_typ_path = typ_dir / "cover-ebook.typ"
    ebook_pdf_path = typ_dir / "cover-ebook-temp.pdf"
    ebook_png_path = dist_dir / "cover-ebook.png"
    ebook_typ_path.write_text(ebook_typ, encoding="utf-8")
    subprocess.run(["typst", "compile", str(ebook_typ_path), str(ebook_pdf_path)], check=True)

    doc = pymupdf.open(str(ebook_pdf_path))
    pix = doc[0].get_pixmap(dpi=320, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    img = img.resize((1600, 2560), Image.Resampling.LANCZOS)
    img.save(ebook_png_path, "PNG")
    doc.close()
    ebook_pdf_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute KDP/IngramSpark spine geometry & render RTL/LTR book covers.")
    parser.add_argument("--project", required=True, help="Path to Book Studio project root.")
    parser.add_argument("--blurb", default="", help="Back-cover blurb text.")
    parser.add_argument("--pages", type=int, default=0, help="Explicit page count ONLY when --spec-only is used.")
    parser.add_argument("--spec-only", action="store_true", help="Calculate dist/cover-spec.json without rendering PDFs.")
    args = parser.parse_args()

    root = Path(args.project).resolve()
    cfg = json.loads((root / "book.config.json").read_text(encoding="utf-8"))
    dist = root / "dist"
    dist.mkdir(parents=True, exist_ok=True)

    interior_pdf = dist / "interior-paperback.pdf"
    if args.spec_only and args.pages > 0:
        page_count = args.pages
    else:
        if not interior_pdf.is_file():
            raise SystemExit(
                f"Error: {interior_pdf} not found. Run book-typesetter (build_interior.py) FIRST so cover spine uses actual page count!"
            )
        with pikepdf.open(interior_pdf) as pdf:
            page_count = len(pdf.pages)

    if page_count % 2 != 0:
        raise SystemExit(f"Error: interior PDF has odd page count ({page_count}); print books must be even.")

    spec = compute_cover_geometry(cfg, page_count)
    spec_path = dist / "cover-spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    default_blurb = (
        f"{cfg.get('title', '')} — {cfg.get('subtitle', '')}. تأليف: {cfg.get('author', '')}."
        if spec["language"] == "ar"
        else f"{cfg.get('title', '')} — {cfg.get('subtitle', '')}. Written by {cfg.get('author', '')}."
    )
    blurb = args.blurb.strip() or cfg.get("back_cover_blurb", "") or default_blurb

    if not args.spec_only:
        render_proof_svg(cfg, spec, blurb, dist / "cover-wrap-proof.svg")
        render_press_cover_and_ebook_via_typst(cfg, spec, blurb, dist)

    spine_note = "Spine text ENABLED (>=79pp)" if spec["spine_text_allowed"] else "Spine text SUPPRESSED (<79pp KDP rule)"
    side_note = "RTL Mirrored (Front LEFT / Back RIGHT)" if spec["direction"] == "rtl" else "LTR Standard (Back LEFT / Front RIGHT)"
    print(
        f"[OK] Cover wrap built for {page_count}pp ({spec['paper_stock']}): "
        f"{spec['full_width_in']}\" x {spec['full_height_in']}\" (spine={spec['spine_width_in']}\", {spec['spine_width_mm']}mm) | "
        f"{side_note} | {spine_note}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
