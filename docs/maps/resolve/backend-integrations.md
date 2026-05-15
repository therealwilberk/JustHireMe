# Resolve: backend-integrations (✅ DONE)

Source: `docs/maps/backend-integrations.md`
Branch: `fix/resolve-integrations`

## Pass 1: 🔴 DEAD code removal ✅

| Item | Result |
|------|--------|
| `import sys` in actuator.py:5 | Removed ✂️ |
| `_knowledge()` in help_agent.py:275 | Removed ✂️ (confirmed dead — only `_focused_knowledge()` called) |

## Pass 2: 🔵 HARDCODED → config ✅

**Existing config keys wired:**
- `contact_lookup.py:60` UA → `settings.scraping.user_agents.contact_lookup`
- `github_ingestor.py:34` timeout=10 → `settings.scraping.timeouts.default_http`
- `actuator.py:385` timeout=30000 → `settings.scraping.timeouts.page_load`
- `github_ingestor.py` GITHUB_API → `settings.scraping.api_urls.github_api_base` (new key)

**New config keys added:**
| Key | Value | Files wired |
|-----|-------|-------------|
| `limits.fill_delay_ms` | 500 | actuator.py |
| `limits.selectors_cache_ttl` | 86400 | selectors.py |
| `limits.github_max_repos` | 12 | github_ingestor.py |
| `limits.github_fork_min_stars` | 10 | github_ingestor.py |
| `api_urls.groq_api_base` | `https://api.groq.com/openai/v1` | actuator.py |
| `api_urls.nvidia_api_base` | `https://integrate.api.nvidia.com/v1` | actuator.py |
| `api_urls.browser_runtime_download_base` | GitHub releases URL | browser_runtime.py |

## Pass 3: 🟡 SUSPECT items ✅

| Item | Action |
|------|--------|
| `_resolve` import bypass in portfolio_ingestor.py:80 | Fixed — uses `resolve_config` instead |
| Other 🟡 items | Noted as intentional/deferred — no change |

## Verification ✅
- `pytest tests/`: 326 passed, 2 deselected
- `from main import app`: 59 routes

## Stats
- 10 files changed: +50 / -48
