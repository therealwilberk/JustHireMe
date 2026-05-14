# Unfiltered Assessment — JustHireMe

> What I actually think after mapping every single file.
> No politeness. No "it depends." Just recommendations.

---

## The Short Version

This app has a good heart buried under layers of overengineering. The scraping + scoring + generating pipeline works. But the architecture makes it harder to maintain, harder to extend, and slower to start than it needs to be. ~90% of the complexity comes from 3 decisions that made sense at prototype stage but are now technical debt:

1. **Three databases when one would do**
2. **17 LLM providers when 1-2 are used**
3. **Deterministic scoring as primary, LLM as fallback (should be reversed)**

Fix those three things and you cut the codebase by ~40%, startup time by ~5s, and maintenance burden by more than half.

---

## What's Actually Good

Before I tear everything apart — these parts are genuinely well done:

- **Config layer** (`backend/config/`) — Pydantic schemas organized by domain, validators, resolution hierarchy. This is production-quality infrastructure.
- **main.py refactor** — Routes extracted to 8 modules, services separated, clean entry point. Good engineering.
- **Scan lifecycle** (`ScanManager`, `GhostService`) — Clean state machine, proper cancellation, ghost lock. Solid async design.
- **WebSocket manager** — Snapshot-under-lock pattern on `_CM` is correct concurrent design.
- **Test fakes** (`fakes.py`, `api_contracts.py`) — Proper test isolation without mocking hell. Real in-memory substitutes.
- **Docstrings** — 22 files with Google-style docstrings. Every function documented. This is rare and valuable.
- **Spec-first discipline** — Phase specs with validation checklists before implementation. Keeps scope in check.

These patterns are worth keeping and expanding. Everything below is what I'd change.

---

## The Database Problem

Three databases. One desktop app with maybe 500 leads.

**Current state:**
- SQLite: leads, events, settings (the real data)
- Kuzu: knowledge graph (Candidate → Experience → Skill — a few hundred nodes)
- LanceDB: vector embeddings for skill similarity (384-dim, maybe 200 vectors)

**Why this is wrong:**

`db/client.py` is 1,628 lines — the single largest file in the codebase — because it has to talk to three different databases with different APIs, connection models, and failure modes. Every CRUD function creates 2-3 new Kuzu connections per call. The LanceDB import alone adds ~7s to startup. The Kuzu import adds ~1.6s. All for data that fits in a SQLite table with 5 columns.

**The evidence from the map:**

```
backend-db.md flags: 4 🔴 DEAD functions | 17 🔵 HARDCODED | 13 🟣 COUPLED
```

Four dead functions. Thirteen coupling flags — more than any other unit. The config layer has a circular dependency with `db.client` because `secrets.py` uses `get_setting()` which is in the file that imports from config.

**Is SQLite-only best practice? I researched it.**

Yes — for this scale it's not just acceptable, it's what the ecosystem is standardizing on. Here's what I found:

There's a growing pattern called "SQLite for everything" in the embedded/single-user space. Multiple libraries prove it works:

| Library | What it adds to SQLite | Use in this app |
|---------|----------------------|-----------------|
| **sqlite-vec** | Vector search as a virtual table (HNSW, cosine, L2) | Replaces LanceDB entirely — 384-dim skill vectors in a single BLOB column with `CREATE VIRTUAL TABLE vec USING vec0(embedding float[384])` |
| **sqlite-graph** | Graph traversal via recursive CTEs + bi-temporal edges | Replaces Kuzu — `WITH RECURSIVE cte AS (...) SELECT` for 2-3 hop profile graph queries |
| **FTS5** | Full-text search with BM25 ranking (built into SQLite stdlib) | Replaces any keyword search needs |
| **sqlitesearch / faissqlite / SimpleVecDB** | Hybrid search (FTS5 + vector + RRF) in one file | All-in-one semantic + keyword search |

The threshold for needing dedicated infrastructure is well above this app's data size:
- Dedicated graph DB (Neo4j/Kuzu): >100K entities with deep traversals. This app has <500 nodes with 2-3 hop queries. SQLite CTEs handle this in milliseconds.
- Dedicated vector DB (Pinecone/Qdrant): >100K vectors. This app has <200. Brute-force cosine similarity on an in-memory list is faster than initializing the ANN index.

sqlite-vec specifically has matured rapidly (2024-2026) and is now production-grade for this use case. It supports cosine/euclidean/manhattan/hamming distance, HNSW indexing, and works as a virtual table you can query with standard SQL.

Kuzu even has a SQLite extension that lets you ATTACH a SQLite database and run Cypher queries against it — proving the two are complementary, not competing.

**Impact of going SQLite-only (+ optional sqlite-vec):**
- `db/client.py` goes from 1,628 lines to ~400
- Startup time drops by ~8.6s (LanceDB 7s + Kuzu 1.6s)
- Removes 4 dead Kuzu functions
- Ends the circular dependency with config
- One connection model, one query syntax, one failure mode
- `uv sync` becomes ~2GB lighter (no PyTorch for sentence-transformers)
- `cp app.db backup.db` is your backup strategy (WAL mode: use `VACUUM INTO` for consistent snapshots)

---

## The Scoring Problem

1,097 lines for a deterministic rubric. 84-entry taxonomy. 6 weighted criteria. And it's never been validated against real data.

**What bothers me:**

The rubric weights (Role: 18, Stack: 27, Proof: 20, Seniority: 20, Constraints: 15, Semantic: 15) sum to 115, not 100. They were clearly tuned by feel, not by testing against actual user decisions. The `WRONG_FIELD_TERMS` tuple has 80+ entries including civil engineering and mechanical engineering — which means this thing would penalize a career-switching civil engineer who learned to code. The whole "wrong field" concept is a bad default.

The LLM evaluator path is better at this task (a model can read a job description and understand nuance), but it's relegated to "optional enhancement" because of the "no LLM dependency" principle. I think that principle is costing accuracy.

**What I'd do:**

Flip the hierarchy. LLM scoring as primary (Ollama is free, local, private), deterministic rubric as fallback when no model is configured. Wire `feedback_ranker.py` (which exists but does nothing useful — it adjusts feature weights that nobody looks at) into an actual learning loop: "good fit" click → boost similar future scores, "bad fit" → penalty.

Also: `classify_kind()` always returns `"job"` because the second branch is unreachable dead code. This is a bug. Freelance leads can never be classified as anything other than "job." Fix or remove.

---

## The LLM Provider Problem

17 providers. ~50 lines of import/init code each. Hardcoded model names that will go stale. Hardcoded base URLs that duplicate the config layer.

**Reality check:**

The app defaults to Ollama (free, local). If someone has Ollama running or wants to try it, they don't need the other 16. If they're paying for an API, they probably use Anthropic or OpenAI. The remaining 14 are configuration noise — they add surface area for bugs, staleness, and testing burden without evidence that anyone uses them.

That said, not everyone can run Ollama. Local LLMs need RAM, and laptop constraints vary. Here's a practical guide that should be surfaced in-app:

**Ollama model recommendations by hardware:**

| RAM | Recommended model | Disk | Quality | Install |
|-----|------------------|------|---------|---------|
| 8GB (budget laptop) | `mistral:7b` or `llama3.2:3b` | 2-4GB | Good for scoring | `ollama pull mistral` |
| 16GB (modern laptop) | `llama3.1:8b` or `gemma2:9b` | 5GB | Very good | `ollama pull llama3.1` |
| 32GB+ (workstation) | `deepseek-r1:14b` or `qwen2.5:14b` | 9GB | Excellent | `ollama pull deepseek-r1:14b` |
| GPU (8GB+ VRAM) | Any 7-13B model runs fast | — | Best | GPU auto-detected |

Mistral 7B is the sweet spot for 8GB laptops — 4.1GB disk, ~6-7GB RAM at runtime, Apache 2.0 license, and genuinely capable at scoring job descriptions. Llama 3.2 3B is the fallback for truly constrained hardware.

**Free-ish API alternatives (when Ollama doesn't fit):**

| Provider | Free tier | Notes |
|----------|-----------|-------|
| **NVIDIA NIM** | Free limited usage | Already in the provider list, uses same OpenAI-compatible API |
| **Groq** | Free tier (30 req/min) | LPU inference, incredibly fast, no GPU needed |
| **Together.ai** | $1 free credits | OpenAI-compatible, many open models |
| **HuggingFace Inference** | 30K free monthly requests | Serverless, no key needed for some models |
| **Perplexity** | $5/mo sonar-pro | Cheap, solid quality |
| **OpenRouter** | Free tier with rate limits | Routes to cheapest available model |

These make sense to keep in the provider list but consolidated into a "cloud free-tier" group with clear documentation on which have free tiers and what the limits are. The rest (Kimi, Cerebras, Fireworks, etc.) are niche.

**What I'd do:**

Keep 4 groups: **Ollama** (default, recommended), **Anthropic** (best quality), **OpenAI** (broadest compatibility), and a **"Free/Cheap Cloud"** group (NVIDIA + Groq + OpenRouter — all OpenAI-compatible, all with free tiers). Collapse the if/elif chain into a provider-registry pattern so adding a new provider doesn't touch `llm.py`.

---

## The Startup Slowness

You said Tauri feels slow on Arch + Hyprland. Here's what's actually happening:

1. **WebKit2GTK cold start** — GTK3-based, known issue on Linux. Tauri has an open PR migrating to GTK4 + WebKitGTK 6.0, which improves rendering performance significantly. This PR (#14684) needs to land and you need to upgrade. Not your fault, not Tauri's fault — GTK3 is just old.

2. **Python sidecar** — `uv run python main.py` adds ~1-2s interpreter overhead on first boot. Then `db/client.py` triggers Kuzu + LanceDB imports at module level (not lazy). That's another ~8.6s. Most of that startup time is database imports.

3. **`npm run tauri dev` vs production** — Dev mode has Vite HMR, dev server, hot reload — all overhead. A `tauri build` binary will be notably faster.

**Quick wins:**
- Make ALL third-party DB imports lazy (not just some — current code has mixed lazy/eager)
- SQLite-only startup would drop from ~10s cold to ~1s
- `tauri build` for production, not `tauri dev`

Long term: migrate to Tauri 4 with GTK4 when it ships. The GTK4 + WebKit6 migration is in progress and directly addresses Linux startup performance.

---

## The Security Reality

17 API keys in plaintext SQLite. The UI masks them with `••••` on settings reads, but the DB file has raw values. Anyone with filesystem access to `~/.local/share/JustHireMe/crm.db` has every key.

**Risk level for a single-user desktop app:** Low-to-Medium. If only you use this machine, the risk is theoretical. If this were distributed or multi-user, it would be Critical.

**The config layer already does the right thing** — `resolve_secret()` checks env vars first. The problem is the fallback: it reads from SQLite `get_setting()` which is the non-encrypted path. The fix is: once you've migrated keys to env vars, delete the SQLite fallback. Or add `docs/deferred/api-key-encryption.md` is Step 1: remove the fallback. Step 2 is libsecret/keychain, which is nice but optional.

---

## What to Remove

This is what the map analysis identified as removable with minimal impact:

### Dead code (verified cross-unit, confirmed unused)

| Function | File | Reason |
|----------|------|--------|
| `_draft()` | `generator.py:661` | Superseded by `_draft_package()` |
| `get_all_freelance_leads()` | `db/client.py:523` | Not imported anywhere |
| `get_discovered_freelance_leads()` | `db/client.py:1114` | Not imported anywhere |
| `graph_available()` | `db/client.py:134` | Not imported anywhere |
| `graph_error()` | `db/client.py:138` | Not imported anywhere |
| `_ensure_scheme` (first def) | `scout.py:374` | Immediately overwritten at line 386 |
| `_SYSTEM_PROMPT` (first def) | `evaluator.py:34` | Immediately overwritten at line 84 |
| `JobCard` (export) | `src/components/JobCard.tsx:7` | Not imported anywhere |
| `StatCard` (export) | `src/components/Topbar.tsx:44` | Not imported anywhere |
| `sys` import | `scout.py:4` | Unused |
| `sys` import | `actuator.py:5` | Unused |
| `HTTPException` import | `misc.py:9` | Unused |
| `JSONResponse` import | `misc.py:10` | Unused |

### Overengineered features

| Feature | Lines | Why remove |
|---------|-------|------------|
| 14 of 17 LLM providers | ~300 | Configuration noise. Keep Anthropic + OpenAI + Ollama. |
| `actuator.py` | 454 | Experimental auto-apply. Gated by env var. Most fragile code in app. 11+ flags in map. Have never been used in production by anyone. |
| `MCP server` | 191 | Cool demo, zero users consuming it. Adds stdio protocol surface. |
| `India-specific logic` | ~200 across 8 files | `_india_clause()`, market guides, Naukri presets. Dead weight if not targeting India. |
| `help_agent.py` full guides | ~300 | Hardcoded help text. FAQ page replaces it. Keep the LLM chat, remove the canned responses. |
| `feedback_ranker.py` | 176 | Does nothing useful. Adjusts weights nobody uses as a signal. Rip out until you build a real feedback loop. |

---

## What Would 10x This App

These are ordered by impact-to-effort ratio.

### 1. SQLite-only (removes Kuzu + LanceDB)
**Effort:** Medium (4-8 hours)
**Impact:** Removes ~1,200 lines from `db/client.py`, drops startup time by ~8.6s, removes 4 dead functions, ends circular dependency, drops PyTorch dependency (~2GB from `uv sync`).

The profile graph data: 3 tables. `Candidate`, `Experience`, `Skill`. With foreign keys and a simple JOIN-based CTE, you get the same query results as Kuzu's Cypher. Vector similarity for 200 384-dim vectors: just keep them in memory and brute-force. It's faster than LanceDB for this data size.

### 2. LLM-first scoring (Ollama default)
**Effort:** Small (2-4 hours)
**Impact:** Better scoring for every user at zero cost. The deterministic rubric becomes the fallback (and can be simplified). This flips the current architecture from "LLM as bonus" to "LLM as default."

### [✓] Tests already run in CI
**Correction:** All 328 tests already run. The CI command is `uv run python -m pytest tests/ -v` with no exclusions. The "45% run in CI" claim was from the stale audit report written before the CI config was fixed. You're not flying blind — the full suite validates every push.

### 4. Fix the scoring feedback loop
**Effort:** Medium (4-6 hours)
**Impact:** User clicks "good fit" or "bad fit" → adjust future scores. Currently `feedback_ranker.py` adjusts abstract "feature weights" that no one looks at. Wire it into actual scoring. This turns user behavior into automatic improvement.

### 5. Unified settings path
**Effort:** Medium (4-6 hours)
**Impact:** Agents currently read settings from SQLite via `get_setting()` — bypassing the Pydantic config layer entirely. This means the config layer (with validation, typing, defaults) is only partially used. Pick one path and delete the other. The config layer is cleaner and safer.

### 6. Frontend state management
**Effort:** Medium (4-8 hours)
**Impact:** 15 `useState` in App.tsx → one store. ApprovalDrawer's 18 `useState` re-renders the entire component tree on every interaction. A lightweight state library (zustand, ~2KB) or React Context would eliminate the re-render cascade and make state predictable.

---

## Architecture Recommendation — Target State

```
backend/
├── main.py                  # Entry point (~100 lines)
├── config/                  # Keep as-is (good)
├── routes/                  # Keep as-is (good)
├── services/                # Keep as-is (good)
├── schemas/                 # Keep as-is (good)
├── core/                    # Keep as-is (good)
├── db/
│   └── client.py            # ~400 lines (SQLite only)
├── agents/
│   ├── scout.py             # Keep
│   ├── free_scout.py        # Keep
│   ├── x_scout.py           # Keep
│   ├── quality_gate.py      # Keep
│   ├── query_gen.py         # Keep
│   ├── evaluator.py         # Rework (LLM-first)
│   ├── scoring_engine.py    # Simplify (~300 lines, fallback only)
│   ├── generator.py         # Keep, remove _draft()
│   ├── ingestor.py          # Keep
│   ├── lead_intel.py        # Keep, fix classify_kind()
│   ├── semantic.py          # Remove (LanceDB gone, inline simple sim)
│   ├── contact_lookup.py    # Keep
│   ├── browser_runtime.py   # Keep
│   ├── github_ingestor.py   # Keep
│   ├── linkedin_parser.py   # Keep
│   ├── portfolio_ingestor.py# Keep
│   └── selectors.py         # Keep
├── llm.py                   # Slim down (3 providers)
├── logger.py                # Keep
└── log_context.py           # Keep
```

Removed: `actuator.py`, `help_agent.py`, `feedback_ranker.py`, MCP server, 14 LLM providers, Kuzu, LanceDB, `semantic.py`, India logic, dead functions.

---

## Closing

This is a genuinely useful app. The pipeline works. The config layer is excellent. The test infrastructure is better than most production apps. The problems are all fixable — none of them are fundamental design errors, they're just artifacts of fast iteration.

The single highest-leverage change is **Kuzu + LanceDB → SQLite-only**. It's not even close. Every other recommendation amplifies that one.

The second highest is **LLM-first scoring** — flip the evaluation hierarchy, show hardware-guided Ollama recommendations in-app, and offer the free-tier cloud providers as alternatives when local isn't feasible.

The third is **unified settings path** — kill the SQLite `get_setting()` dual path and route everything through the Pydantic config layer.

Everything else in this document is optimization around those three.
