#!/usr/bin/env python3
"""
install.py — Cross-Platform Python Installer (Windows / macOS / Linux)

Installs all 9 book-studio-skills and the /book OpenCode command across
Claude Code, OpenAI Codex, OpenCode, and DeepSeek Harness.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent
SKILLS_SRC = SUITE_ROOT / "skills"
COMMAND_SRC = SUITE_ROOT / ".opencode" / "commands" / "book.md"
REQUIREMENTS_FILE = SUITE_ROOT / "requirements.txt"
SKILL_NAMES = [
    "book",
    "book-intake",
    "book-architect",
    "book-drafter",
    "book-illustrator",
    "book-typesetter",
    "book-cover-wrap",
    "book-ebook-web",
    "book-preflight-qc",
]


def resolve_targets(harnesses: list[str], scope: str, project_dir: Path) -> dict[str, list[Path]]:
    home = Path.home()
    dsh_home = Path(os.environ.get("DSH_HOME", str(home / ".dsh")))
    oc_home = Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))) / "opencode"

    mapping: dict[str, list[Path]] = {}
    selected = {"claude", "codex", "opencode", "dsh"} if "all" in harnesses else set(harnesses)

    if scope == "global":
        if "opencode" in selected:
            mapping["OpenCode (global)"] = [oc_home / "skills"]
        if "claude" in selected:
            mapping["Claude Code (global)"] = [home / ".claude" / "skills"]
        if "codex" in selected:
            mapping["OpenAI Codex (global)"] = [home / ".agents" / "skills", home / ".codex" / "skills"]
        if "dsh" in selected:
            mapping["DeepSeek Harness (global)"] = [dsh_home / "skills", home / ".agents" / "skills"]
    else:
        if "opencode" in selected:
            mapping["OpenCode (project)"] = [project_dir / ".opencode" / "skills"]
        if "claude" in selected:
            mapping["Claude Code (project)"] = [project_dir / ".claude" / "skills"]
        if "codex" in selected:
            mapping["OpenAI Codex (project)"] = [project_dir / ".agents" / "skills", project_dir / ".codex" / "skills"]
        if "dsh" in selected:
            mapping["DeepSeek Harness (project)"] = [project_dir / ".dsh" / "skills", project_dir / ".agents" / "skills"]

    return mapping


def install_skill_dir(src: Path, dst_root: Path, mode: str) -> str:
    dst_root.mkdir(parents=True, exist_ok=True)
    dst = dst_root / src.name

    if dst.is_symlink() or dst.exists():
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        else:
            shutil.rmtree(dst)

    if mode == "symlink":
        try:
            dst.symlink_to(src, target_is_directory=True)
            return f"symlinked -> {dst}"
        except OSError:
            shutil.copytree(src, dst)
            return f"copied (symlink fallback) -> {dst}"
    else:
        shutil.copytree(src, dst)
        return f"copied -> {dst}"


def uninstall_from_root(dst_root: Path) -> list[str]:
    removed: list[str] = []
    for name in SKILL_NAMES:
        target = dst_root / name
        if target.is_symlink() or target.is_file():
            target.unlink()
            removed.append(str(target))
        elif target.is_dir():
            shutil.rmtree(target)
            removed.append(str(target))
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install book-studio-skills for OpenCode, Claude Code, Codex CLI & DeepSeek Harness."
    )
    parser.add_argument(
        "--target",
        nargs="+",
        choices=["all", "claude", "codex", "opencode", "dsh"],
        default=["all"],
        help="Target agent harness(es). Default: all.",
    )
    parser.add_argument(
        "--scope",
        choices=["global", "project"],
        default="global",
        help="Install globally in user home (~) or into a specific project directory. Default: global.",
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Target project root when --scope=project (default: current directory).",
    )
    parser.add_argument(
        "--mode",
        choices=["copy", "symlink"],
        default="copy",
        help="Copy files or symlink to this repo. Default: copy.",
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install Python dependencies from requirements.txt.",
    )
    parser.add_argument("--list", action="store_true", help="List available skills and exit.")
    parser.add_argument("--uninstall", action="store_true", help="Remove installed skills.")
    args = parser.parse_args()

    if args.list:
        print(f"Available Book Studio skills ({len(SKILL_NAMES)}):")
        for s in SKILL_NAMES:
            print(f"  - {s}")
        return 0

    if args.install_deps and REQUIREMENTS_FILE.is_file():
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)], check=True)

    for name in SKILL_NAMES:
        skill_md = SKILLS_SRC / name / "SKILL.md"
        if not skill_md.is_file():
            print(f"[ERROR] Missing source skill file: {skill_md}", file=sys.stderr)
            return 1

    project_dir = Path(args.project_dir).resolve()
    targets_map = resolve_targets(args.target, args.scope, project_dir)
    seen_roots: set[Path] = set()

    for label, roots in targets_map.items():
        print(f"[{label}]")
        for root in roots:
            resolved_root = root.resolve() if root.exists() else root
            if resolved_root in seen_roots:
                continue
            seen_roots.add(resolved_root)

            if args.uninstall:
                for r in uninstall_from_root(root):
                    print(f"  - removed {r}")
            else:
                for name in SKILL_NAMES:
                    status = install_skill_dir(SKILLS_SRC / name, root, args.mode)
                    print(f"  + {name}: {status}")
                if "opencode" in str(root):
                    cmd_dir = root.parent / "commands"
                    cmd_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(COMMAND_SRC, cmd_dir / "book.md")
                    print(f"  + /book command -> {cmd_dir / 'book.md'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
