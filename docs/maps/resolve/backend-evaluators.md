# Resolve: backend-evaluators — COMPLETED

Source: `docs/maps/backend-evaluators.md`
Branch: `fix/resolve-evaluators`
Status: All passes done. Ready to merge.

## Results

| Pass | Items | Files changed | Status |
|------|-------|---------------|--------|
| 🔴 1 — Dead `_SYSTEM_PROMPT` removed | 1 removed | `evaluator.py` | ✅ |
| 🔴 2 — `classify_kind` bug fix | `default` param now used | `lead_intel.py` | ✅ |
| 🔵 3 — Truncation limits → config | 4 values wired to `EvaluatorConfig` | `evaluator.py` | ✅ |
| 🔵 4 — Feedback thresholds → config | 4 values → `FeedbackLearningConfig` | `feedback_ranker.py`, `config/scoring.py` | ✅ |
| 🟡 5 — Unused params | 4 params prefixed `_` | `lead_intel.py` | ✅ |
| 🟡 6 — Orphaned wrappers | 2 removed (zero callers) | `evaluator.py` | ✅ |
| ♻️ — Test import fixes | 12 re-export refs → direct imports | `test_regressions.py` | ✅ |
| 📋 — Deferred items | `lead-intel-flexibility.md` created | `docs/deferred/` | ✅ |

**Pre-existing failures (not caused by this branch):**
- 4 tests in `test_regressions.py` — fake storage and wrong test expectations

This file to be deleted after merge.
