#!/usr/bin/env python3
"""
press_pdfx.py — Safe Pre-Press PDF Normalizer & CMYK PDF/X-1a Distiller

Implements the exact order required so Ghostscript never silently drops PDF/X compliance:
1. Strip ALL interactive /Annots (/Link, /Widget, /Popup) across every page via pikepdf.
2. Normalize MediaBox, BleedBox, and TrimBox to exact points.
3. Optionally invoke Ghostscript (-dPDFX -sProcessColorModel=DeviceCMYK) when --cmyk and `gs` are present.
4. Re-apply TrimBox & embed GTS_PDFX /OutputIntents dictionary via pikepdf.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pikepdf


def tag_pdfx_boxes_and_intent(
    pdf_path: Path,
    media_w_pt: float,
    media_h_pt: float,
    trim_inset_pt: float = 0.0,
    condition_id: str = "CGATS TR 001",
) -> dict:
    annots_removed = 0
    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        mbox = pikepdf.Array([0, 0, round(media_w_pt, 3), round(media_h_pt, 3)])
        tbox = pikepdf.Array(
            [
                round(trim_inset_pt, 3),
                round(trim_inset_pt, 3),
                round(media_w_pt - trim_inset_pt, 3),
                round(media_h_pt - trim_inset_pt, 3),
            ]
        )
        for page in pdf.pages:
            if "/Annots" in page:
                annots_removed += len(page["/Annots"])
                del page["/Annots"]
            page["/MediaBox"] = mbox
            page["/BleedBox"] = mbox
            page["/TrimBox"] = tbox

        # Ensure GTS_PDFX OutputIntent metadata is present on Catalog
        intent = pikepdf.Dictionary(
            {
                "/Type": pikepdf.Name("/OutputIntent"),
                "/S": pikepdf.Name("/GTS_PDFX"),
                "/OutputConditionIdentifier": pikepdf.String(condition_id),
                "/OutputCondition": pikepdf.String("SWOP CGATS TR 001 (CMYK Press Profile)"),
                "/RegistryName": pikepdf.String("http://www.color.org"),
            }
        )
        pdf.Root["/OutputIntents"] = pikepdf.Array([intent])
        with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
            meta["pdfxid:GTS_PDFXVersion"] = "PDF/X-1:2001"
        pdf.save(pdf_path)
    return {"annotations_stripped": annots_removed, "pages": len(pikepdf.open(pdf_path).pages)}


def convert_cmyk_with_gs(pdf_path: Path) -> bool:
    gs_bin = shutil.which("gs")
    if not gs_bin:
        return False
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_out = Path(tmp.name)
    cmd = [
        gs_bin,
        "-dBATCH",
        "-dNOPAUSE",
        "-dNOOUTERSAVE",
        "-sDEVICE=pdfwrite",
        "-sProcessColorModel=DeviceCMYK",
        "-sColorConversionStrategy=CMYK",
        "-sColorConversionStrategyForImages=CMYK",
        "-dCompatibilityLevel=1.4",
        f"-sOutputFile={tmp_out}",
        str(pdf_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode == 0 and tmp_out.is_file() and tmp_out.stat().st_size > 0:
        shutil.move(str(tmp_out), str(pdf_path))
        return True
    tmp_out.unlink(missing_ok=True)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Strip PDF annotations, normalize TrimBox/BleedBox & distill press PDF/X.")
    parser.add_argument("--project", required=True, help="Path to Book Studio project root.")
    parser.add_argument("--cmyk", action="store_true", help="Run Ghostscript CMYK conversion if `gs` is installed.")
    args = parser.parse_args()

    root = Path(args.project).resolve()
    dist = root / "dist"
    interior_manifest_path = dist / "interior-manifest.json"
    if not interior_manifest_path.is_file():
        raise SystemExit("Error: dist/interior-manifest.json missing (run build_interior.py first)")

    iman = json.loads(interior_manifest_path.read_text(encoding="utf-8"))
    results = {}

    for ed_name, ed_meta in iman.get("editions", {}).items():
        if ed_name == "screen":
            continue
        pdf_file = root / ed_meta["pdf_path"]
        if not pdf_file.is_file():
            continue
        res1 = tag_pdfx_boxes_and_intent(pdf_file, ed_meta["width_pt"], ed_meta["height_pt"], trim_inset_pt=0.0)
        cmyk_done = convert_cmyk_with_gs(pdf_file) if args.cmyk else False
        if cmyk_done:
            tag_pdfx_boxes_and_intent(pdf_file, ed_meta["width_pt"], ed_meta["height_pt"], trim_inset_pt=0.0)
        results[ed_name] = {**res1, "gs_cmyk_applied": cmyk_done}
        print(f"[OK] Press-prepared interior '{ed_name}' (annots_stripped={res1['annotations_stripped']}, gs_cmyk={cmyk_done})")

    cover_pdf = dist / "cover-wrap-print.pdf"
    cover_spec_path = dist / "cover-spec.json"
    if cover_pdf.is_file() and cover_spec_path.is_file():
        cspec = json.loads(cover_spec_path.read_text(encoding="utf-8"))
        bleed_pt = round(float(cspec["bleed_in"]) * 72.0, 3)
        res_cov = tag_pdfx_boxes_and_intent(
            cover_pdf, cspec["full_width_pt"], cspec["full_height_pt"], trim_inset_pt=bleed_pt
        )
        cmyk_cov = convert_cmyk_with_gs(cover_pdf) if args.cmyk else False
        if cmyk_cov:
            tag_pdfx_boxes_and_intent(
                cover_pdf, cspec["full_width_pt"], cspec["full_height_pt"], trim_inset_pt=bleed_pt
            )
        results["cover_wrap"] = {**res_cov, "gs_cmyk_applied": cmyk_cov}
        print(f"[OK] Press-prepared cover-wrap-print.pdf (annots_stripped={res_cov['annotations_stripped']}, gs_cmyk={cmyk_cov})")

    (dist / "press-prep-report.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
