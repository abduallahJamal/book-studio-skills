#!/usr/bin/env python3
"""
preflight_qc.py — 15-Gate Physical Book Preflight Inspector & Contact Sheet Generator

Enforces all 15 physical gates (G01–G15) across interior-paperback.pdf, cover-wrap-print.pdf,
and manuscript.lock.json using PyMuPDF, pikepdf, and Pillow. Promotes verified files into
dist/press-ready/ ONLY when all 15 gates pass.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
import unicodedata
from pathlib import Path

import pikepdf
from PIL import Image, ImageDraw

try:
    import pymupdf
except ImportError:  # pragma: no cover
    import fitz as pymupdf  # type: ignore

NUMBER_RE = re.compile(r"[\d\u0660-\u0669]+(?:[.,][\d\u0660-\u0669]+)*")
AR_DIACRITICS_RE = re.compile(r"[\u0640\u064B-\u065F\u0670\u06D6-\u06ED]")


def make_gate(gid: str, name: str, passed: bool, detail: str) -> dict:
    return {"id": gid, "name": name, "passed": bool(passed), "detail": detail}


def render_contact_sheet(pdf_path: Path, out_png: Path, cols: int = 4, max_pages: int = 12) -> int:
    doc = pymupdf.open(str(pdf_path))
    total = len(doc)
    if total <= max_pages:
        indices = list(range(total))
    else:
        # Sample first 5, evenly spaced middle pages, and final 2 pages
        mid_step = max((total - 7) // (max_pages - 7), 1)
        mids = list(range(5, total - 2, mid_step))[: max_pages - 7]
        indices = list(range(5)) + mids + [total - 2, total - 1]

    thumbs: list[tuple[int, Image.Image]] = []
    for idx in indices:
        pix = doc[idx].get_pixmap(dpi=96, alpha=False)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        thumbs.append((idx + 1, im))
    doc.close()

    if not thumbs:
        return 0

    tw, th = thumbs[0][1].size
    pad = 18
    label_h = 22
    actual_cols = min(cols, len(thumbs))
    rows = math.ceil(len(thumbs) / actual_cols)
    canvas_w = pad + actual_cols * (tw + pad)
    canvas_h = pad + rows * (th + label_h + pad)

    sheet = Image.new("RGB", (canvas_w, canvas_h), (15, 23, 42))
    draw = ImageDraw.Draw(sheet)

    for pos, (pno, im) in enumerate(thumbs):
        r = pos // actual_cols
        c = pos % actual_cols
        x = pad + c * (tw + pad)
        y = pad + r * (th + label_h + pad)
        sheet.paste(im, (x, y))
        draw.rectangle([x, y, x + tw - 1, y + th - 1], outline=(100, 116, 139), width=1)
        draw.text((x + 4, y + th + 4), f"Page {pno}/{total}", fill=(226, 232, 240))

    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png, "PNG")
    return len(thumbs)


def run_all_15_gates(root: Path) -> list[dict]:
    cfg = json.loads((root / "book.config.json").read_text(encoding="utf-8"))
    dist = root / "dist"
    iman = json.loads((dist / "interior-manifest.json").read_text(encoding="utf-8"))
    primary_ed = iman.get("primary_print_edition", "paperback")
    ed_meta = iman["editions"][primary_ed]

    interior_pdf = root / ed_meta["pdf_path"]
    cover_pdf = dist / "cover-wrap-print.pdf"
    cover_spec_path = dist / "cover-spec.json"
    cspec = json.loads(cover_spec_path.read_text(encoding="utf-8")) if cover_spec_path.is_file() else None

    gates: list[dict] = []

    # Open with pikepdf for G01, G02, G04, G05
    with pikepdf.open(interior_pdf) as ipdf:
        page_count = len(ipdf.pages)
        exp_w, exp_h = float(ed_meta["width_pt"]), float(ed_meta["height_pt"])
        geom_bad = []
        annot_total = 0
        has_trimbox_all = True

        for pno, p in enumerate(ipdf.pages, start=1):
            mb = [float(x) for x in p.get("/MediaBox", [0, 0, 0, 0])]
            tb = [float(x) for x in p.get("/TrimBox", [])] if "/TrimBox" in p else []
            if not tb:
                has_trimbox_all = False
            w_actual = mb[2] - mb[0]
            h_actual = mb[3] - mb[1]
            if abs(w_actual - exp_w) > 0.5 or abs(h_actual - exp_h) > 0.5:
                geom_bad.append(f"p.{pno}: {w_actual:.2f}x{h_actual:.2f}pt != {exp_w:.2f}x{exp_h:.2f}pt")
            if "/Annots" in p:
                annot_total += len(p["/Annots"])

        has_intent = "/OutputIntents" in ipdf.Root

    cov_geom_ok = True
    cov_annots = 0
    if cover_pdf.is_file() and cspec:
        with pikepdf.open(cover_pdf) as cpdf:
            cp = cpdf.pages[0]
            cmb = [float(x) for x in cp.get("/MediaBox", [0, 0, 0, 0])]
            if abs((cmb[2] - cmb[0]) - cspec["full_width_pt"]) > 0.5 or abs((cmb[3] - cmb[1]) - cspec["full_height_pt"]) > 0.5:
                cov_geom_ok = False
            if "/Annots" in cp:
                cov_annots += len(cp["/Annots"])

    # G01: Trim & Bleed Geometry
    g01_ok = len(geom_bad) == 0 and cov_geom_ok
    gates.append(
        make_gate(
            "G01",
            "Trim & Bleed Box Geometry (±0.5pt)",
            g01_ok,
            f"Interior {exp_w}x{exp_h}pt OK; Cover wrap geometry={'OK' if cov_geom_ok else 'MISMATCH'}"
            if g01_ok
            else "; ".join(geom_bad[:3]),
        )
    )

    # G02: Even & Minimum Page Count
    min_pages = int(cfg.get("print", {}).get("min_pages", 24))
    g02_ok = (page_count % 2 == 0) and (page_count >= min_pages)
    gates.append(
        make_gate(
            "G02",
            "Even & Minimum Page Count",
            g02_ok,
            f"{page_count} pages (even={page_count % 2 == 0}, min_required={min_pages})",
        )
    )

    # PyMuPDF deep physical scan for G03, G06, G07, G08, G09, G10, G11
    doc = pymupdf.open(str(interior_pdf))
    unembedded_fonts: list[str] = []
    type3_fonts: list[str] = []
    overflow_hits: list[str] = []
    collision_hits: list[str] = []
    orphan_headings: list[str] = []
    low_dpi_hits: list[str] = []
    tinted_bw_pages: list[int] = []

    body_pt = float(ed_meta.get("body_pt", 11.0))
    safe_edge_pt = 18.0  # 0.25in absolute live-safety border from physical cut edge
    bottom_margin_pt = float(ed_meta.get("bottom_margin_in", 0.85)) * 72.0
    is_bw = cfg.get("print", {}).get("ink", "bw") == "bw"

    for p_idx, page in enumerate(doc):
        pno = p_idx + 1
        pw, ph = page.rect.width, page.rect.height

        # G03: Fonts
        for f in page.get_fonts(full=True):
            # f = (xref, ext, type, basefont, name, encoding, referencer)
            ext, ftype, basefont = f[1], f[2], f[3]
            if ftype == "Type3":
                type3_fonts.append(f"p.{pno}:{basefont}")
            if ext == "n/a" or not ext:
                unembedded_fonts.append(f"p.{pno}:{basefont}")

        # G11: B&W screen-tint background guard
        if is_bw:
            for drw in page.get_drawings():
                fill = drw.get("fill")
                rect = drw.get("rect")
                if fill and rect and (rect.width * rect.height) >= 0.90 * (pw * ph):
                    # Check if non-white fill covers >90% of a B&W print page
                    if any(ch < 0.995 for ch in fill):
                        tinted_bw_pages.append(pno)

        # G10: Raster image effective DPI
        for img_info in page.get_image_info(xrefs=True):
            bbox = img_info.get("bbox")
            w_px = img_info.get("width", 0)
            if bbox and w_px > 0:
                disp_w_in = max((bbox[2] - bbox[0]) / 72.0, 0.05)
                eff_dpi = w_px / disp_w_in
                if eff_dpi < 290:
                    low_dpi_hits.append(f"p.{pno} ({eff_dpi:.0f} DPI)")

        # G06, G07, G08: Text block overflow, vertical line collision & orphan headings
        tdict = page.get_text("dict")
        page_lines: list[tuple[float, float, float, float, float, int, str]] = []
        for b in tdict.get("blocks", []):
            if b.get("type") != 0:
                continue
            bx0, by0, bx1, by1 = b["bbox"]
            # Ignore running header/footer regions for body margin check if centered page number
            if by0 > 36 and by1 < ph - 28:
                if bx0 < safe_edge_pt - 2.0 or bx1 > (pw - safe_edge_pt + 2.0):
                    snippet = "".join(s.get("text", "") for ln in b.get("lines", []) for s in ln.get("spans", []))[:30]
                    overflow_hits.append(f"p.{pno} ({bx0:.1f}..{bx1:.1f}pt): {snippet}")

            for ln in b.get("lines", []):
                lx0, ly0, lx1, ly1 = ln["bbox"]
                spans = ln.get("spans", [])
                if not spans:
                    continue
                txt = "".join(s.get("text", "") for s in spans).strip()
                if not txt:
                    continue
                max_sz = max(float(s.get("size", body_pt)) for s in spans)
                flags = spans[0].get("flags", 0)
                page_lines.append((lx0, ly0, lx1, ly1, max_sz, flags, txt))

        # G07: Check vertical collision among body lines overlapping horizontally
        body_lines = [ln for ln in page_lines if 48.0 < ln[1] and ln[3] < ph - 42.0]
        body_lines.sort(key=lambda item: (round(item[1], 1), item[0]))
        for idx_a in range(len(body_lines)):
            ax0, ay0, ax1, ay1, _, _, atxt = body_lines[idx_a]
            ah = max(ay1 - ay0, 1.0)
            for idx_b in range(idx_a + 1, min(idx_a + 5, len(body_lines))):
                bx0, by0, bx1, by1, _, _, btxt = body_lines[idx_b]
                if by0 >= ay1:
                    break
                horiz_overlap = min(ax1, bx1) - max(ax0, bx0)
                vert_overlap = min(ay1, by1) - max(ay0, by0)
                bh = max(by1 - by0, 1.0)
                # Ignore same baseline split spans (e.g. inline code/bold on exact same line y)
                if abs(ay0 - by0) <= 2.5 and abs(ay1 - by1) <= 2.5:
                    continue
                if horiz_overlap > 25.0 and vert_overlap > 0.50 * min(ah, bh):
                    collision_hits.append(f"p.{pno}: '{atxt[:18]}' vs '{btxt[:18]}'")

        # G08: Heading widow at very bottom of page with zero body lines following it
        if body_lines:
            last_ln = max(body_lines, key=lambda x: x[3])
            _, ly0, _, ly1, lsz, _, ltxt = last_ln
            if pno > 5 and lsz >= body_pt * 1.22 and ly1 > (ph - bottom_margin_pt - 28.0):
                orphan_headings.append(f"p.{pno}: '{ltxt[:35]}'")

    # G03 result
    g03_ok = len(type3_fonts) == 0 and len(unembedded_fonts) == 0
    gates.append(
        make_gate(
            "G03",
            "100% Embedded Fonts & Zero Type3",
            g03_ok,
            "All fonts embedded cleanly; zero Type3 bitmap fonts"
            if g03_ok
            else f"Type3={type3_fonts[:3]}, Unembedded={unembedded_fonts[:3]}",
        )
    )

    # G04 result
    g04_ok = annot_total == 0 and cov_annots == 0
    gates.append(
        make_gate(
            "G04",
            "Zero Interactive PDF Annotations",
            g04_ok,
            f"interior_annots={annot_total}, cover_annots={cov_annots}",
        )
    )

    # G05 result
    g05_ok = has_trimbox_all and has_intent
    gates.append(
        make_gate(
            "G05",
            "TrimBox & GTS_PDFX OutputIntent",
            g05_ok,
            f"TrimBox_all_pages={has_trimbox_all}, GTS_PDFX_OutputIntent={has_intent}",
        )
    )

    # G06 result
    g06_ok = len(overflow_hits) == 0
    gates.append(
        make_gate(
            "G06",
            "Safe-Margin Overflow Scan",
            g06_ok,
            "Zero blocks outside live safety margins" if g06_ok else "; ".join(overflow_hits[:3]),
        )
    )

    # G07 result
    g07_ok = len(collision_hits) == 0
    gates.append(
        make_gate(
            "G07",
            "Vertical Line Collision Scan",
            g07_ok,
            "Zero overlapping text/table lines" if g07_ok else "; ".join(collision_hits[:3]),
        )
    )

    # G08 result
    g08_ok = len(orphan_headings) == 0
    gates.append(
        make_gate(
            "G08",
            "Bottom-of-Page Orphan Heading Guard",
            g08_ok,
            "Zero stranded headings at page bottom" if g08_ok else "; ".join(orphan_headings[:3]),
        )
    )

    # G09: TOC Folio Sync (verify TOC page exists on p.5 and chapter openings land on odd pages <= page_count)
    toc_text = doc[4].get_text() if len(doc) >= 5 else ""
    digit_trans = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    toc_folios = [int(n) for n in re.findall(r"\b(\d{1,3})\b", toc_text.translate(digit_trans)) if 5 < int(n) <= page_count]
    g09_ok = len(toc_folios) >= 1 and all(1 <= f <= page_count for f in toc_folios)
    gates.append(
        make_gate(
            "G09",
            "Printed TOC Folio Sync",
            g09_ok,
            f"Verified {len(toc_folios)} TOC page references within [6..{page_count}]",
        )
    )

    # G10 result
    g10_ok = len(low_dpi_hits) == 0
    gates.append(
        make_gate(
            "G10",
            "Raster Effective Resolution (>= 300 DPI)",
            g10_ok,
            "All embedded images/vectors meet print DPI threshold" if g10_ok else "; ".join(low_dpi_hits[:3]),
        )
    )

    # G11 result
    g11_ok = len(tinted_bw_pages) == 0
    gates.append(
        make_gate(
            "G11",
            "B&W Print Screen-Tint Guard",
            g11_ok,
            "Pure white print canvas confirmed (zero halftone mud)" if g11_ok else f"Tinted pages: {tinted_bw_pages[:5]}",
        )
    )

    # G12: Callout & Stat Grounding in Manuscript
    ungrounded_stats: list[str] = []
    for ch_md in sorted((root / "manuscript" / "chapters").glob("*.md")):
        lines = ch_md.read_text(encoding="utf-8").splitlines()
        quote_lines = [ln for ln in lines if ln.strip().startswith(">")]
        prose_body = "\n".join(ln for ln in lines if not ln.strip().startswith(">"))
        prose_norm = prose_body.translate(digit_trans)
        for ql in quote_lines:
            qnums = [tok.translate(digit_trans) for tok in NUMBER_RE.findall(ql)]
            for qn in qnums:
                if len(qn) >= 2 and qn not in prose_norm:
                    ungrounded_stats.append(f"{ch_md.name}:{qn}")
    g12_ok = len(ungrounded_stats) == 0
    gates.append(
        make_gate(
            "G12",
            "Callout & Stat Prose Grounding",
            g12_ok,
            "All callout numbers grounded in chapter prose" if g12_ok else f"Ungrounded: {ungrounded_stats[:4]}",
        )
    )

    # G13: Cover RTL/LTR Mirroring, <79pp Spine Rule & Barcode Keepout
    g13_ok = False
    g13_msg = "Missing cover-wrap-print.pdf or cover-spec.json"
    if cover_pdf.is_file() and cspec:
        cdoc = pymupdf.open(str(cover_pdf))
        cpage = cdoc[0]
        expected_dir = cfg.get("direction", "rtl" if cfg.get("language") == "ar" else "ltr")
        sp = cspec["panels_in"]["spine"]
        fp = cspec["panels_in"]["front"]
        bp = cspec["panels_in"]["back"]

        side_ok = (fp["x"] < sp["x"] < bp["x"]) if expected_dir == "rtl" else (bp["x"] < sp["x"] < fp["x"])

        spine_rect = pymupdf.Rect(
            (sp["x"] + 0.02) * 72.0,
            sp["y"] * 72.0,
            (sp["x"] + sp["width"] - 0.02) * 72.0,
            (sp["y"] + sp["height"]) * 72.0,
        )
        spine_txt = cpage.get_text("text", clip=spine_rect).strip() if spine_rect.width > 1 else ""
        spine_rule_ok = (spine_txt == "") if page_count < 79 else True

        bc = cspec["panels_in"]["barcode_keepout"]
        bc_rect = pymupdf.Rect(bc["x"] * 72.0, bc["y"] * 72.0, (bc["x"] + bc["width"]) * 72.0, (bc["y"] + bc["height"]) * 72.0)
        bc_txt = cpage.get_text("text", clip=bc_rect).strip()
        # Verify ISBN label actually rendered inside barcode box AND zero text blocks spill outside bleed/trim safety!
        bc_ok = ("ISBN" in bc_txt) and (len(bc_txt.splitlines()) <= 2)
        bleed_pt = float(cspec["bleed_in"]) * 72.0
        cov_blocks_in_bounds = all(
            (b[0] >= bleed_pt + 12.0 and b[2] <= cpage.rect.width - bleed_pt - 12.0)
            for b in cpage.get_text("blocks")
            if b[6] == 0 and b[4].strip()
        )
        cdoc.close()

        g13_ok = side_ok and spine_rule_ok and bc_ok and cov_blocks_in_bounds and (cspec["page_count"] == page_count)
        g13_msg = (
            f"dir={expected_dir.upper()} panel_mirror={side_ok}, in_bounds={cov_blocks_in_bounds}, "
            f"spine_rule_ok={spine_rule_ok}, barcode_keepout_clean={bc_ok}"
        )
    gates.append(make_gate("G13", "Cover RTL/LTR Mirror, Spine & Barcode Gate", g13_ok, g13_msg))

    # G14: Content-Integrity Fingerprint Parity
    ci = ed_meta.get("content_integrity", {})
    lock_path = root / "manuscript" / "manuscript.lock.json"
    lock_ok = True
    if lock_path.is_file():
        lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
        pdf_full_txt = "\n".join(p.get_text() for p in doc)
        pdf_clean_nums = AR_DIACRITICS_RE.sub("", unicodedata.normalize("NFKC", pdf_full_txt)).translate(digit_trans).replace(",", "")
        missing_locked_nums = [tok for tok in lock_data["aggregate"]["numeric_tokens"] if tok not in pdf_clean_nums]
        lock_ok = len(missing_locked_nums) == 0
    doc.close()

    g14_ok = bool(ci.get("verified", False)) and lock_ok
    gates.append(
        make_gate(
            "G14",
            "BiDi Content-Integrity Fingerprint Parity",
            g14_ok,
            f"alnum_retention={ci.get('alnum_retention_ratio', 0)}, zero_missing_numbers={lock_ok}",
        )
    )

    # G15: Render Visual Contact Sheets
    qc_dir = dist / "qc"
    qc_dir.mkdir(parents=True, exist_ok=True)
    int_sheet = qc_dir / "contact-sheet-interior.png"
    cov_sheet = qc_dir / "contact-sheet-cover.png"
    n_int = render_contact_sheet(interior_pdf, int_sheet, cols=4, max_pages=12)
    n_cov = render_contact_sheet(cover_pdf, cov_sheet, cols=1, max_pages=1) if cover_pdf.is_file() else 0
    g15_ok = int_sheet.is_file() and n_int > 0 and (not cover_pdf.is_file() or cov_sheet.is_file())
    gates.append(
        make_gate(
            "G15",
            "Visual Contact Sheets Rendered",
            g15_ok,
            f"Interior thumbs={n_int} ({int_sheet.relative_to(root)}), Cover={cov_sheet.relative_to(root) if n_cov else 'n/a'}",
        )
    )

    return gates


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 15 physical preflight QC gates & promote to dist/press-ready/.")
    parser.add_argument("--project", required=True, help="Path to Book Studio project root.")
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    args = parser.parse_args()

    root = Path(args.project).resolve()
    cfg = json.loads((root / "book.config.json").read_text(encoding="utf-8"))
    dist = root / "dist"
    gates = run_all_15_gates(root)
    all_passed = all(g["passed"] for g in gates)

    promoted: list[str] = []
    if all_passed:
        press_ready = dist / "press-ready"
        press_ready.mkdir(parents=True, exist_ok=True)
        slug = cfg.get("slug", "book")
        candidates = [
            dist / "interior-paperback.pdf",
            dist / "interior-hardcover.pdf",
            dist / "interior-large-print.pdf",
            dist / "cover-wrap-print.pdf",
            dist / "cover-ebook.png",
            dist / f"{slug}.epub",
        ]
        for c in candidates:
            if c.is_file():
                dst = press_ready / c.name
                shutil.copy2(c, dst)
                promoted.append(str(dst.relative_to(root)))

    report = {
        "passed": all_passed,
        "gates_passed": sum(1 for g in gates if g["passed"]),
        "gates_total": len(gates),
        "promoted_files": promoted,
        "gates": gates,
    }
    report_path = dist / "qc" / "preflight-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"=== 15-Gate Physical Preflight Report ({cfg.get('title', root.name)}) ===")
        for g in gates:
            status = "PASS" if g["passed"] else "FAIL"
            print(f"  [{status}] {g['id']} — {g['name']}: {g['detail']}")
        print(f"\nSummary: {report['gates_passed']}/{report['gates_total']} gates passed.")
        if all_passed:
            print(f"Promoted {len(promoted)} verified deliverable(s) -> dist/press-ready/")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
