# Seven-Stage Editorial Loop & `humanizer-skills` Bridge

## 1. Direct Bridge with `abduallahJamal/humanizer-skills`

`book-studio-skills` and `humanizer-skills` are designed as companion suites:
- **General Non-Fiction, Essays & Trade Books:** Pair `book-drafter` with `humanize-text` (`clear-thinker` or `storyteller` voice profile) and verify fact survival via `humanize_gate.py`.
- **Academic Monographs & Textbooks (`academic-monograph`):** Pair `book-drafter` with `academic-humanizer` (`academic_prep.py`) so `[^n]` footnotes, `$...$` equations, and citations stay 100% locked.
- **Pre-Typesetting Slop Audit:** Run `manuscript_metrics.py` across all chapters simultaneously to catch cross-chapter repetition that single-article detectors miss.

## 2. High-Risk English & Arabic AI Tells Blocked by `manuscript_metrics.py`

### English Book-Scale Tells
- Canned transitions: `Moreover,`, `Furthermore,`, `Additionally,`, `It is worth noting that`, `In today's rapidly evolving`
- Lexicon clichés: `delve`, `tapestry`, `testament to`, `underscores`, `pivotal`, `paradigm shift`, `seamlessly`
- Structural clichés: Repeated *"It's not about X — it's about Y"* closers at the end of multiple sections.

### Arabic Book-Scale Tells (`الركاكة المترجمة في الكتب العربية`)
- Canned openers: `في ظل التطورات المتسارعة`، `في عالمنا المعاصر`، `مما لا شك فيه أن`، `من الجدير بالذكر أن`
- Translation calques:
  - Passive calque inflation: `تم تصميم`، `تم تنفيذ`، `تم اعتماد` instead of clean active/passive Arabic verbs (`صُمِّم`، `نُفِّذ`، `اعتمدنا`).
  - Verb padding: `يقوم بتوفير` -> `يوفّر`؛ `تقوم بمعالجة` -> `تعالج`.
  - Adverbial calque: `بشكل كبير`، `بشكل فعال`، `بشكل ملحوظ` instead of classic Arabic cognates (`معالجةً جذرية`، `أثراً بالغاً`).
- Canned chapter closers: `وفي الختام، يمكننا القول إن...`

## 3. Cold Beta-Reader 5-Axis Gate (`>= 7/10` Required)

1. **First-Page Magnetism:** Does Page 1 place the reader inside a concrete problem, scene, or tension within 120 words?
2. **Conceptual Momentum:** Does every `##` section earn its pages without restating the chapter intro?
3. **Cross-Chapter Freshness:** Zero recycled anecdotes or identical chapter rhythms across consecutive chapters.
4. **Evidence Density:** Specific numbers, named mechanisms, or concrete dialogue rather than vague abstractions.
5. **Voice Naturalness:** Passes `manuscript_metrics.py` with `slop_per_1k <= 2.5` and `burstiness_cv >= 0.35`.
