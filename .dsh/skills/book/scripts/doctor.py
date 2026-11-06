#!/usr/bin/env python3
"""
doctor.py — Book Studio Environment & Toolchain Diagnostic CLI

Verifies:
- Required Python publishing libraries: pymupdf, pikepdf, Pillow, python-docx
- Typesetting & press binaries: typst (primary), gs (Ghostscript PDF/X), quarto/lualatex/xelatex, chromium
- Installed Arabic (RTL) and Latin (LTR) font families
"""

from __future__ import annotations

import argparse
import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

PYTHON_PACKAGES = [
    ("pymupdf", "PyMuPDF (physical PDF geometry, collision & contact-sheet engine)"),
    ("pikepdf", "pikepdf (annotation stripping, TrimBox/BleedBox & PDF/X-1a metadata)"),
    ("PIL", "Pillow (DPI verification, chroma-key transparency & cover rasterizing)"),
    ("docx", "python-docx (structured Word .docx manuscript & footnote importer)"),
]

BINARIES = [
    ("typst", True, "Primary fast PDF interior & full-wrap cover compiler"),
    ("gs", False, "Ghostscript CMYK PDF/X-1a press color conversion (optional; pikepdf handles box/annot prep)"),
    ("quarto", False, "Quarto CLI for LaTeX/Quarto academic export track (optional)"),
    ("lualatex", False, "LuaLaTeX engine for bilingual AR/EN TeX compilation (optional)"),
    ("chromium", False, "Headless Chromium for HTML/CSS Paged Media PDF export (optional)"),
]

ARABIC_FONT_CANDIDATES = [
    "Amiri",
    "Noto Naskh Arabic",
    "Noto Sans Arabic",
    "IBM Plex Sans Arabic",
    "Readex Pro",
    "Cairo",
    "DejaVu Sans",
]

LATIN_FONT_CANDIDATES = [
    "Libertinus Serif",
    "New Computer Modern",
    "EB Garamond",
    "Inter",
    "DejaVu Serif",
    "DejaVu Sans",
]


def detect_fonts() -> list[str]:
    found: set[str] = set()
    if shutil.which("typst"):
        proc = subprocess.run(["typst", "fonts"], capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                name = line.strip()
                if name:
                    found.add(name)
    if shutil.which("fc-list"):
        proc = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                for part in line.split(","):
                    name = part.strip()
                    if name:
                        found.add(name)
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose Book Studio Python packages, binaries, and AR/EN fonts.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON report.")
    parser.add_argument(
        "--install-python-deps",
        action="store_true",
        help="Automatically pip-install missing required Python packages.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any required Python package or typst binary is missing.",
    )
    args = parser.parse_args()

    if args.install_python_deps:
        req = Path(__file__).resolve().parents[3] / "requirements.txt"
        if req.is_file():
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req)], check=True)
        else:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pymupdf>=1.24.0", "pikepdf>=9.0.0", "Pillow>=10.0.0", "python-docx>=1.1.0"],
                check=True,
            )

    py_status = []
    missing_required = []

    for mod_name, label in PYTHON_PACKAGES:
        try:
            mod = importlib.import_module(mod_name)
            ver = getattr(mod, "__version__", "installed")
            py_status.append({"module": mod_name, "installed": True, "version": str(ver), "description": label})
        except ImportError:
            py_status.append({"module": mod_name, "installed": False, "version": None, "description": label})
            missing_required.append(mod_name)

    bin_status = []
    for cmd, required, label in BINARIES:
        path = shutil.which(cmd)
        ver = None
        if path:
            vproc = subprocess.run([cmd, "--version"], capture_output=True, text=True, check=False)
            first_line = (vproc.stdout or vproc.stderr or "").splitlines()
            ver = first_line[0].strip() if first_line else "found"
        elif required:
            missing_required.append(cmd)
        bin_status.append({"binary": cmd, "required": required, "path": path, "version": ver, "description": label})

    installed_fonts = detect_fonts()
    installed_lower = {f.lower(): f for f in installed_fonts}
    ar_available = [f for f in ARABIC_FONT_CANDIDATES if f.lower() in installed_lower]
    en_available = [f for f in LATIN_FONT_CANDIDATES if f.lower() in installed_lower]

    report = {
        "ok": len(missing_required) == 0 and len(ar_available) > 0 and len(en_available) > 0,
        "python_version": sys.version.split()[0],
        "python_packages": py_status,
        "binaries": bin_status,
        "fonts": {
            "total_detected": len(installed_fonts),
            "arabic_ready": ar_available,
            "latin_ready": en_available,
        },
        "missing_required": missing_required,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=== Book Studio Environment Doctor ===")
        print(f"Python: {report['python_version']}")
        print("\n[Python Publishing Libraries]")
        for item in py_status:
            mark = "OK" if item["installed"] else "MISSING"
            ver = f" ({item['version']})" if item["version"] else ""
            print(f"  [{mark}] {item['module']}{ver} — {item['description']}")
        print("\n[Typesetting & Press Binaries]")
        for item in bin_status:
            tag = "OK" if item["path"] else ("MISSING-REQ" if item["required"] else "OPTIONAL")
            ver = f" ({item['version']})" if item["version"] else ""
            print(f"  [{tag}] {item['binary']}{ver} — {item['description']}")
        print("\n[Font Coverage]")
        print(f"  Arabic (RTL) fonts available : {', '.join(ar_available) if ar_available else 'NONE'}")
        print(f"  Latin  (LTR) fonts available : {', '.join(en_available) if en_available else 'NONE'}")
        print(f"\nOverall Status: {'READY' if report['ok'] else 'INCOMPLETE'}")

    if args.strict and not report["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
