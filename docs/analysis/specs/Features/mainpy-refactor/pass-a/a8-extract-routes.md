# Pass A8 — Extract Routes

**Lines affected:** 746-1194, 1197-1278, 1480-1620, 1687-2031, 2127-2154
**Target files:** `backend/routes/*.py` (8 files)
**Mode:** AFK per file, HITL for verification

---

## Goal

Move all 49 HTTP route handlers + 1 WebSocket handler into router modules. Each router gets its own file with an `APIRouter`. `main.py` imports and includes each router.

**Important:** This is the highest-risk phase because route handlers use global state (`cm`, `_sched`, scan state, service functions). Move exactly as-is. No `response_model=` yet. No handler body changes.

---

## Router Breakdown

### `routes/misc.py` — 6 routes (lowest risk)

| Route | Handler | Lines |
|-------|---------|-------|
| GET `/health` | `health` | 746-793 |
| GET `/api/v1/events` | `get_events_endpoint` | 1096-1099 |
| GET `/api/v1/graph` | `graph_stats` | 1102-1105 |
| GET `/api/v1/template` | `get_template` | 1083-1086 |
| POST `/api/v1/template` | `save_template` | 1089-1093 |
| POST `/api/v1/help/chat` | `help_chat` | 1278-1283 |

### `routes/settings.py` — 3 routes

| Route | Handler | Lines |
|-------|---------|-------|
| GET `/api/v1/settings` | `get_cfg` | 1480-1488 |
| GET `/api/v1/settings/validate` | `validate_settings` | 1545-1573 |
| POST `/api/v1/settings` | `save_cfg` | 1576-1590 |

### `routes/leads.py` — 12 routes (largest)

| Route | Handler | Lines |
|-------|---------|-------|
| GET `/api/v1/leads` | `leads` | 819-829 |
| GET `/api/v1/leads/export.csv` | `export_leads_csv` | 832-851 |
| GET `/api/v1/leads/{job_id}/versions` | `get_lead_versions` | 876-892 |
| GET `/api/v1/leads/{job_id}` | `get_lead` | 895-902 |
| DELETE `/api/v1/leads/{job_id}` | `delete_lead_endpoint` | 905-912 |
| PUT `/api/v1/leads/{job_id}/status` | `update_status` | 915-925 |
| PUT `/api/v1/leads/{job_id}/feedback` | `update_feedback` | 928-938 |
| PUT `/api/v1/leads/{job_id}/followup` | `update_followup` | 941-948 |
| POST `/api/v1/leads/manual` | `create_manual_lead` | 951-991 |
| GET `/api/v1/followups/due` | `due_followups` | 994-997 |
| POST `/api/v1/leads/{job_id}/generate` | `generate_for_lead` | 1000-1003 |
| POST `/api/v1/leads/{job_id}/pipeline/run` | `run_pipeline` | 1006-1046 |

### `routes/profile.py` — 11 routes

| Route | Handler | Lines |
|-------|---------|-------|
| GET `/api/v1/profile` | `get_profile_endpoint` | 1108-1111 |
| PUT `/api/v1/profile/candidate` | `update_candidate_endpoint` | 1114-1119 |
| POST `/api/v1/profile/skill` | `add_skill_endpoint` | 1124-1129 |
| PUT `/api/v1/profile/skill/{sid}` | `update_skill_endpoint` | 1132-1137 |
| DELETE `/api/v1/profile/skill/{sid}` | `delete_skill_endpoint` | 1140-1144 |
| POST `/api/v1/profile/experience` | `add_experience_endpoint` | 1149-1154 |
| PUT `/api/v1/profile/experience/{eid}` | `update_experience_endpoint` | 1157-1162 |
| DELETE `/api/v1/profile/experience/{eid}` | `delete_experience_endpoint` | 1165-1169 |
| POST `/api/v1/profile/project` | `add_project_endpoint` | 1174-1179 |
| PUT `/api/v1/profile/project/{pid}` | `update_project_endpoint` | 1182-1187 |
| DELETE `/api/v1/profile/project/{pid}` | `delete_project_endpoint` | 1190-1194 |

### `routes/scan.py` — 6 routes

| Route | Handler | Lines |
|-------|---------|-------|
| POST `/api/v1/scan` | `scan` | 1197-1208 |
| POST `/api/v1/scan/stop` | `stop_scan` | 1211-1217 |
| POST `/api/v1/leads/reevaluate` | `reevaluate_jobs` | 1220-1231 |
| POST `/api/v1/leads/reevaluate/stop` | `stop_reevaluate_jobs` | 1234-1240 |
| POST `/api/v1/leads/cleanup` | `cleanup_leads` | 1243-1266 |
| POST `/api/v1/free-sources/scan` | `free_sources_scan` | 1269-1275 |

### `routes/ingest.py` — 6 routes

| Route | Handler | Lines |
|-------|---------|-------|
| POST `/api/v1/ingest` | `ingest` | 1593-1620 |
| POST `/api/v1/ingest/linkedin` | `ingest_linkedin` | 1687-1746 |
| POST `/api/v1/ingest/github` | `ingest_github_endpoint` | 1749-1790 |
| POST `/api/v1/ingest/profile` | `import_profile_json` | 1793-1878 |
| GET `/api/v1/ingest/profile/template` | `get_profile_template` | 1881-1886 |
| POST `/api/v1/ingest/portfolio` | `ingest_portfolio_endpoint` | 1889-1915 |

### `routes/actions.py` — 5 routes

| Route | Handler | Lines |
|-------|---------|-------|
| POST `/api/v1/fire/{job_id}` | `fire` | 1937-1945 |
| POST `/api/v1/leads/{job_id}/form/read` | `read_lead_form` | 1952-1993 |
| GET `/api/v1/identity` | `get_identity` | 1996-2009 |
| POST `/api/v1/selectors/refresh` | `refresh_selectors` | 2012-2019 |
| POST `/api/v1/leads/{job_id}/apply/preview` | `preview_apply` | 2022-2031 |

### `routes/ws.py` — 1 WebSocket

| Route | Handler | Lines |
|-------|---------|-------|
| WS `/ws` | `ws_endpoint` | 2127-2153 |

---

## Router Template

Every router file follows this exact pattern:

```python
from fastapi import APIRouter, ...  # only what this router needs

router = APIRouter(prefix="/api/v1", tags=["name"])

@router.get("/leads")
async def leads(beginner_only: bool = False, seniority: str | None = None):
    # handler body copied exactly from main.py
    ...

# ... more handlers ...
```

---

## What Changes During the Move

| Change | Reason |
|--------|--------|
| Add `router = APIRouter(prefix=..., tags=...)` at top of each file | FastAPI router creation |
| Replace `@app.get(...)` with `@router.get(...)` | Different routing target |
| Replace `@app.websocket(...)` with `@router.websocket(...)` | Same |
| Resolve lazy imports to top-of-file imports in the router module | Standard pattern |
| `main.py` removes route handlers | Now in routers |
| `main.py` adds `from routes.leads import router as leads_router` then `app.include_router(leads_router)` | Router registration |

**No handler body changes.** Not even whitespace. The handler function bodies are copied verbatim.

---

## Verification (per router)

```bash
# After extracting one router:
python -m py_compile backend/routes/leads.py
python -m py_compile backend/main.py
cd backend && uv run python -m pytest tests/ -q --tb=line
```

If it passes, move to the next router. If it fails, stop and report.

---

## Commits (one per router)

```
refactor(a1): extract routes/misc.py
refactor(a1): extract routes/settings.py
refactor(a1): extract routes/leads.py
refactor(a1): extract routes/profile.py
refactor(a1): extract routes/scan.py
refactor(a1): extract routes/ingest.py
refactor(a1): extract routes/actions.py
refactor(a1): extract routes/ws.py
```
