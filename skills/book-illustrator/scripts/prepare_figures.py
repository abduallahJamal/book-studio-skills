#!/usr/bin/env python3
"""
prepare_figures.py — SVG Print Hygiene Validator, 300-DPI Auditor, Chroma-Key Cleaner
& Pure-Vector SVG Pipeline Renderer (zero <foreignObject>).
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

TRIM_WIDTH_IN = {
    "5x8": 5.0,
    "5.25x8": 5.25,
    "5.5x8.5": 5.5,
    "6x9": 6.0,
    "7x10": 7.0,
    "8.5x11": 8.5,
    "a5": 5.827,
    "b5": 6.929,
}


def render_pipeline_svg(spec: dict, out_path: Path) -> None:
    """Render a clean, pure-SVG horizontal/vertical architecture diagram (zero foreignObject)."""
    steps = spec.get("steps", [])
    direction = spec.get("direction", "ltr")
    title = spec.get("title", "")
    font_family = spec.get("font_family", "DejaVu Sans, Arial, sans-serif")

    n = max(len(steps), 1)
    width = 840
    box_h = 62
    gap_y = 26
    top_pad = 64 if title else 24
    height = top_pad + n * box_h + max(n - 1, 0) * gap_y + 28

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        f'  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="12" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.5"/>',
    ]
    if title:
        lines.append(
            f'  <text x="{width // 2}" y="38" text-anchor="middle" font-family="{html.escape(font_family)}" '
            f'font-size="18" font-weight="bold" fill="#0F172A">{html.escape(title)}</text>'
        )

    for idx, step in enumerate(steps):
        y = top_pad + idx * (box_h + gap_y)
        label = html.escape(str(step.get("label", f"Stage {idx + 1}")))
        detail = html.escape(str(step.get("detail", "")))
        badge = html.escape(str(step.get("badge", f"0{idx + 1}")))

        lines.append(f'  <rect x="48" y="{y}" width="{width - 96}" height="{box_h}" rx="8" fill="#F8FAFC" stroke="#334155" stroke-width="1.5"/>')
        if direction == "rtl":
            badge_x = width - 92
            text_x = width - 122
            anchor = "end"
        else:
            badge_x = 64
            text_x = 122
            anchor = "start"

        lines.append(f'  <rect x="{badge_x - (14 if direction == "rtl" else 0)}" y="{y + 13}" width="42" height="36" rx="6" fill="#0F172A"/>')
        lines.append(
            f'  <text x="{badge_x + (7 if direction == "rtl" else 21)}" y="{y + 36}" text-anchor="middle" '
            f'font-family="DejaVu Sans Mono, monospace" font-size="13" font-weight="bold" fill="#FFFFFF">{badge}</text>'
        )
        lines.append(
            f'  <text x="{text_x}" y="{y + 27}" text-anchor="{anchor}" font-family="{html.escape(font_family)}" '
            f'font-size="15" font-weight="bold" fill="#0F172A">{label}</text>'
        )
        if detail:
            lines.append(
                f'  <text x="{text_x}" y="{y + 48}" text-anchor="{anchor}" font-family="{html.escape(font_family)}" '
                f'font-size="12" fill="#475569">{detail}</text>'
            )

        if idx < n - 1:
            ay1 = y + box_h + 3
            ay2 = y + box_h + gap_y - 5
            cx = width // 2
            lines.append(f'  <line x1="{cx}" y1="{ay1}" x2="{cx}" y2="{ay2}" stroke="#334155" stroke-width="2"/>')
            lines.append(f'  <polygon points="{cx - 5},{ay2 - 5} {cx + 5},{ay2 - 5} {cx},{ay2 + 2}" fill="#334155"/>')

    lines.append("</svg>\n")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def chroma_key_strip(src_path: Path, out_path: Path, threshold: int = 242) -> None:
    img = Image.open(src_path).convert("RGBA")
    pixels = img.getdata()
    cleaned = []
    for r, g, b, a in pixels:
        if r >= threshold and g >= threshold and b >= threshold:
            cleaned.append((255, 255, 255, 0))
        else:
            cleaned.append((r, g, b, a))
    img.putdata(cleaned)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")


def audit_svg(svg_path: Path) -> list[str]:
    issues: list[str] = []
    raw = svg_path.read_text(encoding="utf-8", errors="replace")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        return [f"Malformed XML in SVG: {exc}"]

    if "viewBox" not in root.attrib and ("width" not in root.attrib or "height" not in root.attrib):
        issues.append("SVG missing viewBox and explicit width/height")
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag == "foreignObject":
            issues.append("Banned <foreignObject> inside SVG (breaks Typst/PDF-X/EPUB text rendering)")
        for attr_val in el.attrib.values():
            if isinstance(attr_val, str) and ("http://" in attr_val or "https://" in attr_val):
                if not attr_val.startswith("http://www.w3.org/"):
                    issues.append(f"External network URL in SVG attribute: {attr_val}")
    return issues


def audit_raster(img_path: Path, content_width_in: float) -> tuple[dict, list[str]]:
    issues: list[str] = []
    with Image.open(img_path) as im:
        w, h = im.size
        mode = im.mode
    # Assume figure spans 75% of text block width by default unless icon/vignette
    assumed_print_in = max(content_width_in * 0.75, 2.0)
    eff_dpi = round(w / assumed_print_in, 1)
    if eff_dpi < 300:
        issues.append(f"Low print resolution: {w}x{h}px (~{eff_dpi} DPI at {assumed_print_in:.1f}in width; need >= 300 DPI)")
    return {"width_px": w, "height_px": h, "mode": mode, "estimated_dpi": eff_dpi}, issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit, clean, and render print-safe book figures.")
    parser.add_argument("--project", required=True, help="Path to Book Studio project root.")
    parser.add_argument("--render-pipeline-svg", default="", help="Optional JSON spec path to render a pure-SVG diagram.")
    parser.add_argument("--chroma-key", default="", help="Optional PNG path to strip white background.")
    parser.add_argument("--out", default="", help="Output path for --render-pipeline-svg or --chroma-key.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any figure has SVG or DPI errors.")
    args = parser.parse_args()

    root = Path(args.project).resolve()
    cfg = json.loads((root / "book.config.json").read_text(encoding="utf-8"))
    trim_key = cfg.get("print", {}).get("trim", "6x9").lower()
    trim_w = TRIM_WIDTH_IN.get(trim_key, 6.0)
    content_w = max(trim_w - 1.5, 3.5)

    if args.render_pipeline_svg:
        if not args.out:
            raise SystemExit("Error: --render-pipeline-svg requires --out FILE.svg")
        spec = json.loads(Path(args.render_pipeline_svg).read_text(encoding="utf-8"))
        render_pipeline_svg(spec, Path(args.out).resolve())
        print(f"[OK] Rendered pure-SVG diagram -> {args.out}")

    if args.chroma_key:
        if not args.out:
            raise SystemExit("Error: --chroma-key requires --out FILE.png")
        chroma_key_strip(Path(args.chroma_key).resolve(), Path(args.out).resolve())
        print(f"[OK] Stripped background -> {args.out}")

    fig_dir = root / "assets" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    manifest_items = []
    all_issues: list[str] = []
    seen_hashes: dict[str, str] = {}

    for path in sorted(fig_dir.iterdir()):
        if not path.is_file() or path.name.endswith(".json"):
            continue
        ext = path.suffix.lower()
        if ext not in {".svg", ".png", ".jpg", ".jpeg"}:
            continue

        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        issues: list[str] = []
        meta: dict = {"file": path.name, "sha256": digest, "type": ext.lstrip(".")}

        if digest in seen_hashes:
            issues.append(f"Duplicate SHA-256 snapshot collision with '{seen_hashes[digest]}'")
        else:
            seen_hashes[digest] = path.name

        if ext == ".svg":
            issues.extend(audit_svg(path))
        else:
            rmeta, rissues = audit_raster(path, content_w)
            meta.update(rmeta)
            issues.extend(rissues)

        meta["issues"] = issues
        manifest_items.append(meta)
        for iss in issues:
            all_issues.append(f"{path.name}: {iss}")

    manifest_path = fig_dir / "figures-manifest.json"
    manifest_path.write_text(
        json.dumps({"figure_count": len(manifest_items), "figures": manifest_items}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"[OK] Audited {len(manifest_items)} figure(s) -> {manifest_path.relative_to(root)}")
    if all_issues:
        for iss in all_issues:
            print(f"  [WARN] {iss}")
        if args.strict:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
