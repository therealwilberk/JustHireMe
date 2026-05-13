# Feature Spec — Phase B: Security Remediation & Migration Paths

> Written before any code. Source of truth for scope, requirements, and validation.

---

## Meta

| Field | Value |
|-------|-------|
| Feature name | Security Remediation & Migration Paths |
| Roadmap phase | Phase B |
| Branch | `feature/phase-b-security-migration` |
| Type | `Infra` (horizontal — exempt from vertical-slice rule) |
| Mode | `TBD` |
| Status | `[~] In Progress` |
| Depends on | Phase A (config layer for env resolution) |
| Blocks | Phase D+ |
| Created | 2026-05-13 |
| Last updated | 2026-05-13 |

---

## 1. Goal

API keys resolved from env vars exclusively, with no secrets in URLs, query params, or stdout, and a graceful deprecation path for existing SQLite-stored credentials. A single `resolve_secret()` function becomes the only legal access path for all secrets — preventing scattered key-resolution logic and making future SQLite fallback removal a one-file change.

---

## 2. Background & Context

The codebase currently stores all API keys in a SQLite `settings` table as plaintext key-value pairs. Keys are resolved through three different patterns (SQLite-only, env var fallback, config-driven) depending on which module you're in. Two services (Apify, Hunter.io) pass API tokens as URL query parameters — exposing them in HTTP logs, access logs, and any intermediary debug output. The JHM auth token is written to stdout, which is a shared resource and can leak into logs or terminal history.

Phase A established the config layer with env-var-name registries (`LLMKeyNames`, `ContactAPIKeyNames`, etc.) but did not migrate resolution logic or deprecate SQLite storage. Phase B closes that gap with a unified resolver and migration warnings.

---

## 3. Scope

### In scope

- [ ] **Unified secret resolver**: `backend/config/secrets.py` with `resolve_secret(env_var_name, settings_key=None) -> str | None`. Resolution order: env var → SQLite fallback with deprecation warning → None.
- [ ] **Config key registries**: Every API key gets its env-var name and settings-table key name registered in the appropriate config module (`llm.py`, `contact.py`, `scraping.py`, `app.py`). Apify token/actor and Hunter/Proxycurl settings keys added where missing.
- [ ] **All secret lookups centralized**: Every `os.environ.get()` and `get_setting()` call for API keys replaced with `resolve_secret()`.
- [ ] **API keys out of URLs**: Apify token moved from `?token=` query param to `Authorization: Bearer` header. Hunter.io key moved from `?api_key=` query param to `X-API-Key` header.
- [ ] **Auth token to stderr** (deferred): `JHM_TOKEN=...` stays on stdout — blocked by Tauri sidecar protocol (`src-tauri/src/lib.rs:301` reads token from stdout only). Token is ephemeral (generated at startup) and stdout is exclusively captured by Tauri in this local desktop app, so the security posture is equivalent. Revisit if sidecar IPC changes.
- [ ] **Write-path deprecation warnings**: Settings endpoint logs WARN when any sensitive key is written to SQLite, naming the env var to set instead.
- [ ] **Startup migration diagnostics**: On boot, for every key resolved from SQLite (not env), log WARN with env var name and migration instructions.
- [ ] **Deprecation milestone defined**: Roadmap updated with phase target for removing SQLite fallback entirely.

### Out of scope

- OS keychain integration (deferred — not on current roadmap)
- `except: pass` → logged warnings (Phase C)
- WebSocket async-safety / SQLite WAL / concurrency (Phase C)
- Frontend error handling (Phase C)
- Non-security hardcoded values (Phase A — complete)
- All feature work (Phase D+)

---

## 4. Requirements

### Functional Requirements

| # | Requirement | Priority |
|---|-------------|----------|
| F1 | `resolve_secret(env, settings_key)` checks env var first, then SQLite with deprecation warning, returns `None` if neither found | `Must` |
| F2 | Every API key in the codebase is resolved through `resolve_secret()` — zero scattered `os.environ.get()` or `get_setting()` calls for secrets | `Must` |
| F3 | Every API key has its env-var name and settings-table key registered in a config module — no magic strings | `Must` |
| F4 | Apify token is sent via `Authorization: Bearer` header, not `?token=` query param | `Must` |
| F5 | Hunter.io key is sent via `X-API-Key` header, not `?api_key=` query param | `Must` |
| F6 | JHM auth token is written to stderr, not stdout | `Deferred` — blocked by Tauri sidecar protocol at `src-tauri/src/lib.rs:301`. Token remains on stdout; this is a local desktop app where stdout is exclusively captured by the sidecar. |
| F7 | Writing a sensitive key to SQLite via settings endpoint logs a WARN-level deprecation message naming the env var | `Must` |
| F8 | App startup logs WARN for every secret resolved from SQLite, with migration instructions | `Must` |
| F9 | Zero new secrets can be introduced without going through `resolve_secret()` — the pattern is the enforcement | `Should` |

### Non-Functional Requirements

| # | Requirement | Notes |
|---|-------------|-------|
| NF1 | `resolve_secret()` is synchronous and cheap — no blocking I/O beyond `os.environ.get()` and SQLite read | Hot-path safe |
| NF2 | Deprecation warnings are logged once per key per session — no spam on repeated resolution | Use `functools.lru_cache` or flag dict |
| NF3 | SQLite writes continue to work — the deprecation path is advisory, not breaking | Migration smoothness over purity |
| NF4 | Resolver is discoverable — importable from `backend.config.secrets` | Simple import path |

---

## 5. Implementation Plan

### Workstream 1: Config registries

- [ ] **Task 1.1:** Add `ApifyKeyNames` (env) and `ApifySettingsKeyNames` (settings-table) to `backend/config/scraping.py` for `apify_token` and `apify_actor`.
- [ ] **Task 1.2:** Add `ContactSettingsKeyNames` to `backend/config/contact.py` for `hunter_api_key` and `proxycurl_api_key` (env names already exist).
- [ ] **Task 1.3:** Register `x_bearer_token` and `linkedin_cookie` settings keys in `SensitiveKeys` / appropriate config in `backend/config/app.py`.

### Workstream 2: Unified resolver

- [ ] **Task 2.1:** Create `backend/config/secrets.py` with `resolve_secret(env_var_name, settings_key=None, warn_once=True) -> str | None`.
  - Check `os.environ.get(env_var_name)` — return immediately with no warning.
  - If `settings_key` provided, call `get_setting(settings_key)` — if found, log WARN once per key, return value.
  - If neither found, return `None`.
- [ ] **Task 2.2:** Write unit tests for `resolve_secret()` — env precedence, SQLite fallback, deprecation logging, None return, warn_once dedup.

### Workstream 3: Migrate all secret lookups

- [ ] **Task 3.1:** `backend/llm.py` — replace `_key_for_step()` / `_KEY_NAMES` / `_SETTINGS_KEY_NAMES` resolution with `resolve_secret()`. The LLM provider loop calls `resolve_secret(env_name, settings_key)` instead of the current manual chain.
- [ ] **Task 3.2:** `backend/main.py` — replace `cfg.get("apify_token")`, `cfg.get("apify_actor")` with `resolve_secret()`. Same for any other raw dict key reads.
- [ ] **Task 3.3:** `backend/agents/scout.py` — replace direct Apify token reads with `resolve_secret()`.
- [ ] **Task 3.4:** `backend/agents/contact_lookup.py` — replace `os.environ.get()` / `get_setting()` chains with `resolve_secret()`.
- [ ] **Task 3.5:** `backend/agents/x_scout.py` — replace X bearer token resolution with `resolve_secret()`.
- [ ] **Task 3.6:** `backend/agents/free_scout.py` — replace `custom_connector_headers` raw read with `resolve_secret()`.

### Workstream 4: URLs to headers

- [ ] **Task 4.1:** `backend/agents/scout.py` — change Apify POST from `params={"token": tok}` to `headers={"Authorization": f"Bearer {tok}"}`. Update callers if needed.
- [ ] **Task 4.2:** `backend/agents/contact_lookup.py` — change Hunter.io request from `?api_key=` to `headers={"X-API-Key": key}`.

### Workstream 5: Auth token to stderr (deferred)

- [ ] **Task 5.1:** `backend/main.py` — change `sys.stdout.write(f"JHM_TOKEN=...")` to `sys.stderr.write(...)`. Port line stays on stdout.
  **Deferred:** Tauri sidecar at `src-tauri/src/lib.rs:301` reads `JHM_TOKEN=` from stdout exclusively. Moving to stderr would require changing the Rust sidecar code. In a local desktop app where stdout is exclusively captured by Tauri, the security posture is equivalent. Revisit if sidecar IPC protocol changes.
- [ ] **Task 5.2:** Write test that captures stdout/stderr and confirms token is only in stderr. (deferred with 5.1)

### Workstream 6: Deprecation warnings

- [ ] **Task 6.1:** `backend/main.py` settings endpoint — for each key that matches `_sensitive()`, after writing to SQLite, log WARN with env var name.
- [ ] **Task 6.2:** `backend/main.py` startup — iterate known secret keys, call `resolve_secret()`, log WARN for any resolved from SQLite.

### Workstream 7: Documentation

- [ ] **Task 7.1:** Update `.env.example` with every env var declared in config schemas.
- [ ] **Task 7.2:** Update roadmap with SQLite fallback removal milestone (target: Phase C or early Phase D).
- [ ] **Task 7.3:** Document migration in startup diagnostics output.

**Blocking relationships:**
- Tasks 1.1–1.3 unblocked (pure config additions)
- Task 2.1 blocked by 1.1–1.3 (resolver needs key names)
- Tasks 3.1–3.6 blocked by 2.1 (need resolver)
- Tasks 4.1–4.2 unblocked (independent URL changes)
- Task 5.1 unblocked (one-line change)
- Tasks 6.1–6.2 blocked by 2.1 (need resolver output)
- Tasks 7.1–7.3 unblocked (docs)

---

## 6. API / Interface Design

### Resolver interface

```python
# backend/config/secrets.py

def resolve_secret(
    env_var_name: str,
    settings_key: str | None = None,
    warn_once: bool = True,
) -> str | None:
    """Resolve a secret from env var (preferred) or SQLite settings table (deprecated).

    Resolution order:
    1. os.environ[env_var_name] — returned immediately, no warning
    2. get_setting(settings_key) — returned with WARN-level deprecation log
    3. Neither found — returns None

    When warn_once=True, each (env_var_name, settings_key) pair is logged
    at most once per process lifetime.
    """
```

### Key registration pattern

Each config module registers a dataclass:

```python
# backend/config/contact.py
@dataclass
class ContactSettingsKeyNames:
    hunter: str = "hunter_api_key"
    proxycurl: str = "proxycurl_api_key"
```

Usage at call site:

```python
from backend.config import settings
from backend.config.secrets import resolve_secret

key = resolve_secret(
    settings.contact.api_key_names.hunter,       # "HUNTER_API_KEY"
    settings.contact.settings_key_names.hunter,   # "hunter_api_key"
)
```

---

## 7. Migration Architecture

```
Startup
  │
  ├─ For each registered secret key:
  │     resolve_secret(env, settings)
  │       ├─ env var set → OK (no log)
  │       └─ SQLite fallback → WARN "Set {ENV} instead"
  │
  ├─ Settings endpoint POST /api/v1/settings
  │     ├─ sensitive key detected → WARN "Set {ENV} instead"
  │     └─ write to SQLite (still works)
  │
  └─ All secret lookups in runtime
        └─ resolve_secret() → env → SQLite → None
```

Future removal (Phase C/D target):
1. Remove SQLite fallback from `resolve_secret()`
2. Remove `settings_key` parameter
3. Drop `settings` table schema from SQLite
4. Clean up `_sensitive()` and `SensitiveKeys` config

---

## 8. Error Handling Map

| Scenario | Expected behaviour | Logged? | User-facing message |
|----------|--------------------|---------|---------------------|
| Env var set, SQLite also has value | Env var wins silently | No | None |
| Env var missing, SQLite has value | SQLite value returned + deprecation | Yes — WARN | (log only) "Secret `hunter_api_key` resolved from SQLite. Set HUNTER_API_KEY env var to migrate." |
| Neither env var nor SQLite has value | Returns `None` | No (expected) | Caller handles missing key |
| Key written to SQLite via settings endpoint | Write succeeds + deprecation | Yes — WARN | (log only) "Secret `anthropic_key` written to SQLite — deprecated. Set ANTHROPIC_API_KEY instead." |
| Apify/Hunter URL logged with old param pattern | No longer possible — keys moved to headers | N/A | N/A |
| JHM token accidentally captured in stdout log | Deferred — token stays on stdout (required by Tauri sidecar protocol). Token is ephemeral and stdout is exclusively captured by Tauri in local desktop mode, so effective posture is equivalent. | N/A | N/A |

---

## 9. Trust & Autonomy Boundaries

All Phase B tasks are **deterministic** — migration of secret resolution logic, URL parameter changes, and deprecation wiring are mechanical transformations. The resolver design is a one-time architectural decision (approved above); all remaining tasks are pure implementation.

Tasks tagged `[AFK]` (fully deterministic): 1.1–1.3, 3.1–3.6, 4.1–4.2, 5.1, 7.1–7.3.
Tasks requiring judgment call: Task 2.1 (resolver implementation detail — single approved design).

---

## 10. Validation Checklist

### Automated tests

- [ ] `resolve_secret()` returns env var when set, SQLite value when env is missing, `None` when neither
- [ ] `resolve_secret()` logs WARN on SQLite fallback, does not log on env-var hit
- [ ] Apify endpoint call has no `token` query param — `Authorization: Bearer` header present instead
- [ ] Hunter.io endpoint call has no `api_key` query param — `X-API-Key` header present instead
- [ ] JHM_TOKEN appears only in stderr, not stdout (deferred — see Workstream 5)
- [ ] Settings endpoint POST of sensitive key logs WARN but still persists to SQLite
- [ ] All existing backend tests pass

### Manual checks

- [ ] Run app with no env vars set — confirm startup logs WARN for each SQLite-resolved secret
- [ ] Set `ANTHROPIC_API_KEY` env var — confirm no deprecation warning for that key
- [ ] Open settings UI, save a key — confirm WARN appears in server log
- [ ] `git grep 'os\.environ\.get' backend/` — confirm only `resolve_secret()` and non-secret code use it
- [ ] `git grep 'cfg\.get.*api_key' backend/` — confirm zero raw dict key reads for secrets

### Code quality gates

- [ ] Zero new secrets resolvable outside `resolve_secret()`
- [ ] All key names registered in config modules — no string literals at call sites
- [ ] No `except: pass` in any security-related code
- [ ] `.env.example` contains all env vars the config layer recognizes for secrets
- [ ] Branch is clean — no unrelated changes

---

## 11. Open Questions

None remaining — design approved in Phase B brainstorming session (2026-05-13).

---

## 12. Decisions Log

| Date | Decision | Reason | Alternatives considered |
|------|----------|--------|-------------------------|
| 2026-05-13 | `resolve_secret()` as the only legal secret access path | Prevents scattered resolution logic; one-file change for future SQLite removal | Per-module duplication, ad-hoc env fallback |
| 2026-05-13 | Env-var-first with SQLite fallback and deprecation | Migration safety — existing users continue working while receiving clear migration signals | Immediate breakage (Approach 1), silent dual-path (status quo) |
| 2026-05-13 | Config registries per domain module (llm.py, contact.py, etc.) | Maintains Phase A domain-boundary pattern, keys live with their domain | Single monolithic registry |
| 2026-05-13 | SQLite writes continue during deprecation period | Prevents data loss for users who haven't migrated yet | Immediate write-blocking |
| 2026-05-13 | C2 (token to stderr) deferred — blocked by Tauri sidecar protocol | `src-tauri/src/lib.rs:301` reads token from stdout exclusively. Local desktop app — stdout not shared, token ephemeral. Posture equivalent. | Change Tauri Rust code, use temp file |
| 2026-05-13 | SQLite fallback removal targeted for Phase C/D | Gives users one full infra phase to migrate; aligns with Phase C's reliability scope | Immediate removal, deferred indefinitely |

---

## 13. Call Site Migration Map

| Current pattern | File(s) | New pattern |
|----------------|---------|-------------|
| `cfg.get("apify_token") or None` | `main.py:533`, `main.py:1332` | `resolve_secret(settings.scraping.apify_key_names.token, settings.scraping.apify_settings_key_names.token)` |
| `get_setting("hunter_api_key") or os.environ.get("HUNTER_API_KEY")` | `contact_lookup.py:183` | `resolve_secret(settings.contact.api_key_names.hunter, settings.contact.settings_key_names.hunter)` |
| `get_setting("proxycurl_api_key") or os.environ.get("PROXYCURL_API_KEY")` | `contact_lookup.py:184` | `resolve_secret(settings.contact.api_key_names.proxycurl, settings.contact.settings_key_names.proxycurl)` |
| `_KEY_NAMES[provider]` / `_SETTINGS_KEY_NAMES[provider]` chain | `llm.py:40-76` | `resolve_secret(env_name, settings_key)` per provider |
| `cfg.get("x_bearer_token") or os.environ.get(cfg.settings.app.bearer_token_env.x_bearer_token)` | `x_scout.py:400-401` | `resolve_secret(settings.app.bearer_token_env.x_bearer_token, "x_bearer_token")` |
| `cfg.get("linkedin_cookie")` | `scout.py` / `main.py` | `resolve_secret(..., "linkedin_cookie")` |
| `cfg.get("custom_connector_headers")` | `free_scout.py:89-96` | `resolve_secret(..., "custom_connector_headers")` |
| `?token=` in Apify URL | `scout.py:359-363` | `Authorization: Bearer` header |
| `?api_key=` in Hunter URL | `contact_lookup.py:93-95` | `X-API-Key` header |
| `print/stdout` JHM_TOKEN | `main.py:2055` | Deferred — stays on stdout. Tauri sidecar at `src-tauri/src/lib.rs:301` reads token from stdout exclusively. Revisit if sidecar IPC changes. |

---

_Last updated: 2026-05-13 — Agent_
