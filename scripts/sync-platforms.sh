#!/usr/bin/env bash
set -euo pipefail

# Sync canonical skills/* into .opencode/skills/*, .claude/skills/*, .agents/skills/*, and .dsh/skills/*
# Use --check in CI to verify zero drift via recursive SHA-256 digests.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT_DIR/skills"
TARGETS=(
  "$ROOT_DIR/.opencode/skills"
  "$ROOT_DIR/.claude/skills"
  "$ROOT_DIR/.agents/skills"
  "$ROOT_DIR/.dsh/skills"
)

MODE="${1:-sync}"

manifest_of() {
  local dir="$1"
  (
    cd "$dir"
    find . -type f ! -path '*/__pycache__/*' ! -name '*.pyc' | LC_ALL=C sort | xargs sha256sum
  )
}

if [[ "$MODE" == "--check" ]]; then
  SRC_MANIFEST="$(manifest_of "$SRC")"
  for tgt in "${TARGETS[@]}"; do
    if [[ ! -d "$tgt" ]]; then
      echo "[DRIFT] Missing directory: $tgt" >&2
      exit 1
    fi
    TGT_MANIFEST="$(manifest_of "$tgt")"
    if [[ "$SRC_MANIFEST" != "$TGT_MANIFEST" ]]; then
      echo "[DRIFT] Skill files out of sync in $tgt (run ./scripts/sync-platforms.sh)" >&2
      diff -u <(echo "$SRC_MANIFEST") <(echo "$TGT_MANIFEST") || true
      exit 1
    fi
  done
  COUNT="$(find "$SRC" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
  echo "[OK] All $((COUNT * ${#TARGETS[@]})) mirrored skill directories match canonical skills/ SHA-256 digests."
  exit 0
fi

find "$SRC" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

for tgt in "${TARGETS[@]}"; do
  rm -rf "$tgt"
  mkdir -p "$tgt"
  cp -R "$SRC"/. "$tgt"/
done

COUNT="$(find "$SRC" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
echo "[SYNCED] Mirrored $COUNT canonical skills to .opencode/skills, .claude/skills, .agents/skills, and .dsh/skills."
