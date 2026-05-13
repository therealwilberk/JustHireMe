# Feature Spec — Phase A: Config Architecture & Validation Foundation

> Written before any code. Source of truth for scope, requirements, and validation.

---

## Meta

| Field | Value |
|-------|-------|
| Feature name | Config Architecture & Validation Foundation |
| Roadmap phase | Phase A |
| Branch | `feature/phase-a-config-architecture` |
| Type | `Infra` (horizontal — exempt from vertical-slice rule) |
| Mode | `AFK` (all tasks are deterministic per autonomy boundary analysis) |
| Status | `[~] In Progress` |
| Depends on | `none` |
| Blocks | Phase B, Phase C |
| Created | 2026-05-13 |
| Last updated | 2026-05-13 |

---

## 1. Goal

A typed, validated config layer with clear authority boundaries that replaces all 150+ hardcoded values — providing the foundation every subsequent phase builds on. By the end of this phase, no production code reads a magic number, hardcoded URL, or literal threshold; all config flows through a centralized settings object with Pydantic validation, and the full test suite runs in CI to verify nothing broke.

---

## 2. Background & Context

The codebase-audit found 150+ hardcoded values scattered across 25 backend modules — URLs, API endpoints, timeouts, thresholds, model names, rubric weights, file paths. Every future feature either adds more hardcodes or depends on config infrastructure that doesn't exist yet.

The config architecture follows authority-boundary separation (developer constants / operator env / user data / system ephemeral) with a resolution chain: CLI flag → env var → XDG platform path → local fallback. This preserves portability, XDG compliance, and override capability while preventing scattered `os.getenv()` calls.

Security, reliability, and concurrency fixes are deliberately excluded from this phase. They depend on the config layer and get their own phases (B and C) with narrower acceptance boundaries.

---

## 3. Scope

### In scope

- [ ] **Domain-aligned config package**: Create `backend/config/` with Pydantic-schema modules per domain (`llm.py`, `scraping.py`, `scoring.py`, `generator.py`, `contact.py`, `app.py`). No monolithic `settings.py`.
- [ ] **Config resolution hierarchy**: CLI flag (`--config-dir`) → env var (`JHM_CONFIG_DIR`) → `$XDG_CONFIG_HOME/JustHireMe/` → `~/.config/JustHireMe/` → `./data/config/`. The config layer resolves the path at startup; consumers don't know or care where it came from.
- [ ] **Centralized settings accessor**: `from backend.config import settings` exposes `settings.llm.model`, `settings.scraper.timeout`, etc. No scattered `os.getenv()` in production code after this phase.
- [ ] **Startup validation**: Config validates at app boot — malformed YAML, missing required values, or out-of-range values produce a clear error message and abort startup.
- [ ] **Full CI test suite**: All backend test files (`test_api.py`, `test_graph.py`, `test_paths.py`, `test_mcp_server.py`, `test_regressions.py`) run on every push. Currently only regressions run.

### Out of scope

- Security remediation (API keys in SQLite/URLs/stdout — Phase B)
- `except: pass` → logged warnings (Phase C)
- WebSocket async-safety / SQLite WAL / concurrency (Phase C)
- Frontend error handling fixes (SettingsModal, ProfileView — Phase C)
- Build config fixes (updater, bundle targets — Phase C)
- OS keychain integration (not on current roadmap)
- Monolith splitting (deferred)
- All feature work (Phase D+)

---

## 4. Requirements

### Functional Requirements

| # | Requirement | Priority |
|---|-------------|----------|
| F1 | All runtime-configurable values loaded from typed config objects, not source literals | `Must` |
| F2 | Config resolution follows hierarchy: CLI → env → XDG → local fallback | `Must` |
| F3 | Config validates at startup — bad config fails fast with specific error message | `Must` |
| F4 | Schema defines value bounds (ranges, allowed values, types) — runtime coercion is explicit | `Must` |
| F5 | Config files organized by domain boundary, not a single monolithic file | `Must` |
| F6 | Every config value has a known owner (dev constant / operator env / user data / system ephemeral) | `Must` |
| F7 | All backend tests run in CI — no test file excluded | `Must` |
| F8 | Logging config (level, format, destination) is part of the config schema | `Should` |

### Non-Functional Requirements

| # | Requirement | Notes |
|---|-------------|-------|
| NF1 | No new hardcoded values introduced | Every new constant goes through config layer |
| NF2 | Config access is synchronous and cheap | Hot-path reads (scoring, loops) must not allocate |
| NF3 | Config is immutable after startup | Runtime changes require restart — no hot-reload in Phase A |
| NF4 | Missing optional values produce defaults, not errors | Only required fields abort startup |

---

## 5. Implementation Plan

### Guarantees, not mechanisms

Tasks are framed as acceptance guarantees. The implementation technique is chosen by the agent and verified against the guarantee.

### Tasks

**Workstream 1: Config resolution core**

- [ ] `[AFK]` **Task 1.1:** A config path resolver exists that implements the hierarchy: CLI `--config-dir` → `JHM_CONFIG_DIR` env var → `$XDG_CONFIG_HOME/JustHireMe/` → `~/.config/JustHireMe/` → `./data/config/`. The resolved path is a single `pathlib.Path`, available at import time.
- [ ] `[AFK]` **Task 1.2:** A startup validation gate exists that loads all config modules and either produces a valid `Settings` root object or exits with a specific error message identifying the invalid value, its source file, and the expected format.

**Workstream 2: Domain config modules**

- [ ] `[AFK]` **Task 2.1:** LLM config module exists (`backend/config/llm.py`). Covers: provider base URLs, default model names (from `_DEFAULT_MODELS`), per-step provider overrides, API key env-var names, request timeouts. Schema validates model names are non-empty strings; provider URLs are valid URLs. ~40 extracted values.
- [ ] `[AFK]` **Task 2.2:** Scraping config module exists (`backend/config/scraping.py`). Covers: source URLs and API endpoints (Apify, Greenhouse, Lever, Ashby, Workable, RemoteOK, HN, Reddit, GitHub, X/Twitter), rate limits, timeouts, max results per source. ~35 extracted values.
- [ ] `[AFK]` **Task 2.3:** Scoring config module exists (`backend/config/scoring.py`). Covers: rubric weights, score caps, seniority thresholds, tech taxonomy categories, quality gate thresholds, semantic match weights. ~100+ extracted values (taxonomy dominates).
- [ ] `[AFK]` **Task 2.4:** Generator config module exists (`backend/config/generator.py`). Covers: PDF defaults (fonts, scales, margins, colors), word limits per section, template paths, output directory. ~30 extracted values.
- [ ] `[AFK]` **Task 2.5:** Contact config module exists (`backend/config/contact.py`). Covers: Hunter.io and Proxycurl API endpoints, priorities, timeouts, max lookups per session. ~15 extracted values.
- [ ] `[AFK]` **Task 2.6:** App config module exists (`backend/config/app.py`). Covers: ghost mode interval, score thresholds, WebSocket heartbeat timeout, port defaults, lead freshness duration, polling intervals. ~15 extracted values.
- [ ] `[AFK]` **Task 2.7:** Logging config module exists (`backend/config/logging.py`). Covers: log level, format (structured vs plain), destination (stderr, file path), correlation context fields. ~5 values, but defines the contract for Phase C.

**Workstream 3: Migration wiring**

- [ ] `[AFK]` **Task 3.1:** All production code in `main.py` that currently reads hardcoded values is updated to read from `settings.<domain>.<key>` instead. No behavior change — only the value source changes.
- [ ] `[AFK]` **Task 3.2:** Same for `db/client.py` — all hardcoded thresholds, paths, and limits migrated to config accessors.
- [ ] `[AFK]` **Task 3.3:** Same for all 21 agent modules — `scout.py`, `free_scout.py`, `x_scout.py`, `generator.py`, `evaluator.py`, `scoring_engine.py`, etc. Each module imports config from its domain module or the shared `settings` object.
- [ ] `[AFK]` **Task 3.4:** Zero new `os.getenv()` calls in any modified file. All env access routes through the config layer.

**Workstream 4: CI verification**

- [ ] `[AFK]` **Task 4.1:** `.github/workflows/ci.yml` runs all backend test files, not just `test_regressions.py`. The full suite passes before this phase is considered done.

**Blocking relationships:**
- Task 1.1 unblocked (foundation)
- Task 1.2 blocked by Task 1.1 (needs resolver)
- Tasks 2.1–2.7 unblocked (schema design independent of resolver)
- Tasks 3.1–3.4 blocked by 2.1–2.7 (need config modules before wiring)
- Task 4.1 unblocked (CI config, independent)

---

## 6. API / Interface Design

### Config accessor interface

```python
# Usage — NOT literal implementation:
from backend.config import settings

# Typed accessor returns validated object or raises at startup
settings.llm.default_model           # "llama3"  (str, non-empty)
settings.scraper.timeout              # 30  (int, 1-300)
settings.scorer.rubric_weights        # {"role": 18, "stack": 27, ...}  (dict, validated keys)
settings.app.ghost_mode_interval      # 6  (int, hours, 1-72)
settings.app.lead_max_age_days        # 7  (int, 1-90)
settings.generator.pdf.page_size      # "A4"  (Literal["A4", "Letter"])
settings.logging.level                # "INFO"  (Literal["DEBUG", "INFO", "WARN", "ERROR"])
```

### User-facing config layout (`data/config/`)

```
data/config/
├── sources.yaml       # Job sources — user adds/removes/enables
├── filters.yaml       # Quality gate thresholds, keyword filters
└── ghost_mode.yaml    # Automation schedule, intervals
```

These files are loaded at startup. Malformed YAML produces a clear error naming the file and the parse failure.

---

## 7. Config Resolution Architecture

```
CLI --config-dir PATH             (highest priority, dev/test)
    ↓
JHM_CONFIG_DIR env var            (operator override, CI/CD)
    ↓
$XDG_CONFIG_HOME/JustHireMe/       (platform convention)
    ↓
~/.config/JustHireMe/              (XDG fallback)
    ↓
./data/config/                     (local repo fallback, dev convenience)
```

Resolution is one-shot at startup. The result is cached as a `pathlib.Path`. All config modules load from this path for user-facing files; developer-owned config (`backend/config/*.py`) always loads from Python module path regardless of this hierarchy.

---

## 8. Error Handling Map

| Scenario | Expected behaviour | Logged? | User-facing message |
|----------|--------------------|---------|---------------------|
| YAML parse failure in `sources.yaml` | Startup aborts — error identifies file and line | Yes — CRITICAL | "Config file data/config/sources.yaml is invalid: [parse error details]" |
| Config value out of range (e.g., timeout = -1) | Startup aborts — error names the field, value, and allowed range | Yes — CRITICAL | "Config value [app.ghost_mode_interval] = -1 is invalid. Must be between 1 and 72." |
| Required env var not set (e.g., `JHM_CONFIG_DIR` referenced but resolved later) | Uses next level in hierarchy — never fails on missing optional env | No (expected) | None |
| Config module import error (e.g., Pydantic validation error) | Startup aborts with Python traceback + human-readable summary | Yes — CRITICAL | "Internal config error: [summary]. This is a bug — report it." |
| User-facing config file doesn't exist | Uses defaults defined in `backend/config/*.py` — creates missing file with defaults | Yes — INFO | None (silent creation) |

---

## 9. Trust & Autonomy Boundaries

All Phase A tasks are **deterministic** — config extraction, schema definition, and value migration are mechanical transformations with no judgment calls. The config architecture is designed so that Phase B (security) and Phase C (reliability) are also deterministic.

The autonomy boundary intent: the config layer must never make the system feel more autonomous. Every config value's provenance should be traceable. If a value is user-owned, it comes from a user file in `data/config/`. If it's developer-owned, it comes from a Python module in `backend/config/`. The boundary is structural, not documented.

---

## 10. Validation Checklist

### Automated tests

- [ ] Config loads from all hierarchy levels — test with CLI flag set, env var set, XDG path, local fallback
- [ ] Config validation rejects out-of-range values — test with one invalid value per domain
- [ ] Config validation rejects missing required values — test with empty config per file
- [ ] Config accepts valid values — test with known-good config from existing defaults
- [ ] All 100+ backend tests pass in CI — regression tests + API + graph + paths + MCP

### Manual checks

- [ ] Run app with no config files — confirm defaults are created in `data/config/`
- [ ] Provide malformed YAML in `sources.yaml` — confirm startup fails with specific error
- [ ] Set `JHM_CONFIG_DIR` to an empty directory — confirm app uses defaults
- [ ] Remove all config — confirm app falls back to `./data/config/` and creates defaults
- [ ] `git grep 'os\.getenv'` in `backend/` — confirm only the config resolver itself uses it
- [ ] `git grep 'os\.environ'` in `backend/` — confirm same constraint

### Code quality gates

- [ ] Zero new hardcoded values introduced in modified files
- [ ] All new schemas use Pydantic with explicit type annotations and validation constraints
- [ ] Config modules organized by domain — no single `config.py`
- [ ] No `except: pass` in any config module code
- [ ] `.env.example` updated with all env vars the config layer recognizes
- [ ] Branch is clean — no unrelated changes

---

## 11. Open Questions

None remaining.

---

## 12. Decisions Log

| Date | Decision | Reason | Alternatives considered |
|------|----------|--------|-------------------------|
| 2026-05-13 | Authority-boundary config layers | Prevents chaos from extracting 150+ hardcodes | Monolithic settings.py, flat config.yaml |
| 2026-05-13 | Pydantic validation for all config objects | Malformed config fails fast, drift traceable | Bare dicts, unvalidated YAML |
| 2026-05-13 | Domain-aligned config files | Mirrors code organization, prevents merge conflicts | Single config.py, single config.yaml |
| 2026-05-13 | Infra phase (horizontal) — exempt from vertical-slice rule | Phase A has no user-visible output | Forcing vertical structure on infra work |
| 2026-05-13 | Solo fork, watch upstream | Phase A makes deep structural changes upstream wouldn't accept | Keeping changes PR-friendly |
| 2026-05-13 | Config resolution hierarchy (CLI → env → XDG → fallback) | Portable across platforms, XDG-compliant on Linux, overridable for dev | Hardcoded path, single env var |
| 2026-05-13 | Autonomy boundaries: deterministic = AFK, judgment = HITL | Prevents agent sprawl and trust erosion | Per-task AFK/HITL tagging without architectural reasoning |
| 2026-05-13 | Phase scope narrowed: config architecture only | Security (B) and reliability (C) are distinct workstreams with separate acceptance boundaries | Single mega-refactor phase |

---

_Last updated: 2026-05-13 — Agent_
