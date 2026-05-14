# Pass B4 — Resolve Lazy Imports Where Safe

**Mode:** AFK  
**Branch:** `feature/mainpy-refactor-pass-b`  
**Blocked by:** Pass B3 (bug fixes) — can run in parallel with B1/B2

---

## Goal

Move lazy imports back to top-of-file where doing so doesn't pull in slow transitive dependencies during startup. After Pass B3's fixes, we know which lazy imports exist. Some can be safely promoted; others must stay lazy due to import time.

## Analysis

From Pass A's measurements, the slow transitive dependencies are:

| Module | Import time | Safe to promote? |
|--------|-------------|------------------|
| `lancedb` (via `db.client`) | ~7s | **No** — only used in vector functions |
| `anthropic` (via `llm`) | ~2.6s | **No** — only used in LLM probing |
| `instructor` (via `llm`) | ~2.2s | **No** — same |
| `openai` (via `llm`) | ~1.9s | **No** — same |
| `langgraph` (via `graph`) | ~1.6s | **No** — only used in pipeline |
| `agents.*` | ~0.5-1s each | **No** — per-request-loaded |
| `core.*`, `schemas.*`, `stdlib` | < 0.1s | **Yes** — always fast |

## What to Do

1. **Audit** all current lazy imports in route files and service files
2. **Promote** imports that only reference fast modules (stdlib, `core.*`, `schemas.*`, `config`)
3. **Leave lazy** imports that pull in `db.client`, `llm`, `graph`, `agents.*`
4. **Document** each lazy import with a brief comment explaining why it stays lazy

### Example of what to promote:

```python
# In routes/leads.py — currently lazy, but safe to promote:
# from schemas.requests import FeedbackBody  # fast — keep at top (already there)

# In routes/scan.py — must stay lazy:
# from db.client import ...  # 7s import via lancedb — keep lazy
```

### Example comment for lazy imports that must stay:

```python
async def some_handler():
    from db.client import get_foo  # lazy: lancedb import takes ~7s
    ...
```

## Verification

```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

Also verify startup time:
```bash
timeout 10 uv run python -c "import main; print('import OK')"
```

Should complete in under 3 seconds.

## Commit

```
chore(b4): promote fast lazy imports, document remaining slow ones
```
