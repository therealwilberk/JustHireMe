# Resolve: backend-routes

Source: `docs/maps/backend-routes.md`
Branch: `fix/resolve-routes`

## Slice strategy

Horizontal by severity: 🔴 → 🔵 → 🟡 → 🟢. 🟣 deferred (structural refactor).

## Pass 1: 🔴 DEAD code removal

| Item | File:Line | Action | Risk |
|------|-----------|--------|------|
| `HTTPException` import | `misc.py:9` | Remove unused import | None — confirmed unused |
| `JSONResponse` import | `misc.py:10` | Remove unused import | None — confirmed unused |

Test: `pytest tests/ -q --tb=short`

## Pass 2: 🔵 HARDCODED → config

### Existing config keys (direct swap)

| Value | File | Config key |
|-------|------|-----------|
| Heartbeat 2.0s timeout | `ws.py:49` | `settings.app.websocket.heartbeat_interval` (check if exists) |

### New config keys needed

| Value | File | Config key | Notes |
|-------|------|-----------|-------|
| `50 * 1024 * 1024` file size limit | `ingest.py:95` | `settings.app.upload.max_file_size` | Magic number |
| `"selectors_fetched_at": "0"` | `actions.py:182` | Extract to named constant | Magic reset value |
| `"fresher"`, `"junior"` strings | `leads.py:38,91-94` | Already in `config/scoring.py` — `_SENIOR_FLAGS` / `_BEGINNER_FLAGS` | Domain vocabulary — acceptable as constant |
| Provider list inline | `settings.py:50` | Already in `config/llm.py` provider defaults | Use `settings.llm.*` instead |
| `"job"` kind filter | `leads.py:285` | Inline — low impact | Note as constant |
| 100 items WS broadcast cap | `scan.py:81` | Add to `ScraperLimits` | Magic number |
| Ghost mode interval `hours=6` | `settings.py:95` | `config.app.ghost_mode.interval_hours` | Already exists — direct swap |

### Domain data (no change)

Seniority strings, lead status values — matching domain vocabulary.

## Pass 3: 🟡 SUSPECT items

| Item | Action | Risk |
|------|--------|------|
| `_annotate_job_lead` in routes | Note — belongs in services.scout | Low — not actionable in this pass |
| `save_lead` 20+ kwargs in `leads.py` | Note — brittle pattern | Low — not actionable in this pass |

## Verification

```bash
cd backend && uv run python -c "from main import app; print(len(app.routes))"
cd backend && uv run python -m pytest tests/ -q --tb=short
```
