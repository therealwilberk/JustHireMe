# Map: Backend Evaluators
**File:** `docs/maps/backend-evaluators.md`
**Codebase path(s):** `backend/agents/`
**Files in scope:** 5
**Total lines:** ~2,186
**Generated:** 2026-05-15

---

## 1. Unit summary

The evaluators unit owns job-lead scoring, candidate profiling, and lead intelligence for JustHireMe. It spans five modules: a deterministic rubric engine (`scoring_engine.py`) that does the heavy lifting with keyword matching and weighted criteria; an LLM-led wrapper (`evaluator.py`) that can override or calibrate against the rubric; a lightweight feedback-rank learner (`feedback_ranker.py`) that adjusts signal scores from user labels; a semantic similarity module (`semantic.py`) that queries LanceDB vectors; and a lead-intel module (`lead_intel.py`) that classifies raw text into structured leads. The evaluator is the public face consumed by scanners, the ghost mode scheduler, graph workflows, and the MCP server. The scoring engine is the dependency backbone — it pulls from semantic and is pulled by evaluator, generator, and query_gen. Lead_intel is the other major export, consumed by scouts, the MCP server, routes, and quality_gate.

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `agents/evaluator.py` | 274 | LLM-led scoring with deterministic fallback | 🟢 dead prompt removed, truncation limits config-driven |
| 2 | `agents/scoring_engine.py` | 1,097 | Deterministic rubric scoring engine | 🟢 well-factored, many hardcoded values (domain data — acceptable) |
| 3 | `agents/feedback_ranker.py` | 176 | User-feedback-driven signal adjustment | 🟢 thresholds now config-driven |
| 4 | `agents/semantic.py` | 278 | Embedding-based semantic similarity | 🟢 graceful degradation, hardcoded stretch params (noted) |
| 5 | `agents/lead_intel.py` | 314 | Raw text to structured lead conversion | 🟡 tech-centric — deferred to docs/deferred/lead-intel-flexibility.md |

---

## 3. Detailed breakdown

### `agents/evaluator.py`

**Purpose:** Provides the public `score()` function that rates a job lead against a candidate profile. Delegates to an LLM when configured; otherwise falls back to the deterministic rubric from `scoring_engine.py`. The LLM receives the rubric output as calibration context, and hard safety caps from the rubric are enforced post-LLM.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from __future__ import annotations` | stdlib | yes | 🟢 — standard |
| `import json` | stdlib | yes | 🟢 |
| `from typing import List` | stdlib | yes (`_Score.match_points`) | 🟡 SUSPECT — `list` could be used directly in modern Pydantic |
| `from pydantic import BaseModel, Field` | 3rd-party | yes | 🟢 |
| `from logger import get_logger` | local | yes | 🟢 |
| `from agents.scoring_engine import build_proof_text, infer_experience_level, score_job_lead` | local | yes | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_log` | Logger | instance | throughout | 🟢 |
| `_SYSTEM_PROMPT` 1st def (lines 34-82) | str | ~50 lines | none | 🔴 DEAD — immediately overwritten by 2nd def (line 84) |
| `_SYSTEM_PROMPT` 2nd def (lines 84-131) | str | ~48 lines | `_score_with_llm` | 🟢 |

**Classes:**

#### `_Score(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Internal Pydantic model for LLM structured output parsing
- **Still needed:** yes
- **Flag:** 🟢

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| `__init__` | (inherited) | None | N/A | 🟢 |

**Functions:**

#### `_build_proof(candidate_data: dict) -> str`
- **Purpose:** Compatibility wrapper delegating to `build_proof_text`
- **Called by:** unknown within this unit — check cross-refs (likely old tests)
- **Calls:** `build_proof_text`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟡 SUSPECT — docstring says "used by older tests/imports"; verify callers

#### `_infer_experience_level(candidate_data: dict) -> str`
- **Purpose:** Compatibility wrapper delegating to `infer_experience_level`
- **Called by:** unknown within this unit — docstring says "query/evaluation tests"
- **Calls:** `infer_experience_level`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟡 SUSPECT — same orphan pattern as `_build_proof`

#### `_compact_json(value, limit: int = 14000) -> str`
- **Purpose:** JSON serialization with length truncation
- **Called by:** `_user_prompt`
- **Calls:** `json.dumps`
- **Side effects:** none
- **Hardcodes:** default limit 14000
- **Flag:** 🟢 — well-scoped helper

#### `_profile_prompt_payload(candidate_data: dict) -> dict`
- **Purpose:** Reorder and filter candidate profile fields for LLM context window efficiency
- **Called by:** `_user_prompt`
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** ordered key list (line 157-161)
- **Flag:** 🟢 — sensible ordering, acceptable hardcode

#### `_additional_profile_evidence(candidate_data: dict) -> str`
- **Purpose:** Format extra profile sections (certs, education, etc.) for LLM
- **Called by:** `_user_prompt`
- **Calls:** `json.dumps`
- **Side effects:** none
- **Hardcodes:** section key list (lines 172-175)
- **Flag:** 🟢

#### `_evaluator_llm_requested() -> bool`
- **Purpose:** Return True when the user has configured an LLM route
- **Called by:** `score`
- **Calls:** `db.client.get_setting` (lazy import)
- **Side effects:** none
- **Hardcodes:** key names (lines 196-199)
- **Flag:** 🟣 COUPLED — lazy-imports `db.client` inside function body; hardcodes setting key names

#### `_user_prompt(jd: str, candidate_data: dict, baseline: dict) -> str`
- **Purpose:** Build the complete LLM user prompt with JD, profile, proof, and baseline
- **Called by:** `_score_with_llm`
- **Calls:** `build_proof_text`, `_additional_profile_evidence`, `_compact_json`, `_profile_prompt_payload`
- **Side effects:** none
- **Hardcodes:** Truncation limits — JD 9000 chars (line 214), proof 7000 (line 220), baseline 5000 (line 223)
- **Flag:** 🔵 HARDCODED — truncation limits baked in with no config override

#### `_as_list(value) -> list[str]`
- **Purpose:** Normalize a value (list, scalar, None) into a deduplicated list of trimmed strings
- **Called by:** `_normalize_llm_result`
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** item cap 300 chars (line 240)
- **Flag:** 🟢

#### `_hard_cap(baseline: dict) -> tuple[int | None, str]`
- **Purpose:** Extract the lowest hard cap from the deterministic baseline's gap strings
- **Called by:** `_normalize_llm_result`
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** gap prefix strings "wrong-field cap", "seniority cap" (lines 248-252)
- **Flag:** 🟣 COUPLED — fragile string matching against `scoring_engine` gap format

#### `_normalize_llm_result(raw, baseline: dict) -> dict`
- **Purpose:** Parse LLM structured output, clamp score, apply hard caps, fill gaps from baseline
- **Called by:** `_score_with_llm`
- **Calls:** `_as_list`, `_hard_cap`
- **Side effects:** none
- **Hardcodes:** match_points cap at 7 (line 292), gaps cap at 8 (line 293), reason cap 500 (line 290)
- **Flag:** 🟢 — sensible, defensive defaults

#### `_score_with_llm(jd: str, candidate_data: dict, baseline: dict) -> dict`
- **Purpose:** Call the LLM with system+user prompts and parse the result
- **Called by:** `score`
- **Calls:** `call_llm` (lazy import from `llm`), `_normalize_llm_result`
- **Side effects:** API call to LLM provider
- **Hardcodes:** step name "evaluator" (line 303)
- **Flag:** 🟢

#### `score(jd: str, candidate_data: dict) -> dict`
- **Purpose:** Public entry point — return a 0-100 job match score
- **Called by:** `services/scanner.py` (lines 214, 284), `services/ghost.py` (line 148), `graph/__init__.py` (line 68), `mcp_server.py` (line 14), `tests/`
- **Calls:** `score_job_lead`, `_evaluator_llm_requested`, `_score_with_llm`
- **Side effects:** may call LLM API
- **Hardcodes:** none
- **Flag:** 🟢 — clean entry point

**Exports:**

| Export | Known importers |
|--------|----------------|
| `score` | `services/scanner.py`, `services/ghost.py`, `graph/__init__.py`, `mcp_server.py`, `tests/test_regressions.py` |
| `_build_proof` | unknown — likely old tests |
| `_infer_experience_level` | unknown — likely old tests |
| `_user_prompt` | `tests/test_regressions.py` (line 152) |

---

### `agents/scoring_engine.py`

**Purpose:** Deterministic scoring of lead-candidate fit. No LLM in the hot path — uses a fixed rubric with weighted criteria (role alignment, stack overlap, proof of work, seniority fit, constraints). Also builds proof text for the LLM path. Contains the 84-entry `TECH_TAXONOMY`, category mappings, role keywords, and capping logic. This is the largest and most complex file in the unit.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from __future__ import annotations` | stdlib | yes | 🟢 |
| `import re` | stdlib | yes | 🟢 |
| `from dataclasses import dataclass` | stdlib | yes | 🟢 |
| `from typing import Iterable` | stdlib | yes | 🟢 |
| `from logger import get_logger` | local | yes | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `TECH_TAXONOMY` | dict[str, tuple[str, ...]] | 84 entries | `_ALIAS_PATTERNS`, `_find_terms` | 🔵 HARDCODED — 84-entry taxonomy baked into Python module |
| `TECH_CATEGORY` | dict[str, str] | 84 category mappings | `_category_set`, `_direct_and_adjacent` | 🔵 HARDCODED — category mapping baked in |
| `ROLE_KEYWORDS` | dict[str, tuple[str, ...]] | 9 role categories | `_find_tags`, `analyze_posting` | 🔵 HARDCODED |
| `DELIVERABLE_KEYWORDS` | dict[str, tuple[str, ...]] | 14 deliverable types | `_find_tags`, `analyze_posting` | 🔵 HARDCODED |
| `WRONG_FIELD_TERMS` | tuple | 80+ non-tech roles | `analyze_posting` | 🔵 HARDCODED — includes unrelated engineering fields |
| `RED_FLAGS` | tuple | 14 red-flag phrases | `analyze_posting` | 🔵 HARDCODED |
| `COMMERCIAL_TERMS` | tuple | 10 commercial intent phrases | `analyze_posting` | 🔵 HARDCODED |
| `_ADJACENCY_BLOCKLIST` | set | 5 categories | `_direct_and_adjacent` | 🔵 HARDCODED |
| `_MONTHS` | dict | 12 month mappings | `_period_months` | 🟢 |
| `_ALIAS_PATTERNS` | list[tuple[str, Pattern]] | compiled regexes | `_find_terms` | 🟢 — derived from TAXONOMY, not hardcoded per se |

**Classes:**

#### `CriterionScore`
- **Inherits from:** N/A (dataclass, frozen=True)
- **Purpose:** Single rubric criterion result with name, score, weight, reason
- **Still needed:** yes
- **Flag:** 🟢

#### `ScoreResult`
- **Inherits from:** N/A (dataclass, frozen=True)
- **Purpose:** Complete scoring output with score, reason, match_points, gaps, criteria
- **Still needed:** yes
- **Flag:** 🟢

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| `as_dict` | self | dict | Strip criteria for LLM-friendly output | 🟢 |

#### `CandidateEvidence`
- **Inherits from:** N/A (dataclass)
- **Purpose:** Parsed candidate profile with skills, terms, projects, experience, level
- **Still needed:** yes
- **Flag:** 🟢

#### `PostingSignals`
- **Inherits from:** N/A (dataclass)
- **Purpose:** Parsed job posting with terms, flags, constraints, quality features
- **Still needed:** yes
- **Flag:** 🟢

**Functions:**

#### `clamp(n: float, lo: int = 0, hi: int = 100) -> int`
- **Purpose:** Clamp a float to [lo, hi] integer range
- **Called by:** `_stack_overlap`, `_proof_strength`, `_job_constraints`, `_weighted_total`, `_apply_caps`
- **Flag:** 🟢

#### `build_proof_text(candidate_data: dict) -> str`
- **Purpose:** Build a human-readable proof summary from projects, experience, skills
- **Called by:** `evaluator.py:score`, `evaluator.py:_user_prompt`, `_profile_text`
- **Flag:** 🟢

#### `_period_months(period: str) -> int`
- **Purpose:** Estimate months from a date range string
- **Called by:** `_total_work_months`
- **Hardcodes:** "2099-12" sentinel for "present" (line 386)
- **Flag:** 🔵 HARDCODED — year 2099 sentinel value

#### `_total_work_months(candidate_data: dict) -> int`
- **Purpose:** Sum months of non-intern professional experience
- **Called by:** `infer_experience_level`, `analyze_candidate`
- **Hardcodes:** intern/trainee/student keywords (line 417)
- **Flag:** 🟢

#### `infer_experience_level(candidate_data: dict) -> str`
- **Purpose:** Estimate seniority from experience months, senior titles, project count
- **Called by:** `evaluator.py:score` (via import), `analyze_candidate`, `agents/query_gen.py`
- **Hardcodes:** senior title keywords (line 443), thresholds 36/60/24 months (lines 447-454)
- **Flag:** 🔵 HARDCODED — months thresholds baked in

#### `_squash(text: str) -> str`
- **Purpose:** Normalize whitespace
- **Called by:** many
- **Flag:** 🟢

#### `_alias_regex(alias: str) -> re.Pattern[str]`
- **Purpose:** Build a fuzzy regex for a tech term alias
- **Called by:** module-level `_ALIAS_PATTERNS` init, `_contains_phrase`
- **Flag:** 🟢

#### `_contains_phrase(text: str, phrase: str) -> bool`
- **Purpose:** Check if a phrase (as alias regex) appears in text
- **Called by:** `_find_tags`, `analyze_posting`
- **Flag:** 🟢

#### `_find_terms(text: str) -> set[str]`
- **Purpose:** Find all matching tech taxonomy terms in text
- **Called by:** `analyze_candidate`, `analyze_posting`
- **Flag:** 🟢

#### `_find_tags(text: str, taxonomy: dict) -> set[str]`
- **Purpose:** Generic tag finder for role/deliverable keywords
- **Called by:** `analyze_candidate`, `analyze_posting`
- **Flag:** 🟢

#### `_split_stack(value) -> list[str]`
- **Purpose:** Split a stack string on common delimiters
- **Called by:** `analyze_candidate`
- **Flag:** 🟢

#### `_candidate_location(summary: str) -> str`
- **Purpose:** Extract candidate location from profile summary
- **Called by:** `analyze_candidate`
- **Hardcodes:** Location list includes "india", "united states", "usa", "us", "canada", "uk", "europe" (line 509)
- **Flag:** 🔵 HARDCODED — location list baked in

#### `_profile_text(candidate_data: dict) -> str`
- **Purpose:** Concatenate summary + proof text
- **Called by:** `analyze_candidate`
- **Flag:** 🟢

#### `analyze_candidate(candidate_data: dict) -> CandidateEvidence`
- **Purpose:** Full candidate analysis — skills, projects, experience, role tags, deliverables, level
- **Called by:** `score_job_lead`
- **Flag:** 🟢

#### `_field(text: str, name: str) -> str`
- **Purpose:** Extract a named field from structured text
- **Called by:** `_title_from_text`, `_company_from_text`
- **Flag:** 🟢

#### `_title_from_text(text: str, fallback: str) -> str`
- **Purpose:** Extract job title from posting text
- **Called by:** `analyze_posting`
- **Flag:** 🟢

#### `_company_from_text(text: str) -> str`
- **Purpose:** Extract company name from posting text
- **Called by:** `analyze_posting`
- **Flag:** 🟢

#### `_extract_years(text: str) -> int`
- **Purpose:** Extract max years-of-experience requirement
- **Called by:** `analyze_posting`
- **Flag:** 🟢

#### `_budget_amount(text: str) -> int | None`
- **Purpose:** Extract dollar budget from text
- **Called by:** `analyze_posting`
- **Flag:** 🟢

#### `_quality_features(text, terms, title, company) -> list[str]`
- **Purpose:** List quality signals in a posting
- **Called by:** `analyze_posting`
- **Hardcodes:** length thresholds 240 (line 640), 2-term minimum (line 642), next-step regex (line 644)
- **Flag:** 🔵 HARDCODED — length and term thresholds baked in

#### `analyze_posting(raw_text, default_title) -> PostingSignals`
- **Purpose:** Full posting analysis — terms, role tags, deliverables, wrong-field, red flags
- **Called by:** `score_job_lead`
- **Flag:** 🟢

#### `_category_set(terms: Iterable[str]) -> set[str]`
- **Purpose:** Map tech terms to their categories
- **Called by:** `_direct_and_adjacent`
- **Flag:** 🟢

#### `_sorted_terms(terms: Iterable[str]) -> list[str]`
- **Purpose:** Case-insensitive sorted deduplicated terms
- **Called by:** `_fmt_terms`, `_evidence_line`, `_result`
- **Flag:** 🟢

#### `_fmt_terms(terms, empty) -> str`
- **Purpose:** Format terms as comma-separated string, max 8
- **Called by:** `_stack_overlap`, `_result`, `_evidence_line`
- **Flag:** 🟢

#### `_direct_and_adjacent(posting, candidate) -> tuple`
- **Purpose:** Classify required terms as direct-match, adjacent, or missing
- **Called by:** `score_job_lead`
- **Hardcodes:** `_ADJACENCY_BLOCKLIST` (line 722)
- **Flag:** 🔵 HARDCODED — adjacency blocklist

#### `_role_alignment(posting, candidate) -> CriterionScore`
- **Purpose:** Score role/department alignment
- **Called by:** `score_job_lead`
- **Hardcodes:** score thresholds 88/64/78/55/60/38/22 (lines 756-776), weight 18 (line 746)
- **Flag:** 🔵 HARDCODED — score thresholds and weight baked in

#### `_stack_overlap(posting, candidate, weight) -> CriterionScore`
- **Purpose:** Score tech stack overlap with adjacent-term credit
- **Called by:** `score_job_lead`
- **Hardcodes:** adjacent weight 0.30 (line 788), formula constants
- **Flag:** 🔵 HARDCODED — blending ratios

#### `_proof_strength(posting, candidate, weight) -> CriterionScore`
- **Purpose:** Score evidence strength — project/experience proof vs listed-only skills
- **Called by:** `score_job_lead`
- **Hardcodes:** term weights 1.0/0.75/0.45 (lines 828-835), blend ratio 0.78/0.22 (line 842)
- **Flag:** 🔵 HARDCODED — term evidence weights

#### `_seniority_fit(posting, candidate) -> CriterionScore`
- **Purpose:** Score seniority fit vs requirements
- **Called by:** `score_job_lead`
- **Hardcodes:** level-to-years mapping (line 858), gap-to-score thresholds (lines 874-883), weight 20
- **Flag:** 🔵 HARDCODED — level mapping and score bands

#### `_job_constraints(posting, candidate) -> CriterionScore`
- **Purpose:** Score location/remote/red-flag/quality constraints
- **Called by:** `score_job_lead`
- **Hardcodes:** base 78, remote +8, onsite -14, location -28, red flag -35, thin -18, detailed +5 (lines 891-910), weight 15
- **Flag:** 🔵 HARDCODED — all adjustment values baked in

#### `_weighted_total(criteria) -> int`
- **Purpose:** Compute weighted average score across criteria
- **Called by:** `score_job_lead`
- **Flag:** 🟢

#### `_seniority_cap(posting, candidate) -> tuple | None`
- **Purpose:** Compute hard seniority cap based on experience vs requirement
- **Called by:** `_apply_caps`
- **Hardcodes:** thresholds — 6 months/3y/5y/7y (lines 927-939), cap values 30/38/45/48
- **Flag:** 🔵 HARDCODED — all thresholds and cap values baked in

#### `_apply_caps(score, posting, candidate, direct, adjacent) -> tuple`
- **Purpose:** Apply all hard caps (wrong-field, seniority, stack, confidence)
- **Called by:** `score_job_lead`
- **Hardcodes:** wrong-field cap 15 (line 952), stack no-direct cap 42/52 (line 957), thin-posting cap 68 (line 960)
- **Flag:** 🔵 HARDCODED — cap values baked in

#### `_evidence_line(candidate, terms) -> str`
- **Purpose:** Build evidence string for matched terms showing project/experience context
- **Called by:** `_result`, `_proof_strength`
- **Flag:** 🟢

#### `_result(final_score, criteria, ...) -> ScoreResult`
- **Purpose:** Build the final ScoreResult with reasons, match_points, gaps
- **Called by:** `score_job_lead`
- **Hardcodes:** reason cap 500 (line 999), match_points threshold 58 (line 1004), cap 7 (line 1019), gaps threshold 58 (line 1011), cap 8 (line 1020)
- **Flag:** 🔵 HARDCODED — thresholds and caps for output formatting

#### `_with_weight(c, weight) -> CriterionScore`
- **Purpose:** Return a copy of a criterion with a different weight
- **Called by:** `score_job_lead`
- **Flag:** 🟢

#### `_semantic_criterion(jd, candidate_data, weight) -> CriterionScore | None`
- **Purpose:** Build a Semantic-fit criterion from embedding similarity; returns None on failure
- **Called by:** `score_job_lead`
- **Calls:** `agents.semantic.semantic_fit` (lazy import)
- **Flag:** 🟣 COUPLED — lazy-imports internal function from sibling module

#### `score_job_lead(jd: str, candidate_data: dict) -> ScoreResult`
- **Purpose:** Main entry point — run full deterministic scoring pipeline
- **Called by:** `evaluator.py:score`, `tests/`
- **Calls:** `analyze_candidate`, `analyze_posting`, `_role_alignment`, `_seniority_fit`, `_job_constraints`, `_semantic_criterion`, `_stack_overlap`, `_proof_strength`, `_weighted_total`, `_apply_caps`, `_result`
- **Hardcodes:** Rubric weights — role 15/18, stack 20/27, proof 18/20, seniority 20, constraints 12/15, semantic 15 (lines 1073-1089)
- **Flag:** 🔵 HARDCODED — rubric weights change based on semantic availability; values baked in

**Exports:**

| Export | Known importers |
|--------|----------------|
| `build_proof_text` | `evaluator.py`, `tests/` |
| `infer_experience_level` | `evaluator.py`, `agents/query_gen.py`, `tests/` |
| `score_job_lead` | `evaluator.py`, `tests/` |
| `TECH_TAXONOMY` | `agents/generator.py` (lines 399, 425, 459) |
| `ScoreResult` | `evaluator.py` |
| `_budget_amount` | `tests/test_observability.py` |

---

### `agents/feedback_ranker.py`

**Purpose:** Learns from user feedback labels (good/trash/not_relevant etc.) to adjust lead signal scores. Builds a feature-weight model from labeled examples and applies a delta to new leads. Small, focused, clean module.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `import re` | stdlib | yes | 🟢 |
| `from urllib.parse import urlparse` | stdlib | yes | 🟢 |
| `from logger import get_logger` | local | yes | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `POSITIVE_LABELS` | dict | 3 entries | `_label_weight` | 🔵 HARDCODED — label weights baked in |
| `NEGATIVE_LABELS` | dict | 7 entries | `_label_weight` | 🔵 HARDCODED — includes "not_ai" at -1.1 which is an aggressive penalty |
| `FEATURE_WEIGHTS` | dict | 10 feature types | `_feature_weight` | 🔵 HARDCODED — feature type weights baked in |

**Functions:**

#### `_norm(value: str) -> str`
- **Purpose:** Normalize string — squash whitespace, lowercase, cap at 80 chars
- **Called by:** `_company_key`, `lead_features`, `_label_weight`
- **Flag:** 🟢

#### `_list(value) -> list[str]`
- **Purpose:** Normalize to list of trimmed strings
- **Called by:** `lead_features`
- **Flag:** 🟢

#### `_company_key(lead: dict) -> str`
- **Purpose:** Extract a normalized company identifier from lead dict or URL
- **Called by:** `lead_features`
- **Flag:** 🟢

#### `lead_features(lead: dict) -> set[str]`
- **Purpose:** Extract feature strings from a lead dict
- **Called by:** `build_model`, `apply_feedback_learning`
- **Flag:** 🟢

#### `_label_weight(label: str) -> float`
- **Purpose:** Look up feedback label weight
- **Called by:** `build_model`
- **Flag:** 🟢 — but backed by hardcoded LABELS dicts

#### `build_model(examples: list[dict]) -> dict[str, dict]`
- **Purpose:** Build a feature-weight model from labeled examples
- **Called by:** `apply_feedback_learning`
- **Flag:** 🟢

#### `_feature_weight(feature: str) -> float`
- **Purpose:** Look up feature-type weight by prefix
- **Called by:** `apply_feedback_learning`
- **Flag:** 🟢 — but backed by hardcoded FEATURE_WEIGHTS dict

#### `apply_feedback_learning(lead: dict, examples: list[dict], max_delta: int = 18) -> dict`
- **Purpose:** Main entry point — apply learned feedback to adjust lead signal score
- **Called by:** `db/client.py` (lines 754, 771), `tests/`
- **Hardcodes:** max_delta default 18 (line 125), confidence divisor 5 (line 141), contribution threshold 0.35 (line 144), top-k 3 (line 157)
- **Flag:** 🔵 HARDCODED — delta cap, confidence scaling, contribution threshold baked in

**Exports:**

| Export | Known importers |
|--------|----------------|
| `apply_feedback_learning` | `db/client.py` (lines 754, 771), `tests/test_regressions.py` (lines 555, 585) |

---

### `agents/semantic.py`

**Purpose:** Computes a 0-100 semantic similarity score between a JD and the candidate's embedded profile. Uses SentenceTransformer (`all-MiniLM-L6-v2`) to embed the JD and searches LanceDB tables (`skills`, `projects`) that were populated by the ingestor. Returns `None` on any failure so callers transparently fall back to keyword scoring.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `from __future__ import annotations` | stdlib | yes | 🟢 |
| `import hashlib` | stdlib | yes | 🟢 |
| `from typing import Optional` | stdlib | yes | 🟢 |
| `from logger import get_logger` | local | yes | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_log` | Logger | instance | throughout | 🟢 |

**Functions:**

#### `_h(value: str) -> str`
- **Purpose:** MD5 hash first 12 chars for fallback ID generation
- **Called by:** `_profile_scope`
- **Flag:** 🟢

#### `_embed_jd(text: str) -> Optional[list[float]]`
- **Purpose:** Embed JD string to 384-dim vector; returns None on failure
- **Called by:** `semantic_fit`
- **Calls:** `agents.ingestor._emb` (lazy import)
- **Flag:** 🟣 COUPLED — imports private `_emb` from `agents.ingestor`; 🔵 HARDCODED — model `all-MiniLM-L6-v2` baked into ingestor, referenced in docstring

#### `_vec_store()`
- **Purpose:** Get LanceDB vector store reference; returns None on failure
- **Called by:** `_table_search`, `semantic_fit`
- **Calls:** `db.client.vec` (lazy import)
- **Flag:** 🟣 COUPLED — lazy-imports `db.client.vec`

#### `_available_tables(store) -> set[str]`
- **Purpose:** List available LanceDB tables; returns empty set on failure
- **Called by:** `_table_search`, `semantic_fit`
- **Flag:** 🟢

#### `_profile_scope(candidate_data: dict | None) -> dict | None`
- **Purpose:** Compute allowed vector IDs scoped to the current candidate profile
- **Called by:** `semantic_fit`
- **Flag:** 🟢

#### `_ids_where_clause(ids: set[str]) -> str`
- **Purpose:** Build LanceDB SQL WHERE clause from a set of IDs
- **Called by:** `_table_search`
- **Flag:** 🟢

#### `_filter_rows(rows, allowed_ids, limit) -> list[dict]`
- **Purpose:** Filter query results to allowed IDs
- **Called by:** `_table_search`
- **Flag:** 🟢

#### `_table_search(table_name, query, limit, *, allowed_ids, store, available_tables) -> list[dict]`
- **Purpose:** Search a LanceDB table with cosine metric fallback and scope filtering
- **Called by:** `semantic_fit`
- **Hardcodes:** request_limit fallback formula (line 152)
- **Flag:** 🟢 — well-structured graceful fallback

#### `_row_label(row, fallback) -> str`
- **Purpose:** Extract label from a LanceDB result row
- **Called by:** `semantic_fit`
- **Flag:** 🟢

#### `_row_similarity(row) -> float`
- **Purpose:** Convert LanceDB distance/score to [0,1] similarity
- **Called by:** `semantic_fit`
- **Flag:** 🟢

#### `semantic_fit(jd_text, *, candidate_data, top_skills, top_projects) -> Optional[dict]`
- **Purpose:** Main entry point — compute 0-100 semantic-fit score
- **Called by:** `scoring_engine.py:_semantic_criterion`
- **Hardcodes:** `top_skills=6`, `top_projects=3` (lines 193-194); signal blend 0.40/0.60 (lines 250-251); combined blend 0.60/0.40 (line 259); stretch lower 0.15, range 0.55 (line 264)
- **Flag:** 🔵 HARDCODED — blend weights and stretch parameters baked in

**Exports:**

| Export | Known importers |
|--------|----------------|
| `semantic_fit` | `scoring_engine.py` (lazy import, line 1037), `tests/test_regressions.py` (lines 236, 242) |

---

### `agents/lead_intel.py`

**Purpose:** Converts raw text (and optionally URL) into a structured lead dict. Used by scouts, the MCP server, routes, and quality gate. Provides classification, budget/company/location extraction, outreach draft generation, and signal quality scoring. Has a confirmed bug in `classify_kind`.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `import hashlib` | stdlib | yes | 🟢 |
| `import re` | stdlib | yes | 🟢 |
| `from urllib.parse import urlparse` | stdlib | yes | 🟢 |
| `from logger import get_logger` | local | yes | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `TECH_TERMS` | tuple | 20 terms | `tech_stack_from_text`, `signal_quality` | 🔵 HARDCODED |
| `TECH_LABELS` | dict | 22 mappings | `tech_stack_from_text` | 🔵 HARDCODED |
| `INTENT_TERMS` | tuple | 13 terms | `signal_quality` | 🔵 HARDCODED |
| `JOB_TERMS` | tuple | 8 terms | `classify_kind` | 🔵 HARDCODED |
| `URGENCY_TERMS` | tuple | 9 terms | `urgency_from_text`, `signal_quality` | 🔵 HARDCODED |
| `NOISE_TERMS` | tuple | 8 terms | `signal_quality` | 🔵 HARDCODED |

**Functions:**

#### `lead_id(prefix: str, value: str) -> str`
- **Purpose:** Generate MD5-hashed lead ID
- **Called by:** `manual_lead_from_text`
- **Flag:** 🟢

#### `clean_text(text: str) -> str`
- **Purpose:** Normalize whitespace
- **Called by:** many functions in file, also imported by `agents/quality_gate.py`
- **Flag:** 🟢

#### `has_any(text: str, terms: tuple[str, ...]) -> bool`
- **Purpose:** Check if any term is a substring of text
- **Called by:** `classify_kind`
- **Flag:** 🟢 — note: substring match (not word boundary) is coarse but intentional

#### `matched_terms(text, terms, limit) -> list[str]`
- **Purpose:** Return matching terms up to limit
- **Called by:** `signal_quality`, `urgency_from_text`
- **Flag:** 🟢

#### `budget_from_text(text: str) -> str`
- **Purpose:** Extract budget amount/range from text
- **Called by:** `manual_lead_from_text`, `signal_quality`
- **Hardcodes:** regex patterns (lines 79-82)
- **Flag:** 🔵 HARDCODED — regex patterns baked in

#### `tech_stack_from_text(text: str) -> list[str]`
- **Purpose:** Extract tech stack terms from text
- **Called by:** `manual_lead_from_text`, `fit_bullets`, `proof_snippet`
- **Flag:** 🟢 — but relies on hardcoded `TECH_TERMS`/`TECH_LABELS`

#### `urgency_from_text(text: str) -> str`
- **Purpose:** Extract urgency signals from text
- **Called by:** `manual_lead_from_text`
- **Flag:** 🟢

#### `location_from_text(text: str) -> str`
- **Purpose:** Extract location from text
- **Called by:** `manual_lead_from_text`
- **Hardcodes:** City list (line 116) — San Francisco, New York, London, Berlin, **Bengaluru**, Bangalore, Mumbai, Delhi, Toronto, Singapore; regex patterns (line 115)
- **Flag:** 🔵 HARDCODED — city list baked in; 🟡 SUSPECT — includes India-specific cities but no broader India handling in location patterns

#### `company_from_text(text, fallback) -> str`
- **Purpose:** Extract company name from text
- **Called by:** `manual_lead_from_text`
- **Hardcodes:** regex patterns (lines 127-131)
- **Flag:** 🔵 HARDCODED — regex patterns baked in

#### `classify_kind(text, default) -> str`
- **Purpose:** Classify lead kind (should return "job", "gig", etc.)
- **Called by:** `signal_quality`, `manual_lead_from_text`
- **Flag:** 🔴 DEAD/⚪ INCOMPLETE — always returns "job" (line 143). Second branch is unreachable dead code. The `default` parameter is never used. This is also a **bug** — non-job leads can never be classified as anything else.

#### `signal_quality(text, default_kind) -> dict`
- **Purpose:** Compute signal quality score (0-100) with tags and reasons
- **Called by:** `manual_lead_from_text`, `agents/quality_gate.py`
- **Hardcodes:** base score 18 (line 156), tech bonus 25 (line 159), intent bonus 24 (line 163), budget 10 (line 167), urgency 12 (line 171), kind job 6 (line 174), next-step 5 (line 177), noise penalty -20 (line 180)
- **Flag:** 🔵 HARDCODED — all scoring values baked in

#### `fit_bullets(title, text) -> list[str]`
- **Purpose:** Generate fit-justification bullets for a lead
- **Called by:** `manual_lead_from_text`
- **Flag:** 🟡 SUSPECT — `title` parameter is unused (line 194)

#### `proof_snippet(title, text, kind) -> str`
- **Purpose:** Generate credibility snippet for outreach
- **Called by:** `manual_lead_from_text`
- **Flag:** 🟡 SUSPECT — `kind` parameter is unused (line 210)

#### `followup_sequence(company, kind) -> list[str]`
- **Purpose:** Generate followup sequence
- **Called by:** `manual_lead_from_text`
- **Flag:** 🟡 SUSPECT — `kind` parameter is unused (line 219)

#### `outreach_drafts(title, company, text, kind, budget) -> dict`
- **Purpose:** Generate outreach drafts (reply, DM, email, proposal)
- **Called by:** `manual_lead_from_text`
- **Hardcodes:** term list (line 231) for first-match project detection; hardcoded reply/DM/email/proposal templates (lines 236-256)
- **Flag:** 🔵 HARDCODED — templates baked in; 🟡 SUSPECT — `kind` and `budget` parameters unused (lines 228, 234-256)

#### `company_from_url(url: str) -> str`
- **Purpose:** Extract company name from URL
- **Called by:** `manual_lead_from_text`
- **Flag:** 🟢

#### `manual_lead_from_text(text, url, default_kind) -> dict`
- **Purpose:** Main entry point — convert raw text to structured lead dict
- **Called by:** `routes/leads.py` (line 283), `agents/x_scout.py`, `agents/free_scout.py`, `mcp_server.py`, `tests/`
- **Hardcodes:** source_url fallback prefix "manual://" (line 285); description cap 1200 (line 293)
- **Flag:** 🟢 — well-structured orchestration

**Exports:**

| Export | Known importers |
|--------|----------------|
| `clean_text` | `agents/quality_gate.py` (line 14) |
| `signal_quality` | `agents/quality_gate.py` (line 14) |
| `manual_lead_from_text` | `routes/leads.py` (line 283), `agents/x_scout.py` (line 7), `agents/free_scout.py` (line 11), `mcp_server.py` (line 15), `tests/test_regressions.py` (line 936) |
| `budget_from_text` | `tests/` |
| `tech_stack_from_text` | `agents/x_scout.py`, `agents/free_scout.py` |
| `company_from_text` | `agents/x_scout.py`, `agents/free_scout.py` |
| `location_from_text` | `agents/x_scout.py` |
| `outreach_drafts` | `agents/x_scout.py`, `agents/free_scout.py` |
| `followup_sequence` | `agents/x_scout.py` |
| `fit_bullets` | `agents/x_scout.py`, `agents/free_scout.py` |
| `proof_snippet` | `agents/x_scout.py` |
| `company_from_url` | `agents/x_scout.py` |
| `classify_kind` | `agents/x_scout.py` |

---

## 4. Flags summary

| Priority | Status | Item | File:Line | Resolution |
|----------|--------|------|-----------|------------|
| P0 | ✅ RESOLVED | `_SYSTEM_PROMPT` 1st definition | `evaluator.py` | Deleted — dead code, immediately overwritten |
| P0 | ✅ RESOLVED | `classify_kind` 2nd branch | `lead_intel.py` | Now uses `default` param instead of hardcoded `"job"` |
| P1 | 🔄 NOTED | `TECH_TAXONOMY` (84 entries) | `scoring_engine.py` | Domain data — acceptable as constants |
| P1 | 🔄 NOTED | `TECH_CATEGORY` (84 mappings) | `scoring_engine.py` | Domain data — acceptable |
| P1 | 🔄 NOTED | Rubric weights | `scoring_engine.py` | Scoring engine domain logic — acceptable |
| P1 | 🔄 NOTED | Seniority cap thresholds | `scoring_engine.py` | Scoring engine domain logic — acceptable |
| P1 | 🔄 NOTED | Criterion score constants | `scoring_engine.py` | Scoring engine domain logic — acceptable |
| P1 | 🔄 NOTED | Model name and embedding params | `semantic.py` | Domain data — acceptable |
| P1 | 🔄 NOTED | Semantic stretch/blend weights | `semantic.py` | Domain logic — acceptable |
| P1 | 🔄 NOTED | Feedback ranker label/weight dicts | `feedback_ranker.py` | Domain data — acceptable as module-level constants |
| P1 | ✅ RESOLVED | Feedback delta cap & thresholds | `feedback_ranker.py` | Now driven from `settings.scoring.feedback_learning` |
| P1 | ✅ RESOLVED | Evaluator truncation limits | `evaluator.py` | Now driven from `settings.scoring.evaluator` |
| P1 | 🔄 NOTED | `lead_intel.py` term lists | `lead_intel.py` | Deferred — see `docs/deferred/lead-intel-flexibility.md` |
| P1 | 🔄 NOTED | Lead intel scoring/regex/templates | `lead_intel.py` | Deferred — see `docs/deferred/lead-intel-flexibility.md` |
| P1 | 🔄 NOTED | `_candidate_location` India reference | `scoring_engine.py` | Domain data — acceptable as static list |
| P1 | 🔄 NOTED | All 🟣 COUPLED items | evaluator/scoring/semantic | Structural — needs dedicated refactor pass |
| P2 | ✅ RESOLVED | `_build_proof` wrapper | `evaluator.py` | Removed — zero callers |
| P2 | ✅ RESOLVED | `_infer_experience_level` wrapper | `evaluator.py` | Removed — zero callers |
| P2 | ✅ RESOLVED | Unused function params | `lead_intel.py` | Prefixed with `_` to signal intent |
| P2 | ✅ RESOLVED | `classify_kind.default` param | `lead_intel.py` | Now actually used |
| P3 | 🟢 CLEAN | All CLEAN items | evaluator/scoring/semantic/feedback/lead_intel | Unchanged |

---

## 5. Dependencies

**Inbound (other units depend on this):**

| Consumer | Depends on | Imported items |
|----------|-----------|----------------|
| `services/scanner.py` | `evaluator.py` | `score` |
| `services/ghost.py` | `evaluator.py` | `score` |
| `graph/__init__.py` | `evaluator.py` | `score` |
| `mcp_server.py` | `evaluator.py`, `lead_intel.py` | `score`; `manual_lead_from_text`, `signal_quality`, `budget_from_text`, `tech_stack_from_text`, `company_from_text`, `location_from_text`, `outreach_drafts`, `followup_sequence`, `fit_bullets`, `proof_snippet`, `clean_text` |
| `routes/leads.py` | `lead_intel.py` | `manual_lead_from_text` |
| `agents/quality_gate.py` | `lead_intel.py` | `clean_text`, `signal_quality` |
| `agents/x_scout.py` | `lead_intel.py` | Multiple lead intel functions |
| `agents/free_scout.py` | `lead_intel.py` | Multiple lead intel functions |
| `agents/generator.py` | `scoring_engine.py` | `TECH_TAXONOMY` |
| `agents/query_gen.py` | `scoring_engine.py` | `infer_experience_level` |
| `db/client.py` | `feedback_ranker.py` | `apply_feedback_learning` |
| `tests/test_regressions.py` | All 5 modules | Multiple functions |
| `tests/test_observability.py` | `scoring_engine.py` | `_budget_amount` |

**Outbound (this unit depends on others):**

| Callee | Used by | Items used |
|--------|---------|------------|
| `db.client.vec` | `semantic.py:_vec_store` | `vec` |
| `db.client.get_setting` | `evaluator.py:_evaluator_llm_requested` | `get_setting` |
| `agents.ingestor._emb` | `semantic.py:_embed_jd` | `_emb` (private!) |
| `llm.call_llm` | `evaluator.py:_score_with_llm` | `call_llm` |
| `logger.get_logger` | All 5 files | `get_logger` |

**External (third-party libs used):**

| Library | Used for | Version pin? | Flag |
|---------|----------|-------------|------|
| `pydantic` | Structured LLM output parsing | via project | 🟢 |
| `lancedb` (via `db.client.vec`) | Vector search | via project | 🟣 COUPLED — indirect dependency accessed through `db.client.vec` |

---

## 6. First principles assessment

### `agents/evaluator.py`

1. **Does this file need to exist?** Yes — provides the LLM-led scoring path and decouples callers from the deterministic engine internals.
2. **Does it do what it claims?** Yes — consistently implements "LLM-led with deterministic fallback".
3. **Is it the right place for this logic?** Yes — the evaluator/fallback pattern is appropriately separated from the rubric engine.
4. **What would break if deleted?** `services/scanner.py`, `services/ghost.py`, `graph/__init__.py`, `mcp_server.py` — all import `score`. Tests also directly test this module.

### `agents/scoring_engine.py`

1. **Does this file need to exist?** Yes — this is the core scoring logic for the entire app.
2. **Does it do what it claims?** Yes — "Deterministic scoring engine" is accurate.
3. **Is it the right place for this logic?** Partially — the massive hardcoded taxonomies (TECH_TAXONOMY, ROLE_KEYWORDS, WRONG_FIELD_TERMS) might be better as data files loaded at startup. The rubric weights belong in config.
4. **What would break if deleted?** `evaluator.py` (imports 3 functions), `generator.py` (imports TECH_TAXONOMY), `query_gen.py` (imports infer_experience_level), plus all tests.

### `agents/feedback_ranker.py`

1. **Does this file need to exist?** Yes — small, focused, single-responsibility.
2. **Does it do what it claims?** Yes — applies feedback-based signal adjustment.
3. **Is it the right place for this logic?** Yes — it is correctly separated from the deterministic scoring engine.
4. **What would break if deleted?** `db/client.py` lines 754, 771 — feedback learning in lead storage would be lost. Tests.

### `agents/semantic.py`

1. **Does this file need to exist?** Yes — provides embedding-based similarity as a separate concern.
2. **Does it do what it claims?** Yes — "fail-soft semantic fit that returns None on failure".
3. **Is it the right place for this logic?** Yes — separated from the scoring engine where it's consumed.
4. **What would break if deleted?** `scoring_engine.py:_semantic_criterion` returns None (which it already handles), so scoring degrades cleanly to keyword-only. Tests.

### `agents/lead_intel.py`

1. **Does this file need to exist?** Yes — central text-to-lead conversion used by scouts, routes, MCP server.
2. **Does it do what it claims?** Partially — the `classify_kind` function has a confirmed bug (always returns "job"). Name is accurate otherwise.
3. **Is it the right place for this logic?** Yes — it's a conversion/enrichment layer between raw scraped text and structured lead dicts.
4. **What would break if deleted?** `routes/leads.py`, `agents/x_scout.py`, `agents/free_scout.py`, `mcp_server.py`, `agents/quality_gate.py` — all heavily depend on this module.
