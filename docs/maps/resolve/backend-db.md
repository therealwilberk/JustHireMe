# Resolve: backend-db

Source: `docs/maps/backend-db.md`
Branch: `fix/resolve-db`

## Slice strategy

Horizontal by severity: 🔴 → 🔵 → 🟡. 🟣 deferred.

## Pass 1: 🔴 DEAD code removal

| Item | File:Line | Action | Risk |
|------|-----------|--------|------|
| `graph_available()` | `client.py:134` | Remove function | Low — confirmed dead; no importers |
| `graph_error()` | `client.py:138` | Remove function | Low — confirmed dead; no importers |
| `get_all_freelance_leads()` | `client.py:523` | Remove function | Low — confirmed dead; no importers |
| `get_discovered_freelance_leads()` | `client.py:1114` | Remove function | Low — confirmed dead; no importers |
| `_b` first assignment | `client.py:41` | Remove line 41 (first `_b = data_base()`) | Low — immediately overwritten at line 84 |

Test: `pytest tests/test_regressions.py tests/test_observability.py -q --tb=short`

## Pass 2: 🔵 HARDCODED → config

### Existing config keys (direct swap)

| Value | File:Line | Config key |
|-------|-----------|-----------|
| `_b` first assignment removal | `client.py:41` | Remove, keep only the line 84 assignment |

### New config keys needed

| Value | File:Line | Config key | Notes |
|-------|-----------|-----------|-------|
| `"crm.db"` filename | `client.py:43` | Add to `ScrapingConfig` as `sqlite_filename` | Hardcoded DB filename |
| Score threshold 76 | `client.py:378,380` | Add to `ScoringConfig` or `ScrapingLimits` | Magic number for "matched"/"tailoring" |
| Allowed status set | `client.py:988-992` | Move to config constant (not user-facing) | Domain data — acceptable as constant |
| Feedback-to-status mappings | `client.py:1029-1037` | Add to `config/scoring.py` or note as domain data | Policies baked in |
| `_LEAD_SELECT_COLUMNS` | `client.py:245-252` | Note as schema definition — acceptable as constant | Must match SQLite schema by design |

### Domain data (no change)

SQLite table schemas, Kuzu table schemas, Kuzu query patterns, lead status values — these are intrinsic to the database design. Not config-viable.

## Pass 3: 🟡 SUSPECT items

| Item | Action | Risk |
|------|--------|------|
| `save_asset_path()` partially superseded | Noted, low priority | None |
| `update_skill()` / `delete_skill()` / `update_experience()` / `delete_experience()` / `update_project()` / `delete_project()` — test-only or unused | Note as likely dead; verify imports | Low — confirm no production callers |

## Verification

```bash
cd backend && uv run python -c "from main import app; print(len(app.routes))"
cd backend && uv run python -m pytest tests/ -q --tb=short
```
