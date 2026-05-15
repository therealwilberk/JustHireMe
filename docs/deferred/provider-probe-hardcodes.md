# Provider Probe Hardcodes

**Status:** Pending

The `services/provider_probe.py` module has several hardcoded provider URLs and API parameters that should be config-driven:

| Value | Line | Notes |
|-------|------|-------|
| `"https://api.anthropic.com/v1/messages"` | 39 | Anthropic messages endpoint — base URL is now in config, but full path could be |
| `"anthropic-version": "2023-06-01"` | 42 | Static API version — stable but hardcoded |
| `"https://api.openai.com/v1/models"` | 54 | OpenAI model list endpoint |
| `"https://api.groq.com/openai/v1/models"` | 60 | Groq model list endpoint |
| `"https://generativelanguage.googleapis.com/v1beta/openai/models"` | 66 | Gemini OpenAI-compatible endpoint |
| `"claude-haiku-4-5-20251001"` | 46 | Probe model — moved to `config` but keeping deferred for removal |

These should be centralized in `config/scraping.py` APISourceURLs (or a new `ProbeEndpoints` model) following the pattern used for ATS endpoints and scraping URLs.
