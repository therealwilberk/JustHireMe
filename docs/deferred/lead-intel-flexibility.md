# Lead Intel Flexibility — Non-Tech Job Support

**Status:** Pending

**Source:** `docs/maps/backend-evaluators.md` — `agents/lead_intel.py`

## Description

`lead_intel.py` is heavily hardcoded for tech/AI job leads — term lists, scoring weights,
outreach templates, location lists, and fit bullets all assume a technical audience.
This makes it unsuitable for non-tech job categories (admin, sales, design, operations, etc.).

## Hardcoded Items

| Item | Lines | Problem |
|------|-------|---------|
| `TECH_TERMS` | 9-13 | 22 tech-specific terms (python, fastapi, react, llm, etc.) |
| `TECH_LABELS` | 15-38 | 22 tech-specific display labels |
| `INTENT_TERMS` | 40-44 | 14 terms (hiring, job opening, internship, etc.) |
| `JOB_TERMS` | 46-49 | 10 terms (full-time, part-time, remote, etc.) |
| `NOISE_TERMS` | 56-59 | 8 terms (course, newsletter, tutorial, podcast, etc.) |
| `location_from_text` | 105-122 | City list includes SF/NY/London/Berlin/India cities only |
| `signal_quality` | 146-191 | All scoring values (base 18, tech +25, intent +24, etc.) assume tech context |
| `outreach_drafts` | 228-257 | Templates hardcoded for "AI automation, Python, React" |
| `fit_bullets` | 194-207 | Only generates tech-relevant bullets (automation, agent, react, fastapi) |
| `proof_snippet` | 210-216 | Fallback text is "AI automation, Python, React" |

## Effort Estimate

Large — requires:
1. Config-driven term lists (move to YAML or settings)
2. Config-driven scoring weights
3. Config-driven outreach templates (or remove them entirely)
4. Config-driven location lists
5. Non-tech fallback behavior for all extraction functions
6. Tests for non-tech categories

## Dependencies

None — self-contained module.
