---
name: book-drafter
description: "Draft and edit Arabic (RTL) or English (LTR) book chapters with full-manuscript continuity, a grounded Claim Ledger, 7-stage editorial refinement, direct humanizer-skills anti-slop integration, and Cold Beta-Reader scoring."
---

# `book-drafter` — Continuity Drafting, Claim Ledger & Humanizer Bridge

Write and refine full-length book chapters that read like an authoritative human author across 200+ pages — never like stitched-together LLM blog posts.

## 1. Full-Context Continuity Protocol

1. **Before Writing Chapter `N`:**
   - Read `editorial/outline.json`, `editorial/book-bible.md`, and `editorial/voice-lock.md`.
   - Read the closing 400 words of Chapter `N-1` plus the list of metaphors/examples already used so Chapter `N` never repeats an anecdote, opening formula, or definition.
2. **Ground Every Fact in `editorial/claims-ledger.json`:**
   - Whenever a chapter cites a date, percentage, benchmark, historical event, or research study, log `{ "id", "chapter", "claim", "numbers", "source", "verified" }` in `editorial/claims-ledger.json`. Never invent citations or statistics.

## 2. Seven-Stage Editorial Loop + `humanizer-skills` Bridge

Run every drafted chapter through 7 focused passes:
1. **Structural Arc Pass:** Does the chapter answer its `core_question` from `outline.json`?
2. **Continuity & Terminology Pass:** Check every technical/character term against `editorial/book-bible.md`.
3. **Claim & Digit Lock Pass:** Verify every statistic and footnote against `editorial/claims-ledger.json`.
4. **Line Rhythm & Burstiness Pass:** Break monotonous 15–18 word paragraphs; alternate crisp 6-word verdicts with multi-clause explanations (`CV >= 0.40`).
5. **Bilingual Anti-Slop Pass (`humanizer-skills` Integration):**
   - Strip English AI tells (`delve`, `tapestry`, `leverage`, `Moreover,`, prose em-dash overuse, `Not X, but Y` formulas).
   - Strip Arabic AI translation calques (`في ظل التطورات المتسارعة`, `مما لا شك فيه`, `يلعب دوراً محورياً`, excessive `تم + المصدر` passive calques, `يقوم بـ + المصدر` padding, and `لا يقتصر الأمر على X فحسب، بل يتعداه إلى Y`).
   - If [`humanizer-skills`](https://github.com/abduallahJamal/humanizer-skills) is installed in the harness, invoke `humanize-text` (or `academic-humanizer` for scholarly monographs) directly before locking the manuscript!
6. **Opening & Ending Surgery:** Cut throat-clearing first paragraphs and summary-style *"In conclusion, this chapter showed..."* endings.
7. **Cold Beta-Reader Gate:** Score Chapters 1–3 on Hook Strength, Clarity, Pacing, Voice Authenticity, and Put-Down Risk (`>= 7/10` on every axis before typesetting).

See [`references/editorial-and-humanizer-bridge.md`](references/editorial-and-humanizer-bridge.md) for the complete 7-stage checklist and Arabic/English slop dictionary.

## 3. Deterministic CLI Usage

```bash
# Audit manuscript word budgets, burstiness CV, cross-chapter repetition, AR/EN AI slop & claim grounding
python3 skills/book-drafter/scripts/manuscript_metrics.py --project ./my-book

# Strict gate mode (exits non-zero if high AI-slop density or cross-chapter 6-gram cloning is detected)
python3 skills/book-drafter/scripts/manuscript_metrics.py --project ./my-book --strict
```
