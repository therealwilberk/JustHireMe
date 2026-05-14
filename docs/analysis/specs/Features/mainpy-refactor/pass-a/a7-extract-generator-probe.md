# Pass A7 — Extract Generator & Provider Probe

**Lines affected:** 1491-1573, 1918-1934, 2034-2124
**Target files:** `backend/services/generator.py`, `backend/services/provider_probe.py`
**Mode:** AFK

---

## Goal

Move the asset generation pipeline and LLM provider key probing into `services/`. These are self-contained: the generator doesn't call back to other services, and the probe is only used by the settings validation route.

---

## What Moves

### To `services/generator.py`

| Item | Lines in main.py |
|------|-----------------|
| `_asset_ready` | 1918-1919 |
| `_fire_blocker` | 1922-1934 |
| `_generate_one` | 2034-2096 |
| `_actuate` | 2099-2124 |

### To `services/provider_probe.py`

| Item | Lines in main.py |
|------|-----------------|
| `_probe_provider_key` | 1491-1542 |
| `_sensitive` | 1454-1458 (move from scanner — it's used by settings routes, not scan logic) |
| `_log_sensitive_deprecation` | 1461-1477 (same reasoning) |

**Note:** `_sensitive` and `_log_sensitive_deprecation` move here instead of `scanner.py` because they're used by settings routes, not scan logic. The earlier A5 plan listed them incorrectly.

---

## What Changes During the Move

| Change | Reason |
|--------|--------|
| Move `_sensitive` and `_log_sensitive_deprecation` to `provider_probe.py` | Correct module boundary |
| Import from new modules in `main.py` route handlers | `generate_for_lead` and `fire` routes call `_generate_one` / `_actuate` |

---

## Dependencies

- `core/ws_manager.py` (A3) — `cm.broadcast`
- `core/config_constants.py` (A3) — `_log`

---

## Verification

```bash
# 1. Compile checks
python -m py_compile backend/services/generator.py
python -m py_compile backend/services/provider_probe.py
python -m py_compile backend/main.py

# 2. Full test suite
cd backend && uv run python -m pytest tests/ -q --tb=line
```

---

## Commit

```
refactor(a1): extract generator and provider probe to services/
```
