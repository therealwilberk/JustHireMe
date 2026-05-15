# Resolve: backend-services

Source: `docs/maps/backend-services.md`
Branch: `fix/resolve-services`

## Slice strategy

Horizontal by severity: 🔵 → 🟡 → 🟣 (deferred).

## Pass 1: 🔵 HARDCODED values → config

### Existing config keys (direct swap)

| Value | File | Config key |
|-------|------|-----------|
| Probe timeout 5.0 | `provider_probe.py:35` | `settings.scraping.timeouts.default_http` |

### New config keys needed

| Value | File | Config key | Notes |
|-------|------|-----------|-------|
| Anthropic model name | `provider_probe.py:46` | Add to `config/llm.py` vision model field | Pinned dated model should be configurable |
| X query templates | `job_targets.py:302-304` | Add `x_query_template` to `config/scraping.py` | Replaces hardcoded `_profile_x_queries` templates |
| Free source query templates | `job_targets.py:281-285` | Add `free_source_query_template` to `config/scraping.py` | Replaces `_profile_free_source_targets` templates |

### Domain vocabulary (NOT changing)

Location terms in `_profile_x_queries`, `lang:en` filter, limit defaults — these are static search parameters. No change.

## Pass 2: 🟡 SUSPECT items

| Item | Action | Risk | Ripple |
|------|--------|------|--------|
| `kind_filter` overwritten in scout.py:47,109 | Remove the dead parameter from both functions; callers always pass it but it's immediately overwritten | Low | Check callers (`ghost.py`, `scanner.py`, `routes/scan.py`) |
| `_run_scan` duplicates `_job_eval_document` | Replace inline formatting with call to shared `_job_eval_document` | Low | Verify same output shape |
| `_job_targets` unused `market_focus` | Remove parameter or mark with `_` prefix | Low | Check callers |
| `_profile_x_queries` unused `market_focus` | Remove parameter or mark with `_` prefix | Low | Check callers |

## Pass 3: 🟣 COUPLED (deferred)

| Item | Note |
|------|------|
| `_fire_blocker` circular import | Structural refactor — needs module extraction |
| `scan_manager._ghost_lock` direct access | Needs public API on ScanManager |

## Verification

```bash
cd backend && uv run python -c "from main import app; print(f'{len(app.routes)} routes')"
cd backend && uv run python -m pytest tests/ -q --tb=short
```
