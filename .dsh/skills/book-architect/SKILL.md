---
name: book-architect
description: "Design a complete Arabic or English book from a raw topic or thesis: generate editorial/outline.json, Book Bible terminology/character locks, Art Bible visual rules, and a Voice Lock sample before chapter drafting begins."
---

# `book-architect` — Book Architecture, Voice Lock & Continuity Bibles

Never jump straight from a topic prompt into drafting Chapter 1. Books drafted without an explicit chapter contract, terminology lock, and Voice Lock collapse by Chapter 4 into repetitive structure, drifting terminology, and generic AI cadence.

## 1. Four-Artifact Architecture Protocol

Before `book-drafter` writes any full chapter, produce and lock four artifacts inside `editorial/`:

1. **`editorial/outline.json` — Chapter & Section Contract:**
   - Every chapter defines: `id`, `title`, `core_question`, `key_takeaway`, `opening_hook_type`, `target_words`, `sections[]`, and `planned_figures[]`.
   - Enforce **anti-overlap**: no two chapters may share the same central case study, metaphor, or thesis claim.
2. **`editorial/book-bible.md` — Continuity & Bilingual Terminology Lock:**
   - For non-fiction/technical books (especially Arabic `RTL`): lock the exact Arabic translation of every recurring technical term (e.g., `Idempotency -> التماثل التكراري`, `Latency -> زمن الاستجابة`) on first mention so Chapter 2 and Chapter 8 never use conflicting translations.
   - For fiction: lock character voices, physical traits, timeline dates, and world rules.
3. **`editorial/voice-lock.md` — 600–800 Word Calibration Sample:**
   - Write one 600–800 word calibration passage in the target register and lock rhythm rules (sentence-length burstiness `CV >= 0.40`, banned openings, pronoun stance, vocalization level for Arabic).
4. **`editorial/art-bible.md` — Visual & Diagram Cohesion Lock:**
   - Lock palette hex codes, stroke weights, diagram font family, and the **No-Text-In-Raster-Art** rule for `book-illustrator`.

See [`references/genre-blueprints.md`](references/genre-blueprints.md) for structural arcs across all 6 genres.

## 2. Deterministic CLI Usage

```bash
# Generate editorial/outline.json, voice-lock.md, book-bible.md, art-bible.md & optional chapter stubs
python3 skills/book-architect/scripts/scaffold_outline.py \
  --project ./my-book \
  --chapters 8 \
  --words-per-chapter 2500 \
  --scaffold-chapters

# Validate an edited editorial/outline.json for duplicate titles, missing theses, or budget skew
python3 skills/book-architect/scripts/scaffold_outline.py \
  --project ./my-book \
  --validate-only
```

## 3. Hard Guardrails

- **Vary Chapter Openings:** Explicitly assign distinct `opening_hook_type` tags across consecutive chapters (`incident`, `paradox`, `historical-vignette`, `metric-anomaly`, `dialogue`, `direct-thesis`) so every chapter does not open with the same formula.
- **Pause for User Approval When Interactive:** Present the outline summary and Voice Lock sample before launching full-manuscript drafting.
