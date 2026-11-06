# Contributing to `book-studio-skills`

Contributions improving Arabic (`RTL`) / English (`LTR`) typography, style packs, preflight geometry gates, or multi-harness compatibility are welcome.

## Development Workflow

```bash
pip install -r requirements.txt
python3 skills/book/scripts/doctor.py

# Edit canonical files under skills/<skill-name>/
./scripts/sync-platforms.sh
./scripts/sync-platforms.sh --check

# Run full schema, link, Tri-Engine compilation & 15-gate preflight test suite
python3 scripts/validate.py
```

Ensure all 4 mirrored skill trees (`.opencode/skills`, `.claude/skills`, `.agents/skills`, `.dsh/skills`) match `skills/` SHA-256 digests before opening a pull request.
