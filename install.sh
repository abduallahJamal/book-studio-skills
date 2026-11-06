#!/usr/bin/env bash
set -euo pipefail

# Multi-agent installer for book-studio-skills
# Supports OpenCode, Claude Code, Codex CLI, and DeepSeek Harness (global or project-local).

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS=(
  book
  book-intake
  book-architect
  book-drafter
  book-illustrator
  book-typesetter
  book-cover-wrap
  book-ebook-web
  book-preflight-qc
)

MODE=""
TARGET_DIR=""
INSTALL_OPENCODE=0
INSTALL_CLAUDE=0
INSTALL_CODEX=0
INSTALL_DSH=0
INSTALL_DEPS=0

usage() {
  cat <<'EOF'
Usage: ./install.sh [AGENT FLAGS] (--global | --project PATH | --list) [--install-deps]

Agent flags:
  --all            Install for OpenCode, Claude Code, Codex CLI, and DeepSeek Harness (default)
  --opencode       Install for OpenCode (.opencode/skills + .opencode/commands/book.md)
  --claude         Install for Claude Code (.claude/skills)
  --codex          Install for OpenAI Codex CLI (.agents/skills + .codex/skills)
  --dsh            Install for DeepSeek Harness (.dsh/skills + .agents/skills — flat depth-1 layout)

Scope & helper flags:
  --global         Install into user home (~/.config/opencode, ~/.claude, ~/.agents, ~/.codex, ~/.dsh)
  --project DIR    Install into a target project directory
  --install-deps   Install Python pro publishing packages (pymupdf, pikepdf, Pillow, python-docx)
  --list           List available skills and exit
  -h, --help       Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)
      INSTALL_OPENCODE=1; INSTALL_CLAUDE=1; INSTALL_CODEX=1; INSTALL_DSH=1; shift ;;
    --opencode)
      INSTALL_OPENCODE=1; shift ;;
    --claude)
      INSTALL_CLAUDE=1; shift ;;
    --codex)
      INSTALL_CODEX=1; shift ;;
    --dsh)
      INSTALL_DSH=1; shift ;;
    --install-deps)
      INSTALL_DEPS=1; shift ;;
    --global)
      MODE="global"; shift ;;
    --project)
      MODE="project"; TARGET_DIR="${2:-}"; shift 2 ;;
    --list)
      echo "Available Book Studio skills (${#SKILLS[@]}):"
      for s in "${SKILLS[@]}"; do
        echo "  - $s"
      done
      exit 0 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      exec python3 "$ROOT_DIR/install.py" "$@"
      ;;
  esac
done

if [[ $INSTALL_DEPS -eq 1 ]]; then
  python3 -m pip install -r "$ROOT_DIR/requirements.txt"
fi

if [[ $INSTALL_OPENCODE -eq 0 && $INSTALL_CLAUDE -eq 0 && $INSTALL_CODEX -eq 0 && $INSTALL_DSH -eq 0 ]]; then
  INSTALL_OPENCODE=1; INSTALL_CLAUDE=1; INSTALL_CODEX=1; INSTALL_DSH=1
fi

if [[ -z "$MODE" ]]; then
  echo "Error: specify --global, --project PATH, or --list" >&2
  usage >&2
  exit 2
fi

if [[ "$MODE" == "project" ]]; then
  if [[ -z "$TARGET_DIR" ]]; then
    echo "Error: --project requires a target directory path" >&2
    exit 2
  fi
  mkdir -p "$TARGET_DIR"
  TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
fi

copy_skills_into() {
  local dest_base="$1"
  mkdir -p "$dest_base"
  for s in "${SKILLS[@]}"; do
    rm -rf "$dest_base/$s"
    cp -R "$ROOT_DIR/skills/$s" "$dest_base/$s"
  done
}

AGENTS_INSTALLED=0

if [[ "$MODE" == "global" ]]; then
  if [[ $INSTALL_OPENCODE -eq 1 ]]; then
    OC_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"
    copy_skills_into "$OC_DIR/skills"
    mkdir -p "$OC_DIR/commands"
    cp "$ROOT_DIR/.opencode/commands/book.md" "$OC_DIR/commands/book.md"
    echo "[OK] Installed ${#SKILLS[@]} skills + /book command -> $OC_DIR"
  fi
  if [[ $INSTALL_CLAUDE -eq 1 ]]; then
    copy_skills_into "$HOME/.claude/skills"
    echo "[OK] Installed ${#SKILLS[@]} skills -> $HOME/.claude/skills"
  fi
  if [[ $INSTALL_CODEX -eq 1 ]]; then
    copy_skills_into "$HOME/.agents/skills"
    AGENTS_INSTALLED=1
    copy_skills_into "$HOME/.codex/skills"
    echo "[OK] Installed ${#SKILLS[@]} skills -> $HOME/.agents/skills & $HOME/.codex/skills"
  fi
  if [[ $INSTALL_DSH -eq 1 ]]; then
    DSH_ROOT="${DSH_HOME:-$HOME/.dsh}"
    copy_skills_into "$DSH_ROOT/skills"
    if [[ $AGENTS_INSTALLED -eq 0 ]]; then
      copy_skills_into "$HOME/.agents/skills"
    fi
    echo "[OK] Installed ${#SKILLS[@]} skills -> $DSH_ROOT/skills & $HOME/.agents/skills"
  fi
else
  if [[ $INSTALL_OPENCODE -eq 1 ]]; then
    copy_skills_into "$TARGET_DIR/.opencode/skills"
    mkdir -p "$TARGET_DIR/.opencode/commands"
    cp "$ROOT_DIR/.opencode/commands/book.md" "$TARGET_DIR/.opencode/commands/book.md"
    echo "[OK] Installed ${#SKILLS[@]} skills + /book command -> $TARGET_DIR/.opencode"
  fi
  if [[ $INSTALL_CLAUDE -eq 1 ]]; then
    copy_skills_into "$TARGET_DIR/.claude/skills"
    echo "[OK] Installed ${#SKILLS[@]} skills -> $TARGET_DIR/.claude/skills"
  fi
  if [[ $INSTALL_CODEX -eq 1 ]]; then
    copy_skills_into "$TARGET_DIR/.agents/skills"
    AGENTS_INSTALLED=1
    copy_skills_into "$TARGET_DIR/.codex/skills"
    echo "[OK] Installed ${#SKILLS[@]} skills -> $TARGET_DIR/.agents/skills & $TARGET_DIR/.codex/skills"
  fi
  if [[ $INSTALL_DSH -eq 1 ]]; then
    copy_skills_into "$TARGET_DIR/.dsh/skills"
    if [[ $AGENTS_INSTALLED -eq 0 ]]; then
      copy_skills_into "$TARGET_DIR/.agents/skills"
    fi
    echo "[OK] Installed ${#SKILLS[@]} skills -> $TARGET_DIR/.dsh/skills & $TARGET_DIR/.agents/skills"
  fi
fi
