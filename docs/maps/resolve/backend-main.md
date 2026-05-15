# Resolve: backend-main — COMPLETED

Source: `docs/maps/backend-main.md`
Branch: `fix/resolve-backend-main`
Status: All passes done. Ready to merge.

## Results

| Pass | Items | Files changed | Tests |
|------|-------|---------------|-------|
| 🔴 1 — Dead code | `ContextFormatter` deleted | `logger.py`, `test_log_context.py` | 28/28 |
| 🔵 2a — Provider URLs | 7 hardcoded URLs → config | `llm.py` | 31/31 |
| 🔵 2b — Tokens/timeouts | 6 values → config + `_TIMEOUT` | `llm.py` | 31/31 |
| 🔵 2c — Ghost interval | `hours=6` → config | `main.py` | 2/2 |
| 🔵 2d — Secret diag list | Noted: values are config-driven, manual enum acceptable | — | — |
| 🔵 2e — MCP defaults | 3 defaults → config + new config key | `mcp_server.py`, `config/scoring.py` | 31/31 |
| 🟠 3 — Stale re-exports | 12 re-exports removed; `ghost.py` import updated | `main.py`, `services/ghost.py` | 40/40 |
| 🟡 4a — Unused `os` import | Noted: only used in 1 place, acceptable stdlib import | — | — |
| 🟡 4b — Unused `get_logger` | Import removed | `main.py` | ✓ |
| 🟡 4c — No stdin limit | 64KB readline limit added | `mcp_server.py` | ✓ |
| 🟡 4d — `enrich()` callers | Zero production callers; function noted, left in place | — | — |

**Final test count:** 326 collected (2 deselected as external)
**App boots:** 59 routes

## Verification commands

```bash
cd backend && uv run python -c "from main import app; print(len(app.routes))"
cd backend && uv run python -m pytest tests/ -q --tb=short
```

This file to be deleted after merge.
