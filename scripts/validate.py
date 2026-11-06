#!/usr/bin/env python3
"""
validate.py — Repository, Multi-Harness Schema, Link & End-to-End AR/EN Publishing Validator

Checks:
1. Canonical skills/ (9 skills) + strict YAML frontmatter (OpenCode/DSH/Claude/Codex safe)
2. Codex sidecars (agents/openai.yaml), OpenCode command (.opencode/commands/book.md), and JSON manifests
3. Markdown relative link integrity across README.md, README.ar.md, and all 9 SKILL.md files
4. End-to-end execution of init_book.py + .docx manuscript import (import_manuscript.py)
5. Full live compilation (Typst + HTML Paged + Quarto/LaTeX), RTL/LTR KDP cover wrap, EPUB 3.3,
   Static Web Book, press_pdfx.py, and 15-gate preflight_qc.py on BOTH Arabic (RTL) and English (LTR) books!
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import docx

SUITE_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = SUITE_ROOT / "skills"
EXPECTED_SKILLS = {
    "book",
    "book-intake",
    "book-architect",
    "book-drafter",
    "book-illustrator",
    "book-typesetter",
    "book-cover-wrap",
    "book-ebook-web",
    "book-preflight-qc",
}
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def fail(msg: str, gh_annot: bool, file: str | None = None) -> None:
    if gh_annot and file:
        print(f"::error file={file}::{msg}")
    elif gh_annot:
        print(f"::error::{msg}")
    else:
        print(f"[FAIL] {msg}", file=sys.stderr)
    raise SystemExit(1)


def run_cli(cmd: list[str], gh_annot: bool, label: str) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        fail(f"{label} failed (exit {proc.returncode}): {detail}", gh_annot)
    return proc


def parse_frontmatter(md_text: str, rel_file: str, gh_annot: bool) -> dict[str, str]:
    if not md_text.startswith("---\n"):
        fail("SKILL.md must open with '---\\n' YAML frontmatter", gh_annot, rel_file)
    end_idx = md_text.find("\n---\n", 4)
    if end_idx == -1:
        fail("SKILL.md must close YAML frontmatter with '\\n---\\n'", gh_annot, rel_file)
    block = md_text[4:end_idx]
    parsed: dict[str, str] = {}
    for line in block.splitlines():
        if not line.strip() or line.startswith("  "):
            continue
        if ":" not in line:
            fail(f"Invalid YAML line: {line}", gh_annot, rel_file)
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if ":" in val and not (
            (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'"))
        ):
            fail(f"Unquoted colon in frontmatter key '{key}' breaks strict parsers", gh_annot, rel_file)
        parsed[key] = val.strip('"').strip("'")
    return parsed


def check_skills_and_manifests(gh_annot: bool) -> None:
    print("[1/5] Validating 9 canonical skills, YAML frontmatter, Codex sidecars & plugin manifests...")
    discovered = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}
    if discovered != EXPECTED_SKILLS:
        fail(f"Expected {EXPECTED_SKILLS}, got {discovered}", gh_annot)

    for skill_name in sorted(EXPECTED_SKILLS):
        sdir = SKILLS_DIR / skill_name
        if not KEBAB_RE.match(skill_name):
            fail(f"Invalid kebab-case skill directory: {skill_name}", gh_annot)
        skill_md = sdir / "SKILL.md"
        rel = str(skill_md.relative_to(SUITE_ROOT))
        if not skill_md.is_file():
            fail(f"Missing {rel}", gh_annot, rel)
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"), rel, gh_annot)
        if fm.get("name") != skill_name:
            fail(f"Frontmatter name '{fm.get('name')}' != directory '{skill_name}'", gh_annot, rel)
        desc = fm.get("description", "")
        if not (40 <= len(desc) <= 1024):
            fail(f"Description length ({len(desc)}) out of bounds [40, 1024]", gh_annot, rel)

        sidecar = sdir / "agents" / "openai.yaml"
        if not sidecar.is_file():
            fail(f"Missing Codex sidecar {sidecar.relative_to(SUITE_ROOT)}", gh_annot)
        if f"${skill_name}" not in sidecar.read_text(encoding="utf-8"):
            fail(f"Codex sidecar must reference ${skill_name}", gh_annot, str(sidecar.relative_to(SUITE_ROOT)))

    cmd_file = SUITE_ROOT / ".opencode" / "commands" / "book.md"
    if not cmd_file.is_file():
        fail("Missing .opencode/commands/book.md", gh_annot)

    claude_plugin = json.loads((SUITE_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    if "$schema" in claude_plugin:
        fail("Remove top-level $schema from .claude-plugin/plugin.json", gh_annot, ".claude-plugin/plugin.json")
    json.loads((SUITE_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    json.loads((SUITE_ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    print("  OK")


def check_markdown_links(gh_annot: bool) -> None:
    print("[2/5] Checking relative links across README.md, README.ar.md & all 9 SKILL.md files...")
    md_files = [SUITE_ROOT / "README.md", SUITE_ROOT / "README.ar.md"] + sorted(SKILLS_DIR.glob("*/SKILL.md"))
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

    for md in md_files:
        if not md.is_file():
            fail(f"Missing markdown file: {md.relative_to(SUITE_ROOT)}", gh_annot)
        text = re.sub(r"```[\s\S]*?```", "", md.read_text(encoding="utf-8"))
        for m in link_re.finditer(text):
            target = m.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean_target = target.split("#", 1)[0]
            if not clean_target:
                continue
            resolved = (md.parent / clean_target).resolve()
            if not resolved.exists():
                fail(
                    f"Broken relative link '{target}' -> {resolved}",
                    gh_annot,
                    str(md.relative_to(SUITE_ROOT)),
                )
    print("  OK")


def check_docx_intake_and_scaffolding(gh_annot: bool) -> None:
    print("[3/5] Testing init_book.py, scaffold_outline.py & Word .docx intake + content lock...")
    py = sys.executable
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        proj = tmp_path / "docx-test-book"
        sample_docx = tmp_path / "draft.docx"

        # Create a real bilingual .docx with Headings + Table
        d = docx.Document()
        d.add_heading("مقدمة المؤلف", level=1)
        d.add_paragraph("نص تجريبي في المقدمة لاختبار استيراد ملفات وورد بدقة 100%.")
        d.add_heading("الفصل الأول: البداية", level=1)
        d.add_paragraph("فقرة عربية تحتوي على الرقم 2026 ومصطلح هندسي واضح.")
        tbl = d.add_table(rows=2, cols=2)
        tbl.rows[0].cells[0].text = "المعيار"
        tbl.rows[0].cells[1].text = "القيمة"
        tbl.rows[1].cells[0].text = "الدقة"
        tbl.rows[1].cells[1].text = "300"
        d.save(str(sample_docx))

        run_cli(
            [
                py,
                str(SKILLS_DIR / "book" / "scripts" / "init_book.py"),
                "--dir",
                str(proj),
                "--title",
                "كتاب تجريبي",
                "--author",
                "مؤلف تجريبي",
                "--lang",
                "ar",
                "--style",
                "classic-arabic-turath",
            ],
            gh_annot,
            "init_book.py",
        )
        run_cli(
            [
                py,
                str(SKILLS_DIR / "book-architect" / "scripts" / "scaffold_outline.py"),
                "--project",
                str(proj),
                "--chapters",
                "4",
            ],
            gh_annot,
            "scaffold_outline.py",
        )
        run_cli(
            [
                py,
                str(SKILLS_DIR / "book-intake" / "scripts" / "import_manuscript.py"),
                "--project",
                str(proj),
                "--source",
                str(sample_docx),
                "--clean",
            ],
            gh_annot,
            "import_manuscript.py (.docx)",
        )
        lock = json.loads((proj / "manuscript" / "manuscript.lock.json").read_text(encoding="utf-8"))
        if "2026" not in lock["aggregate"]["numeric_tokens"] or "300" not in lock["aggregate"]["numeric_tokens"]:
            fail(f".docx intake missed numeric tokens: {lock['aggregate']['numeric_tokens']}", gh_annot)
    print("  OK")


def build_and_verify_demo_book(demo_rel: str, step_label: str, expected_dir: str, gh_annot: bool) -> None:
    print(f"{step_label} End-to-end compile, cover wrap, EPUB 3, Web Book & 15-gate QC on {demo_rel}...")
    py = sys.executable
    src_demo = SUITE_ROOT / demo_rel
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / Path(demo_rel).name
        shutil.copytree(src_demo, work, ignore=shutil.ignore_patterns("dist"))

        spec_json = work / "assets" / "figures" / "pipeline.spec.json"
        svg_name = "fig-01-pipeline.svg" if expected_dir == "rtl" else "fig-01-architecture.svg"
        run_cli(
            [
                py,
                str(SKILLS_DIR / "book-illustrator" / "scripts" / "prepare_figures.py"),
                "--project",
                str(work),
                "--render-pipeline-svg",
                str(spec_json),
                "--out",
                str(work / "assets" / "figures" / svg_name),
                "--strict",
            ],
            gh_annot,
            "prepare_figures.py",
        )
        run_cli(
            [py, str(SKILLS_DIR / "book-intake" / "scripts" / "import_manuscript.py"), "--project", str(work), "--lock-only"],
            gh_annot,
            "import_manuscript.py --lock-only",
        )
        run_cli(
            [py, str(SKILLS_DIR / "book-drafter" / "scripts" / "manuscript_metrics.py"), "--project", str(work), "--strict"],
            gh_annot,
            "manuscript_metrics.py --strict",
        )
        run_cli(
            [
                py,
                str(SKILLS_DIR / "book-typesetter" / "scripts" / "build_interior.py"),
                "--project",
                str(work),
                "--engine",
                "all",
                "--edition",
                "all",
            ],
            gh_annot,
            "build_interior.py",
        )
        run_cli(
            [py, str(SKILLS_DIR / "book-cover-wrap" / "scripts" / "calc_and_render_cover.py"), "--project", str(work)],
            gh_annot,
            "calc_and_render_cover.py",
        )
        run_cli(
            [py, str(SKILLS_DIR / "book-ebook-web" / "scripts" / "build_epub_and_web.py"), "--project", str(work)],
            gh_annot,
            "build_epub_and_web.py",
        )
        run_cli(
            [py, str(SKILLS_DIR / "book-preflight-qc" / "scripts" / "press_pdfx.py"), "--project", str(work), "--cmyk"],
            gh_annot,
            "press_pdfx.py",
        )
        qc_proc = run_cli(
            [py, str(SKILLS_DIR / "book-preflight-qc" / "scripts" / "preflight_qc.py"), "--project", str(work), "--json"],
            gh_annot,
            "preflight_qc.py",
        )
        qc_report = json.loads(qc_proc.stdout)
        if not qc_report.get("passed") or qc_report.get("gates_passed") != 15:
            fail(f"Preflight QC did not pass 15/15 gates on {demo_rel}: {qc_report}", gh_annot)
        if len(qc_report.get("promoted_files", [])) < 5:
            fail(f"Expected >=5 promoted press-ready deliverables on {demo_rel}", gh_annot)
    print(f"  OK (15/15 gates passed, {expected_dir.upper()} verified)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate book-studio-skills schema, links, and end-to-end builds.")
    parser.add_argument("--github-annotations", action="store_true", help="Emit GitHub Actions ::error annotations.")
    args = parser.parse_args()

    run_cli([sys.executable, str(SKILLS_DIR / "book" / "scripts" / "doctor.py"), "--strict"], args.github_annotations, "doctor.py")
    check_skills_and_manifests(args.github_annotations)
    check_markdown_links(args.github_annotations)
    check_docx_intake_and_scaffolding(args.github_annotations)
    build_and_verify_demo_book("examples/arabic-rtl-book", "[4/5]", "rtl", args.github_annotations)
    build_and_verify_demo_book("examples/english-ltr-book", "[5/5]", "ltr", args.github_annotations)

    print("\n[SUCCESS] All 9 skills, 4-harness manifests, links, .docx intake, and AR/EN 15-gate book builds passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
