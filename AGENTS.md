# AGENTS.md — Repository Engineering & Skill Sync Rules

`book-studio-skills` is a multi-harness Agent Skills suite (9 skills + `/book` command) supporting **OpenCode**, **Claude Code**, **OpenAI Codex CLI**, and **DeepSeek Harness (`dsh`)**.

## Canonical Source of Truth

1. **Always edit files inside `skills/<skill-name>/` first.** Never directly edit `.opencode/skills/`, `.claude/skills/`, `.agents/skills/`, or `.dsh/skills/`.
2. Keep `skills/` strictly **depth-1 flat** (`skills/<kebab-name>/SKILL.md`) so `@deepseek-ai/dsh-skill-filesystem` discovers every skill without nested directory drops.
3. Quote any YAML frontmatter value containing colons (`description: "..."`) so strict parsers in OpenCode and DeepSeek Harness succeed.
4. After modifying anything in `skills/`, run:
   ```bash
   ./scripts/sync-platforms.sh
   python3 scripts/validate.py
   ```
5. Every bundled Python CLI tool must support `--help`, run deterministically on both **Arabic (`RTL`)** and **English (`LTR`)** books, and pass end-to-end compilation + 15-gate preflight QC in `scripts/validate.py`.
