# Map: backend-generators

**File:** `docs/maps/backend-generators.md`
**Codebase path(s):** `backend/agents/generator.py`, `backend/agents/ingestor.py`
**Files in scope:** 2
**Total lines:** ~1,779
**Generated:** 2026-05-15

---

## 1. Unit summary

This unit covers the two production agent files that sit between the application layer and the LLM/graph/vector stores. `generator.py` owns the document-assembly pipeline: given a lead (job) and the local profile, it produces a tailored resume PDF, cover letter PDF, outreach messages, and ATS keyword-coverage metrics. `ingestor.py` owns the profile-ingestion pipeline: given raw text (hand-typed or PDF-extracted), it parses it into structured candidate data (`C` schema), writes it into the Kuzu knowledge graph, and indexes skill/project embeddings in LanceDB. Both files depend on `agents/scoring_engine.py` (keyword taxonomy), `db/client.py` (SQLite, Kuzu, LanceDB connections), `llm.py` (LLM calls), and `models/schema.py`. Consumers include `services/ghost.py`, `services/generator.py`, `graph/__init__.py`, `routes/ingest.py`, and `agents/semantic.py`.

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `backend/agents/generator.py` | 1,215 | Document assembly: resume/cover letter PDF generation, outreach messages, ATS keyword coverage | 🟠 STALE — `_draft()` dead code; hardcoded prompt values and PDF parameters should be config-driven |
| 2 | `backend/agents/ingestor.py` | 564 | Profile ingestion: text parsing (LLM + local fallback), Kuzu graph write, LanceDB vector embed | 🟡 SUSPECT — model name hardcoded, thread-safety race on `_st`, hash embedder degrades silently |

---

## 3. Detailed breakdown

### `backend/agents/generator.py`

**Purpose:** Takes a lead (job posting) and the local candidate profile, selects matching projects, generates tailored resume/cover letter markdown via LLM (or local fallback), renders to PDF, produces outreach messages, and computes ATS keyword coverage metrics. Name matches content well. The public surface is `run_package()` and the backward-compat `run()`.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `import os` | stdlib | yes — lines 9, 939, 945, 1146, 1153 | 🟢 — standard |
| `import re` | stdlib | yes — lines 81, 122–131, 140, 146–147, etc. | 🟢 — standard |
| `from pydantic import BaseModel, Field` | 3rd-party | yes — line 13 | 🟢 — standard |
| `from db.client import data_base, get_profile, get_sql_connection, sql` | local | `data_base` (line 9), `get_profile` (1158), `get_sql_connection` (1179, 1187); `sql` — **never referenced** | 🟡 SUSPECT — `sql` imported but never used in this file |
| `from logger import get_logger` | local | yes — line 7 | 🟢 — standard |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_log` | Logger | from `get_logger(__name__)` | throughout | 🟢 — standard |
| `_assets` | str | `data_base() + "/assets"` | `_render_resume_template`, `_render` | 🟢 — reasonable, follows app data layout |
| `_COVER_HEADING_RE` | Pattern | regex matching "Cover Letter" headings | `_split_cover_from_resume` (line 159) | 🟢 — well-scoped |
| `_COVER_SALUTATION_RE` | Pattern | regex matching "Dear/Hi/Hello ..." salutations | `_split_cover_from_resume` (line 161) | 🟢 — well-scoped |
| `_RESUME_HEADING_RE` | Pattern | regex matching "Resume" headings | `_strip_doc_heading` (line 137) | 🟢 — well-scoped |

**Classes:**

#### `_DocPackage(BaseModel)`
- **Inherits from:** `BaseModel`
- **Purpose:** Structured container for LLM-generated document package — resume markdown, cover letter markdown, founder message, LinkedIn note, cold email, selected project titles.
- **Still needed:** yes
- **Flag:** 🟢 CLEAN — well-documented field descriptions, clear separation of concerns

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| (none) | — | — | Pydantic model with defaults, no custom methods | 🟢 |

**Functions:**

#### `_build_proof(profile: dict) -> str`
- **Purpose:** Build a proof-of-work string from profile dict, avoiding dead PROJ_UTILIZES graph edges as per comment.
- **Called by:** `run_package` (line 1159)
- **Calls:** none within this file
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN — straightforward, well-commented

#### `_keywords(text: str) -> set[str]`
- **Purpose:** Extract lowercase tokens from text, filtering against a stop word list.
- **Called by:** `_rank_projects` (lines 92, 102–103)
- **Calls:** `re.findall`
- **Side effects:** none
- **Hardcodes:** stop word set (lines 76–80) — includes domain terms like "engineer", "developer", "company" which could suppress meaningful JD tokens
- **Flag:** 🟡 SUSPECT — stop words include domain-relevant terms (`engineer`, `developer`, `role`, `company`) that may be meaningful for ranking

#### `_rank_projects(profile: dict, lead: dict, limit: int = 4) -> list[dict]`
- **Purpose:** Rank profile projects by JD keyword overlap; stack keywords weighted 3x. Return top N, ensuring at least the first 2 non-zero-score entries.
- **Called by:** `_normalize_package` (line 205), `_fallback_package` (line 300), `_draft_package` (line 512)
- **Calls:** `_keywords`, `lead.get`, `profile.get`
- **Side effects:** none
- **Hardcodes:** stack weight multiplier 3 (line 103), limit=4, minimum 2 entries (line 107)
- **Flag:** 🟢 CLEAN — reasonable heuristic, clear logic

#### `_profile_payload(profile: dict) -> dict`
- **Purpose:** Shape profile dict into LLM-friendly payload with normalized keys.
- **Called by:** `_draft_package` (line 645)
- **Calls:** `profile.get`
- **Side effects:** none
- **Hardcodes:** key mapping (lines 112–118)
- **Flag:** 🟢 CLEAN

#### `_strip_doc_heading(text: str, heading: str) -> str`
- **Purpose:** Strip a section heading from the beginning of a document.
- **Called by:** `_normalize_package` (lines 191–192)
- **Calls:** `_COVER_HEADING_RE`, `_RESUME_HEADING_RE`, `re.compile`, `pattern.sub`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

#### `_is_trivial_doc(text: str, kind: str) -> bool`
- **Purpose:** Detect whether a generated document is too short/empty to be useful.
- **Called by:** `_normalize_package` (lines 181, 187–188, 195)
- **Calls:** `re.sub`
- **Side effects:** none
- **Hardcodes:** threshold values: cover < 120 chars, resume < 160 chars (lines 152, 154)
- **Flag:** 🟢 CLEAN — sensible thresholds, clear intent

#### `_split_cover_from_resume(text: str) -> tuple[str, str]`
- **Purpose:** Split combined LLM output into resume and cover letter parts at the cover letter heading/salutation boundary.
- **Called by:** `_normalize_package` (lines 178, 185)
- **Calls:** `_COVER_HEADING_RE`, `_COVER_SALUTATION_RE`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

#### `_normalize_package(package: _DocPackage, profile: dict, lead: dict, template: str = "") -> _DocPackage`
- **Purpose:** Defensively post-process LLM output: split combined docs, strip headings, apply fallbacks for trivial/empty documents and outreach messages.
- **Called by:** `run_package` (line 1166)
- **Calls:** `_split_cover_from_resume`, `_is_trivial_doc`, `_strip_doc_heading`, `_fallback_package`, `_rank_projects`, `_fallback_outreach`
- **Side effects:** none
- **Hardcodes:** outreach fallback thresholds: founder_message < 30 chars, linkedin_note < 20 chars, cold_email < 30 chars (lines 216–218)
- **Flag:** 🟢 CLEAN — thorough defensive logic, well-structured

#### `_fallback_outreach(profile: dict, lead: dict) -> dict`
- **Purpose:** Generate deterministic outreach messages when LLM fails or returns empty.
- **Called by:** `_normalize_package` (line 221), `_fallback_package` (line 386)
- **Calls:** none significant
- **Side effects:** none
- **Hardcodes:** template strings (lines 241–256), char limits (lines 259–261: 280/300/600)
- **Flag:** 🟢 CLEAN — acceptable for a fallback path; templates are reasonable

#### `_categorize_skills(skills: list[dict]) -> dict[str, list[str]]`
- **Purpose:** Group skills into canonical categories matching the resume format.
- **Called by:** `_fallback_package` (line 310)
- **Calls:** none significant
- **Side effects:** none
- **Hardcodes:** category map (lines 275–288) — maps raw category strings to canonical buckets
- **Flag:** 🟢 CLEAN — necessary mapping; some overlap risk (e.g. "frontend" and "backend" both → Frameworks & Libraries)

#### `_fallback_package(profile: dict, lead: dict, template: str = "") -> _DocPackage`
- **Purpose:** Generate a complete document package locally when LLM is unavailable, using profile data directly.
- **Called by:** `_normalize_package` (line 196), `run_package` (line 1173)
- **Calls:** `_rank_projects`, `_categorize_skills`, `_fallback_outreach`
- **Side effects:** none
- **Hardcodes:** resume template strings (lines 362–385), cover letter template (lines 375–385), default summary text (lines 357–359), "Python, JavaScript, TypeScript" as default skills (line 314)
- **Flag:** 🟢 CLEAN — fallback is inherently hardcoded; acceptable

#### `_extract_jd_keywords(jd: str, profile: dict) -> str`
- **Purpose:** Extract top ATS keywords from JD using TECH_TAXONOMY, prioritizing those the candidate can claim.
- **Called by:** `_draft_package` (line 513)
- **Calls:** `agents.scoring_engine.TECH_TAXONOMY` (lazy import), `re.findall`
- **Side effects:** none
- **Hardcodes:** extra regex terms (line 408) — CI/CD, REST, GraphQL, etc.
- **Flag:** 🟡 SUSPECT — `profile` parameter is accepted but never used (function only filters JD); extra regex terms duplicate some entries already in TECH_TAXONOMY

#### `_compact_value(value) -> str`
- **Purpose:** Flatten any iterable or None into a comma-separated string.
- **Called by:** `_profile_keyword_terms` (line 438)
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN — simple utility

#### `_profile_keyword_terms(profile: dict) -> set[str]`
- **Purpose:** Return canonical taxonomy terms evidenced somewhere in the profile graph.
- **Called by:** `_keyword_coverage` (line 491)
- **Calls:** `agents.scoring_engine.TECH_TAXONOMY` (lazy import), `_compact_value`, `re.search`
- **Side effects:** none
- **Hardcodes:** field access paths (lines 428–448) — tightly coupled to profile dict shape
- **Flag:** 🟢 CLEAN — well-scoped search across all profile fields

#### `_job_keyword_terms(jd: str) -> list[str]`
- **Purpose:** Return JD keyword requirements in stable display order from TECH_TAXONOMY plus extra terms.
- **Called by:** `_keyword_coverage` (line 490)
- **Calls:** `agents.scoring_engine.TECH_TAXONOMY` (lazy import), `re.search`
- **Side effects:** none
- **Hardcodes:** extra_terms dict (lines 467–473) — duplicates/extends TECH_TAXONOMY
- **Flag:** 🟡 SUSPECT — extra_terms dict overlaps with TECH_TAXONOMY; should either be merged or justified as separate

#### `_keyword_coverage(profile: dict, lead: dict, resume_markdown: str = "") -> dict`
- **Purpose:** Compute ATS keyword coverage metrics: JD terms, covered, missing, incorporated, coverage percentage.
- **Called by:** `_draft_package` (line 514), `run_package` (line 1174)
- **Calls:** `_job_keyword_terms`, `_profile_keyword_terms`, `re.search`
- **Side effects:** none
- **Hardcodes:** list limits (lines 500–503: 24/18/12/18) — truncation of returned lists
- **Flag:** 🟢 CLEAN — clear metrics, reasonable truncation

#### `_draft_package(profile: dict, proof: str, j: dict, template: str = "") -> _DocPackage`
- **Purpose:** Call the LLM with a comprehensive system prompt and user context to generate the full document package.
- **Called by:** `run_package` (line 1165)
- **Calls:** `llm.call_llm`, `_rank_projects`, `_extract_jd_keywords`, `_keyword_coverage`, `_profile_payload`
- **Side effects:** LLM API call via `call_llm`
- **Hardcodes:** entire system prompt (lines 521–630) — 110 lines of instructions with hardcoded format, word limits, char limits, and phone number `+1-555-555-0100` (line 535); word budget "460-620 words" (line 601); cover letter "150-220 words" (line 610); outreach char limits (lines 614–619)
- **Flag:** 🟡 SUSPECT — massive hardcoded prompt with baked-in values (phone, word limits); 460-620 word target may be unrealistic for dense ATS resume

#### `_draft(proof: str, j: dict, template: str = "") -> str`
- **Purpose:** Old LLM draft function returning raw markdown string (not a structured `_DocPackage`). Superseded by `_draft_package`.
- **Called by:** **never called** — confirmed via grep across entire backend
- **Calls:** `llm.call_raw` (would call, if invoked)
- **Side effects:** LLM API call (potential, but unreachable)
- **Hardcodes:** system prompt (lines 678–687), template instruction (lines 667–669)
- **Flag:** 🔴 DEAD — never called; superseded by `_draft_package`

#### `_clean(text: str) -> str`
- **Purpose:** Replace characters Helvetica (Latin-1) cannot encode with ASCII equivalents, then NFKD-normalize and re-encode.
- **Called by:** `_render_resume_template` (line 748), `_render` (line 973)
- **Calls:** `unicodedata.normalize`, character substitution
- **Side effects:** none
- **Hardcodes:** substitution dict (lines 706–727) — comprehensive unicode → ascii mapping
- **Flag:** 🟢 CLEAN — thorough, well-commented

#### `_strip_inline(text: str) -> str`
- **Purpose:** Strip `**bold**`, `*italic*`, `` `code` ``, and `[link](url)` inline markers.
- **Called by:** `_render_resume_template` (multiple), `_render` (line 1056)
- **Calls:** `re.sub`
- **Side effects:** none
- **Hardcodes:** regex patterns (lines 737–740)
- **Flag:** 🟢 CLEAN

#### `_render_resume_template(md_text: str, filename: str) -> str`
- **Purpose:** Render resume markdown to a one-page PDF using direct FPDF multi_cell() with trial-scaling to fit.
- **Called by:** `_render` (line 971)
- **Calls:** `_clean`, `_strip_inline`, `FPDF`
- **Side effects:** writes PDF to `_assets` directory (line 954)
- **Hardcodes:** scale list `[1.28, 1.22, ..., 0.76]` (line 942), accent/injected/muted/rule color tuples (lines 794–797), min font size 6.2pt (line 800), min line height 3.0mm (line 803), date patterns for title parsing (lines 857–859), contact separator `"  |  "` (line 920), ruling line widths and positions (lines 927–928)
- **Flag:** 🔵 HARDCODED — PDF rendering parameters (scales, colors, sizes) should be configurable; 🟢 otherwise — renders consistently

#### `_render(md_text: str, filename: str, kind: str = "resume") -> str`
- **Purpose:** Dispatch to `_render_resume_template` for resumes or FPDF-based render for cover letters, using trial scaling to fit one page.
- **Called by:** `run_package` (lines 1184–1185)
- **Calls:** `_clean`, `_render_resume_template`, `FPDF`
- **Side effects:** writes PDF to `_assets` directory (line 1153)
- **Hardcodes:** base_margin values (line 976), base_sizes dict per kind (lines 977–984), scale list for covers `[1.0, 0.94, ..., 0.70]` (line 1148)
- **Flag:** 🟡 SUSPECT — `base_margin` always uses `kind == "resume"` branch (15mm) since `_render_resume_template` handles resumes; lines 976–984 are effectively dead for the resume path but active for cover letters

#### `run_package(lead: dict, template: str = "") -> dict`
- **Purpose:** Main entry point. Loads profile, calls `_draft_package` → `_normalize_package`, computes keyword coverage, renders PDFs, updates leads DB table with paths and version.
- **Called by:** `graph/__init__.py` (line 97), `services/ghost.py` (line 192), `services/generator.py` (line 73)
- **Calls:** `get_profile`, `_build_proof`, `_draft_package`, `_normalize_package`, `_fallback_package`, `_keyword_coverage`, `_render`, `get_sql_connection`
- **Side effects:** SQLite DB write (lines 1188–1196), PDF file creation (lines 1184–1185), possibly LLM call
- **Hardcodes:** none in this function itself
- **Flag:** 🟡 SUSPECT — path traversal risk: `job_id` from `lead["job_id"]` (line 1177) is used directly in filename `f"{job_id}_v{new_version}.pdf"` (line 1184). Malicious job_id like `../../etc/tmp/foo` could write outside assets dir.

#### `run(lead: dict, template: str = "") -> str`
- **Purpose:** Backward-compatible thin wrapper returning only the resume path string.
- **Called by:** `e2e/manval/run_live_fire.py` (line 163: `from agents.generator import run as gen`)
- **Calls:** `run_package`
- **Side effects:** (same as `run_package`)
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN — thin wrapper, clearly documented as backward-compat

**Exports (what other modules import from this file):**

| Export | Known importers |
|--------|----------------|
| `run_package` | `services/ghost.py:192`, `services/generator.py:73`, `graph/__init__.py:97` |
| `run` | `e2e/manval/run_live_fire.py:163` |
| `_DocPackage` | `tests/test_regressions.py:307` |
| `_normalize_package` | `tests/test_regressions.py:307` |

---

### `backend/agents/ingestor.py`

**Purpose:** Profile ingestion pipeline. Accepts raw text (typed or PDF-extracted), attempts structured extraction via LLM, falls back to local heuristic parsers (portfolio markdown parser or flat field parser). On success, writes candidate data to a Kuzu property graph (`_graph`) and LanceDB vector store (`_vectors`). Name "ingestor" is appropriate — it ingests profiles.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `import hashlib` | stdlib | yes — lines 19, 53 | 🟢 — standard |
| `import math` | stdlib | yes — line 57 | 🟢 — standard |
| `import re` | stdlib | yes — throughout | 🟢 — standard |
| `from db.client import vec` | local | yes — lines 97–110 | 🟢 — standard |
| `from logger import get_logger` | local | yes — line 13 | 🟢 — standard |
| `from models.schema import C` | local | yes — line 113 (`_graph`), line 167 (`_vectors`), line 381 (`_parse_portfolio_markdown`), line 492 (`_parse_local`), line 504 (`run`), line 549 (`ingest`) | 🟢 — standard |
| `import kuzu` | 3rd-party (optional) | yes — guarded try/except (lines 8–11) | 🟢 — optional dependency handled gracefully |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `_log` | Logger | from `get_logger(__name__)` | throughout | 🟢 |
| `_st` | any | `None` initially | `_emb` — set to model or string "hashing" | 🟡 SUSPECT — module-level mutable state; thread-safety race between concurrent calls |

**Functions:**

#### `_h(t: str) -> str`
- **Purpose:** First 12 hex chars of MD5 hash — used as node ID for graph entities.
- **Called by:** `_graph`, `_vectors`, `_put_vec` (via row IDs)
- **Calls:** `hashlib.md5`
- **Side effects:** none
- **Hardcodes:** digest length 12 (line 19)
- **Flag:** 🟢 CLEAN — simple utility

#### `_emb(texts: list[str]) -> list`
- **Purpose:** Thread-safe embedding with lazy model loading. Falls back to deterministic hash-based embedding if sentence-transformers unavailable.
- **Called by:** `_vectors` (lines 171, 181), `db/client.py` (lines 1615, 1630), `agents/semantic.py` (line 33)
- **Calls:** `SentenceTransformer("all-MiniLM-L6-v2")`, `_hash_embedding`
- **Side effects:** mutates module-level `_st` after async thread completes
- **Hardcodes:** model name `"all-MiniLM-L6-v2"` (line 32), thread timeout 120s (line 38), sentinel string `"hashing"` (line 41)
- **Flag:** 🟡 SUSPECT — thread-safety: `_st` is read (line 24) then written (lines 43, 45) without a lock; two concurrent calls could both see `_st is None` and launch duplicate threads. Hash fallback degrades silently (no warning when used via external callers).

#### `_hash_embedding(text: str, dims: int = 384) -> list[float]`
- **Purpose:** Deterministic hash-based embedding using BLAKE2b for reproducible fallback when sentence-transformers is unavailable.
- **Called by:** `_emb` (line 45)
- **Calls:** `re.findall`, `hashlib.blake2b`
- **Side effects:** none
- **Hardcodes:** dimension 384 (line 49) — matches all-MiniLM-L6-v2 output size
- **Flag:** 🟢 CLEAN — reasonable deterministic fallback

#### `_conn() -> kuzu.Connection`
- **Purpose:** Get a fresh Kuzu connection per call to avoid lock contention.
- **Called by:** `_put_node` (lines 72, 78), `_put_rel` (line 87)
- **Calls:** `kuzu.Connection(db)`
- **Side effects:** creates DB connection (no explicit close in callers)
- **Hardcodes:** none
- **Flag:** 🟡 SUSPECT — connections created but never explicitly closed; Kuzu's Python bindings may leak connections if GC-triggered cleanup is unreliable

#### `_put_node(tbl: str, props: dict)`
- **Purpose:** Upsert a node in Kuzu graph: CREATE on PK conflict → MATCH + SET.
- **Called by:** `_graph` (lines 115–163)
- **Calls:** `_conn`, `c.execute`
- **Side effects:** Kuzu graph write
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN — clear upsert pattern

#### `_put_rel(a: str, aid: str, b: str, bid: str, rel: str)`
- **Purpose:** Create or merge a relationship edge in Kuzu graph between two nodes.
- **Called by:** `_graph` (lines 123–164)
- **Calls:** `_conn`, `c.execute`
- **Side effects:** Kuzu graph write
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

#### `_put_vec(name: str, rows: list)`
- **Purpose:** Upsert rows into a LanceDB vector table (delete existing IDs, then add new rows).
- **Called by:** `_vectors` (lines 173, 183)
- **Calls:** `vec.list_tables`, `vec.open_table`, `table.delete`, `table.add`, `vec.create_table`
- **Side effects:** LanceDB vector store write
- **Hardcodes:** none
- **Flag:** 🟡 SUSPECT — SQL injection-ish pattern in delete (lines 104–105): IDs are single-quoted and escaped, but constructing SQL-like predicates via string interpolation is brittle

#### `_graph(p: C)`
- **Purpose:** Write a candidate profile into the Kuzu property graph: candidate node, skill nodes, experience nodes, project nodes, certification/education/achievement nodes, and their relationships.
- **Called by:** `ingest` (line 557)
- **Calls:** `_h`, `_put_node`, `_put_rel`
- **Side effects:** Kuzu graph write
- **Hardcodes:** node/relationship label strings (e.g. "Candidate", "WORKED_AS", "PROJ_UTILIZES" — lines 115–164)
- **Flag:** 🟢 CLEAN — well-structured graph schema

#### `_vectors(p: C)`
- **Purpose:** Compute and store embeddings for skills and projects in LanceDB, using `_emb` for vector generation.
- **Called by:** `ingest` (line 561)
- **Calls:** `_emb`, `_put_vec`, `_h`
- **Side effects:** LanceDB vector store write
- **Hardcodes:** vector table names ("skills", "projects" — lines 173, 183), text concatenation format (line 180)
- **Flag:** 🟢 CLEAN

#### `_pdf(path: str) -> str`
- **Purpose:** Extract text from a PDF file using pypdf.
- **Called by:** `run` (line 507), `ingest` (line 550)
- **Calls:** `PdfReader`
- **Side effects:** reads file from disk
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

#### `_strip_md(text: str) -> str`
- **Purpose:** Strip common Markdown formatting from text.
- **Called by:** multiple within file
- **Calls:** `re.sub`
- **Side effects:** none
- **Hardcodes:** regex patterns (lines 202–206), arrow/bullet replacements (line 206)
- **Flag:** 🟢 CLEAN

#### `_split_csv(value: str) -> list[str]`
- **Purpose:** Split a comma-separated string and strip markdown from each part.
- **Called by:** `_project_from_block` (line 283), `_parse_portfolio_markdown` (lines 340, 364), `_parse_local` (lines 488–490)
- **Calls:** `_strip_md`
- **Side effects:** none
- **Hardcodes:** comma delimiter
- **Flag:** 🟢 CLEAN

#### `_dedupe(items: list[str]) -> list[str]`
- **Purpose:** Deduplicate strings with case-insensitive comparison, preserving order.
- **Called by:** `_section_items` (line 240), `_parse_portfolio_markdown` (line 370)
- **Calls:** `_strip_md`, lowercasing
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

#### `_section_items(text: str, names: tuple[str, ...]) -> list[str]`
- **Purpose:** Extract items from a Markdown section heading matching one of the given names.
- **Called by:** `_parse_portfolio_markdown` (lines 387–389)
- **Calls:** `_dedupe`, `_strip_md`, `re.search`
- **Side effects:** none
- **Hardcodes:** regex for section boundary (`#{1,3}\s+` — line 232) — matches headings at any level 1-3
- **Flag:** 🟢 CLEAN

#### `_section(text: str, start: str, end: str | None = None) -> str`
- **Purpose:** Extract a section of text between two regex patterns.
- **Called by:** `_project_from_block` (lines 293–295), `_parse_portfolio_markdown` (multiple)
- **Calls:** `re.search`
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

#### `_field(block: str, name: str) -> str`
- **Purpose:** Extract field value from a Markdown block by `**Name:** value` pattern.
- **Called by:** `_project_from_block` (multiple), `_parse_portfolio_markdown` (lines 322, 340)
- **Calls:** `_strip_md`, `re.search`
- **Side effects:** none
- **Hardcodes:** pattern `**{name}:**` (line 256)
- **Flag:** 🟢 CLEAN

#### `_heading_blocks(section: str) -> list[tuple[str, str]]`
- **Purpose:** Split a section into `### heading` → content blocks.
- **Called by:** `_parse_portfolio_markdown` (line 354)
- **Calls:** `_strip_md`, `re.finditer`
- **Side effects:** none
- **Hardcodes:** `###` heading level only (line 261)
- **Flag:** 🟢 CLEAN

#### `_title_from_heading(heading: str) -> str`
- **Purpose:** Extract project title from a heading by stripping numbering and parenthetical suffixes.
- **Called by:** `_project_from_block` (line 282)
- **Calls:** `_strip_md`, `re.sub`
- **Side effects:** none
- **Hardcodes:** regex patterns (lines 270–271)
- **Flag:** 🟢 CLEAN

#### `_first_url(value: str) -> str`
- **Purpose:** Extract the first URL from a string.
- **Called by:** `_project_from_block` (lines 284–285)
- **Calls:** `re.search`
- **Side effects:** none
- **Hardcodes:** URL regex (line 275)
- **Flag:** 🟢 CLEAN

#### `_project_from_block(heading: str, block: str) -> P`
- **Purpose:** Parse a project block from portfolio markdown into a `P` schema object.
- **Called by:** `_parse_portfolio_markdown` (line 355)
- **Calls:** `_title_from_heading`, `_split_csv`, `_field`, `_first_url`, `_section`
- **Side effects:** none
- **Hardcodes:** field key names: "Description", "Summary", "Highlights" (line 288), "Tech Stack" / "Tech" (line 283), "Live" / "Video" (lines 284–285), "Modal Details" / "Project Modal Details" (lines 293, 295)
- **Flag:** 🟢 CLEAN — comprehensive field extraction

#### `_parse_portfolio_markdown(txt: str) -> C | None`
- **Purpose:** Parse portfolio-style markdown (numbered sections: Hero, Experience, Selected Work, etc.) into a `C` schema object.
- **Called by:** `_parse_local` (line 396)
- **Calls:** `_section`, `_field`, `_heading_blocks`, `_project_from_block`, `_split_csv`, `_dedupe`, `_section_items`
- **Side effects:** none
- **Hardcodes:** section heading patterns (lines 321–372), field names ("Name", "Tagline", "Tech Stack"), section numbers ("01", "02", etc.)
- **Flag:** 🟢 CLEAN — well-structured, handles a specific known format

#### `_parse_local(txt: str) -> C`
- **Purpose:** Parse generic flat-format or portfolio-markdown text into a `C` schema. Tries portfolio parser first.
- **Called by:** `run` (lines 516, 546)
- **Calls:** `_parse_portfolio_markdown`, _split_csv`
- **Side effects:** none
- **Hardcodes:** section delimiters ("--- Projects ---", "--- Experience ---" — lines 410, 413), field prefixes ("Project: ", "Experience: " — lines 426, 432), "Freelance" as default company (line 334), "Full-Stack Engineer" as default role (line 333)
- **Flag:** 🟢 CLEAN

#### `run(raw: str = "", pdf: str | None = None) -> C`
- **Purpose:** Main extraction entry point. Tries LLM-based extraction first, falls back to `_parse_local` on failure (or if no API key set and not ollama).
- **Called by:** `ingest` (line 555), `e2e/manval/run_live_fire.py` (line 130: `from agents.ingestor import run as ingest`)
- **Calls:** `llm.call_llm`, `llm.resolve_config`, `_parse_local`
- **Side effects:** LLM API call
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN — clear fallback chain

#### `ingest(raw: str = "", pdf: str | None = None) -> C`
- **Purpose:** Top-level ingestion: extract text (PDF optional), call `run()`, write to Kuzu graph and LanceDB vectors, return structured profile.
- **Called by:** `routes/ingest.py` (line 47)
- **Calls:** `_pdf`, `run`, `_graph`, `_vectors`
- **Side effects:** Kuzu graph write, LanceDB vector write
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN — clear orchestration

**Exports (what other modules import from this file):**

| Export | Known importers |
|--------|----------------|
| `ingest` | `routes/ingest.py:47` |
| `run` | `e2e/manval/run_live_fire.py:130` |
| `_emb` | `db/client.py:1615,1630`, `agents/semantic.py:33` |
| `_h` | `tests/test_observability.py:250` |
| `_put_rel` | `tests/test_observability.py:368` |
| `_put_node` | `tests/test_observability.py:379` |
| `_put_vec` | `tests/test_observability.py:393,408` |
| `_parse_local` | `tests/test_regressions.py:492` |

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P0 | 🔴 DEAD | `_draft()` | `generator.py:661` | Never called anywhere; superseded by `_draft_package()` |
| P0 | 🟡 SUSPECT | Path traversal risk in `job_id` usage | `generator.py:1184` | `job_id` from lead dict used directly in PDF filename — `f"{job_id}_v{new_version}.pdf"` could allow traversal with `../` |
| P1 | 🔵 HARDCODED | Placeholder phone `+1-555-555-0100` | `generator.py:535` | Baked into LLM system prompt as example contact line |
| P1 | 🔵 HARDCODED | Resume word budget "460-620 words" | `generator.py:601` | Hardcoded in system prompt; may not fit all roles |
| P1 | 🔵 HARDCODED | Cover letter word range "150-220 words" | `generator.py:610` | Hardcoded in system prompt |
| P1 | 🔵 HARDCODED | Outreach char limits (280/300/600) | `generator.py:614-619` | Hardcoded in system prompt |
| P1 | 🔵 HARDCODED | PDF rendering scale lists | `generator.py:942, 1148` | Trial scale arrays (8-10 values) hardcoded for fit-to-page |
| P1 | 🔵 HARDCODED | PDF accent/ink/muted/rule colors | `generator.py:794-797` | RGB tuples hardcoded in inner function |
| P1 | 🔵 HARDCODED | Font min sizes (6.2pt, 3.0mm line height) | `generator.py:800-801` | Baked into PDF render inner functions |
| P1 | 🔵 HARDCODED | SentenceTransformer model `"all-MiniLM-L6-v2"` | `ingestor.py:32` | Model name hardcoded; should be configurable |
| P2 | 🟡 SUSPECT | Thread-safety race on `_st` in `_emb` | `ingestor.py:23-45` | Module-level mutable `_st` accessed without lock; concurrent calls can both launch loading threads |
| P2 | 🟡 SUSPECT | `sql` imported but unused | `generator.py:4` | `sql` imported from `db.client` but never referenced |
| P2 | 🟡 SUSPECT | `_extract_jd_keywords` accepts unused `profile` param | `generator.py:397` | `profile` parameter is never used; function only processes JD text |
| P2 | 🟡 SUSPECT | `extra_terms` duplicates `TECH_TAXONOMY` | `generator.py:467-473` | Extra term dict in `_job_keyword_terms` overlaps with `scoring_engine.TECH_TAXONOMY` |
| P2 | 🟡 SUSPECT | Kuzu connections not explicitly closed | `ingestor.py:66-67` | `_conn()` returns new connections; `_put_node`/`_put_rel` never close them |
| P2 | 🟡 SUSPECT | LanceDB `delete` uses string interpolation | `ingestor.py:104-105` | SQL-like predicate string built via f-string and `","` join; manually escaped but fragile |
| P3 | 🟢 CLEAN | `_normalize_package` | `generator.py:173` | Thorough defensive post-processing, clear logic |
| P3 | 🟢 CLEAN | `_clean()` | `generator.py:699` | Comprehensive unicode sanitization |
| P3 | 🟢 CLEAN | `_render_resume_template` | `generator.py:744` | Complex but well-structured PDF layout engine |
| P3 | 🟢 CLEAN | `ingest()` | `ingestor.py:549` | Clean orchestration of extraction, graph, and vector writes |
| P3 | 🟢 CLEAN | `_graph()` | `ingestor.py:113` | Well-structured Kuzu graph writer with clear schema |

---

## 5. Dependencies

**Inbound (other units depend on this):**

| Consumer | What they use |
|----------|--------------|
| `services/generator.py` | `generator.run_package` |
| `services/ghost.py` | `generator.run_package` |
| `graph/__init__.py` | `generator.run_package` |
| `e2e/manval/run_live_fire.py` | `generator.run`, `ingestor.run` |
| `routes/ingest.py` | `ingestor.ingest` |
| `db/client.py` | `ingestor._emb` |
| `agents/semantic.py` | `ingestor._emb` |
| `tests/test_regressions.py` | `generator._DocPackage`, `generator._normalize_package`, `ingestor._parse_local` |
| `tests/test_observability.py` | `ingestor._h`, `ingestor._put_rel`, `ingestor._put_node`, `ingestor._put_vec` |
| `tests/test_graph.py`, `tests/test_graph_failures.py` | `generator.run_package` (mocked) |

**Outbound (this unit depends on others):**

| Dependency | Unit | Used by |
|-----------|------|---------|
| `db.client.data_base`, `get_profile`, `get_sql_connection` | `backend-db` | `generator.py` |
| `db.client.vec` | `backend-db` | `ingestor.py` |
| `db.client.db` | `backend-db` | `ingestor.py` |
| `models.schema.C`, `S`, `E`, `P` | `backend-models` | `ingestor.py` |
| `agents.scoring_engine.TECH_TAXONOMY` | `backend-scoring-engine` | `generator.py` (lazy) |
| `llm.call_llm`, `call_raw`, `resolve_config` | `backend-llm` | `generator.py`, `ingestor.py` (lazy) |
| `logger.get_logger` | `backend-logger` | both |

**External (third-party libs used):**

| Library | Used for | Version pin? | Flag |
|---------|----------|-------------|------|
| `pydantic` | Data models (`BaseModel`, `Field`) | via project | 🟢 — standard |
| `fpdf2` | PDF generation (FPDF) | via project | 🔵 HARDCODED — Helvetica-only, no configurable font |
| `kuzu` | Property graph database | optional | 🟢 — guarded import |
| `lancedb` | Vector store | via project | 🟢 — standard |
| `sentence-transformers` | Text embeddings | optional (model name hardcoded) | 🔵 HARDCODED — model pinned to "all-MiniLM-L6-v2" |
| `pypdf` | PDF text extraction | optional | 🟢 — guarded import |

---

## 6. First principles assessment

### `backend/agents/generator.py`

1. **Does this file need to exist?** Yes — core document generation logic that's separate from both the LLM abstraction layer and the app services.
2. **Does it do what it claims?** Yes — generates package documents from leads + profile, matching the filename.
3. **Is it the right place for this logic?** Yes — the PDF rendering and LLM prompting are agent concerns; the fallback logic makes sense co-located.
4. **What would break if deleted?** `graph/__init__.py` generate_nodes, `services/ghost.py`, `services/generator.py`, and `e2e/manval/run_live_fire.py` would all fail.

### `backend/agents/ingestor.py`

1. **Does this file need to exist?** Yes — ingestion pipeline (graph + vectors + parsing) is a distinct concern.
2. **Does it do what it claims?** Yes — ingests profile text into structured data, graph, and vectors.
3. **Is it the right place for this logic?** Partially — the embedding function `_emb` is imported by `db/client.py` and `agents/semantic.py`, creating a reverse dependency. Embedding could arguably live in a shared utility rather than the ingestor.
4. **What would break if deleted?** `routes/ingest.py` /ingest endpoint, `db/client.py` skill/project vector search (via `_emb`), `agents/semantic.py` semantic search (via `_emb`), `e2e/manval/run_live_fire.py` ingestion.
