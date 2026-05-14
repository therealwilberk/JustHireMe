# Map: Frontend Views

**File:** `docs/maps/frontend-views.md`
**Codebase path(s):** `src/views/` — all `.tsx` files
**Files in scope:** 9 (8 views + 1 test file)
**Total lines:** ~2,351
**Generated:** 2026-05-15

---

## 1. Unit summary

The `src/views/` unit contains all top-level page components consumed by `App.tsx` via a view-router pattern (`view` state → conditional render inside `<ErrorBoundary>` wrappers). Each view corresponds to a distinct screen in the Tauri desktop app: dashboard, pipeline (lead table with tabs/filters), lead inbox (manual + free-source entry), job-apply (customization package with polling), profile (candidate evidence graph), activity (live agent log stream), graph (Kuzu node topology), and ingestion (multi-tab context import). All views are owned by `App.tsx` and consume shared types from `src/types.ts`, utility functions from `src/lib/leadUtils.ts`, and UI components from `src/components/`. No view is imported by any other view — they are leaf components in the dependency tree.

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `ActivityView.tsx` | 66 | Live agent log stream with category filtering | 🟢 CLEAN |
| 2 | `ApplyJobView.tsx` | 346 | Job URL paste → analyze → generate resume/cover + polling for completion | 🟠 STALE (poll interval + leftover comment) |
| 3 | `DashboardView.tsx` | 297 | Home screen: stats, top leads, scan/maintenance actions | 🟢 CLEAN |
| 4 | `GraphView.tsx` | 137 | Pentagon visualization of Kuzu node types | 🟢 CLEAN |
| 5 | `IngestionView.tsx` | 553 | Multi-tab import (resume, manual, raw, LinkedIn, GitHub, portfolio, JSON, template) | 🟠 STALE (try/catch swallowing) |
| 6 | `LeadInboxView.tsx` | 106 | Manual lead creation + free-source scan trigger | 🟢 CLEAN |
| 7 | `PipelineView.tsx` | 269 | Lead table with tabs, filters, sort, bulk delete, CSV export | 🟢 CLEAN |
| 8 | `ProfileView.tsx` | 384 | Candidate evidence map: skills/experience/projects with CRUD | 🟢 CLEAN |
| 9 | `ProfileView.test.tsx` | 193 | Test suite for ProfileView error states | 🟢 CLEAN |

---

## 3. Detailed breakdown

### `ActivityView.tsx`

**Purpose:** Renders a real-time stream of agent log lines with category tabs (All, Scout, Eval, Customize, System). The component is stateless except for the active tab filter. Currently clean and minimal.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useState` from `react` | stdlib | yes | 🟢 CLEAN |
| `LogLine` from `../types` | local | yes | 🟢 CLEAN |

**Module-level constants & state:** None.

**Functions:**

#### `ActivityView({ logs }: { logs: LogLine[] })`
- **Purpose:** Renders filterable log stream
- **Called by:** `App.tsx:202`
- **Calls:** none within unit
- **Side effects:** none
- **Hardcodes:** tab labels inline at line 9-10, filter logic at lines 36-41
- **Flag:** 🟡 SUSPECT — log filter regex matching (lines 37-39) uses `msg.toLowerCase().includes()` which is fragile; log messages could change server-side and silently break tabs

**Exports:**

| Export | Known importers |
|--------|----------------|
| `ActivityView` | `App.tsx` |

---

### `ApplyJobView.tsx`

**Purpose:** The "Customize for this job" screen. User pastes a job URL/description, the view POSTs to create a lead and trigger generation, then polls `GET /api/v1/leads/{id}` every 1.8s until resume and cover letter are ready. Also displays PDFs (iframe), keyword coverage, contact lookup, outreach drafts, and copy-to-clipboard buttons.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useEffect`, `useRef`, `useState` | stdlib | yes | 🟢 CLEAN |
| `openUrl` from `@tauri-apps/plugin-opener` | 3rd-party | yes | 🟢 CLEAN |
| `Icon` from `../components/Icon` | local | yes | 🟢 CLEAN |
| `ApiFetch`, `ContactLookup`, `KeywordCoverage`, `Lead` from `../types` | local | yes | 🟢 CLEAN |
| `roleFromLead` from `../lib/leadUtils` | local | yes (L189) | 🟢 CLEAN |

**Module-level constants & state:** None.

**Functions:**

#### `ApplyJobView(port, api, leads, openDrawer, initialInput?, autoFocus?)`
- **Purpose:** Full-page view for resume/cover generation flow
- **Called by:** `App.tsx:197`
- **Calls:** `roleFromLead()` from `leadUtils`
- **Side effects:** `setInterval` polling (L46-58), `URL.createObjectURL`/`revokeObjectURL` (L73-79, L96-103), `window.dispatchEvent(new CustomEvent("leads-refresh"))` (L134), `navigator.clipboard.writeText` (L141)
- **Hardcodes:** polling interval 1800ms (L53)
- **Flag:** 🔵 HARDCODED — 1800ms poll interval should be a constant; 🔴 DEAD — `port` prop is accepted but never used in the component body (L7 declares it, L111 checks it, but no actual port-dependent logic)

**Key state machine (lines 10-17):**
```
input, lead, busy, err, resumeBlobUrl, coverBlobUrl, resumeLoadErr, coverLoadErr
```

**Polling mechanism (lines 43-58):**
- Uses `setInterval` + `alive` flag pattern (correct cleanup)
- Polls every 1800ms hardcoded
- Swallows fetch errors silently (`catch { /* keep waiting */ }`)
- Only active when `!resumeReady || !coverReady`
- 🟡 SUSPECT — if the backend returns a non-ok response consistently, polling never stops and never shows error to user

**PDF loading (lines 60-104):**
- Two parallel `useEffect` hooks for resume PDF and cover letter PDF
- Both use `api(path) → blob → URL.createObjectURL` pattern
- Lifespan tracked via `revoke` variable; cleanup calls `URL.revokeObjectURL`
- Error message extraction uses `e instanceof Error ? e.message : ...` (consistent)

**Submit flow (lines 110-139):**
1. POST `/api/v1/leads/manual` — creates lead
2. POST `/api/v1/leads/{id}/generate` — triggers generation
3. On success: dispatches `leads-refresh` CustomEvent
4. Error: stringified into `err` state (displayed in red banner)

**Exports:**

| Export | Known importers |
|--------|----------------|
| `ApplyJobView` | `App.tsx` |

---

### `DashboardView.tsx`

**Purpose:** The home/landing screen. Displays agent status, summary stats (active, scored, ready, applied), top 4 leads by signal score, maintenance panel (rescore, cleanup), and follow-up count. Purely presentational — all state lives in `App.tsx`.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `Icon` from `../components/Icon` | local | yes | 🟢 CLEAN |
| `React` | stdlib | yes | 🟢 CLEAN |
| `Lead`, `LogLine`, `View` from `../types` | local | yes | 🟢 CLEAN |
| `getMark`, `getTone`, `leadDisplayHeading`, `leadSignal` from `../lib/leadUtils` | local | yes | 🟢 CLEAN |

**Module-level constants & state (lines 6-8):**
| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `warmSurface` | string | `"rgba(255, 255, 255, 0.64)"` | `LeadRow`, `SecondaryButton`, JSX | 🟢 CLEAN — consistent theme |
| `warmSurfaceStrong` | string | `"rgba(255, 255, 255, 0.78)"` | `LeadRow`, `SecondaryButton` | 🟢 CLEAN |
| `warmBorder` | string | `"rgba(201, 100, 66, 0.16)"` | JSX | 🟢 CLEAN — shared tone variable |

**Local components:**

#### `MiniStat({ tone, label, value, hint, icon })`
- **Purpose:** Stat card with icon, large number, label
- **Called by:** `DashboardView` render (L229-233)
- **Calls:** none
- **Side effects:** none
- **Flag:** 🟢 CLEAN

#### `LeadRow({ lead, openDrawer })`
- **Purpose:** Single lead row with signal badge
- **Called by:** `DashboardView` render (L255)
- **Calls:** `leadDisplayHeading()`, `leadSignal()`, `getTone()`, `getMark()`
- **Side effects:** none
- **Flag:** 🟢 CLEAN

#### `SecondaryButton({ children, onClick, disabled?, danger? })`
- **Purpose:** Themed secondary button
- **Called by:** `DashboardView` render (L194-202, L271-284)
- **Calls:** none
- **Side effects:** none
- **Flag:** 🟢 CLEAN

**Main function:**

#### `DashboardView({ leads, dueFollowups, logs, setView, openDrawer, scanning, reevaluating, cleaning, onScan, onStopScan, onReevaluate, onStopReevaluate, onCleanup, scanErr })`
- **Purpose:** Render the home dashboard
- **Called by:** `App.tsx:198`
- **Calls:** local components (`MiniStat`, `LeadRow`, `SecondaryButton`), `leadSignal()`, `leadDisplayHeading()`
- **Side effects:** none (all callbacks passed from parent)
- **Hardcodes:** 4-lead queue limit at line 131
- **Flag:** 🟢 CLEAN — well-scoped, no logic leaks

**Exports:**

| Export | Known importers |
|--------|----------------|
| `DashboardView` | `App.tsx` |

---

### `GraphView.tsx`

**Purpose:** Visualizes the Kuzu local graph's node-type distribution as a pentagon radar chart and a list of per-type counts. Pure presentational — receives `GraphStats` and renders SVG.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `Icon` from `../components/Icon` | local | yes | 🟢 CLEAN |
| `GraphStats` from `../types` | local | yes | 🟢 CLEAN |

**Module-level constants & state:** None.

**Functions:**

#### `PentagonGraph({ stats }: { stats: any[] })`
- **Purpose:** SVG radar chart for 5 vertex types
- **Called by:** `GraphView` render (L102)
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** `cx=130, cy=125, R=80`, 5 vertices, polar angle offsets
- **Flag:** 🟡 SUSPECT — stats parameter typed as `any[]` instead of typed interface (line 4); should use `{ key: string; count: number; tone: string }[]`

#### `GraphView({ stats }: { stats: GraphStats })`
- **Purpose:** Full page with pentagon + node list
- **Called by:** `App.tsx:201`
- **Calls:** `PentagonGraph`
- **Side effects:** none
- **Flag:** 🟢 CLEAN

**Exports:**

| Export | Known importers |
|--------|----------------|
| `GraphView` | `App.tsx` |

---

### `IngestionView.tsx`

**Purpose:** 8-tab context import page. Each tab handles a distinct ingestion source: resume PDF upload, manual form (skills/experience/projects), raw text paste, resume template save/edit, LinkedIn zip import, GitHub profile scan, portfolio URL scan, and structured JSON import. Centralized `status` state machine drives feedback.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useEffect`, `useState` from `react` | stdlib | yes | 🟢 CLEAN |
| `motion` from `framer-motion` | 3rd-party | yes | 🟢 CLEAN |
| `Icon` from `../components/Icon` | local | yes | 🟢 CLEAN |
| `ApiFetch` from `../types` | local | yes | 🟢 CLEAN |

**Module-level state (all in component, lines 7-33):**

| Name | Type | Default | Used by | Flag |
|------|------|---------|---------|------|
| `status` | `"idle"\|"loading"\|"done"\|"error"` | `"idle"` | All ingestion functions | 🟢 CLEAN — shared state machine |
| `activeTab` | union of 8 tab IDs | `"resume"` | Tab switching, conditional renders | 🟢 CLEAN |
| `skillForm`, `expForm`, `projForm` | objects | empty strings | `addManual()` | 🟢 CLEAN |
| `rawText` | string | `""` | `ingestRaw()` | 🟢 CLEAN |
| `template`, `templateLoaded` | string, bool | `""`, `false` | Template save/load | 🟢 CLEAN — guards re-fetch |
| `linkedinFile`, `linkedinResult` | File \| null, any | `null`, `null` | `ingestLinkedin()` | 🟢 CLEAN |
| `githubUsername`, `githubToken`, `githubResult`, `showToken`, `githubMaxRepos` | various | defaults | `ingestGithub()` | 🟢 CLEAN |
| `portfolioUrl`, `portfolioResult` | string, any | `""`, `null` | `scanPortfolio()` | 🟢 CLEAN |
| `jsonText`, `jsonError`, `jsonResult` | string, string\|null, any | defaults | `importProfileJson()`, `downloadProfileTemplate()` | 🟢 CLEAN |

**Functions:**

#### `saveTemplate()`
- **Purpose:** POST template content to backend
- **Called by:** "Save Template" button (L537)
- **Calls:** `api()`, `setStatus()`
- **Side effects:** writes to server
- **Flag:** 🟢 CLEAN

#### `addManual(type, data)`
- **Purpose:** POST a skill/experience/project to profile
- **Called by:** 3 "Add *" buttons (L278, L286, L294)
- **Calls:** `api()`, form reset logic
- **Side effects:** writes to server, resets form on success
- **Flag:** 🟡 SUSPECT — endpoint mapping `type === "exp" ? "experience" : type` (L59) is fragile; could silently misroute if new types added

#### `ingestResume(file)`
- **Purpose:** Upload PDF to `/api/v1/ingest`
- **Called by:** file input onChange (L260)
- **Calls:** `api()`, `FormData`
- **Side effects:** file upload
- **Flag:** 🟢 CLEAN

#### `ingestLinkedin()`
- **Purpose:** Upload LinkedIn zip export
- **Called by:** "Import LinkedIn data" button (L337)
- **Calls:** `api()`, `FormData`
- **Side effects:** file upload, sets `linkedinResult`
- **Flag:** 🟢 CLEAN

#### `ingestGithub()`
- **Purpose:** POST GitHub username + optional token
- **Called by:** "Scan GitHub profile" button (L387)
- **Calls:** `api()`, sets `githubResult`
- **Side effects:** server-side API call to GitHub
- **Flag:** 🟢 CLEAN — well-structured with specific 404 handling (L111-113)

#### `scanPortfolio(autoImport)`
- **Purpose:** POST portfolio URL, optionally auto-import
- **Called by:** "Scan portfolio" + "Import to Knowledge Brain" buttons (L430, L456)
- **Calls:** `api()`, sets `portfolioResult`
- **Side effects:** server-side scrape
- **Flag:** 🟢 CLEAN

#### `downloadProfileTemplate()`
- **Purpose:** Fetch profile template JSON and trigger browser download
- **Called by:** "Download template" button (L477)
- **Calls:** `api()`, `document.createElement('a')`, `URL.createObjectURL`
- **Side effects:** DOM manipulation, file download
- **Flag:** 🟢 CLEAN

#### `importProfileJson()`
- **Purpose:** Validate and POST structured profile JSON
- **Called by:** "Import profile" button (L487)
- **Calls:** `JSON.parse()`, `api()`, sets `jsonResult`/`jsonError`
- **Side effects:** writes to server
- **Flag:** 🟢 CLEAN — proper local validation before network call

#### `ingestRaw()`
- **Purpose:** POST raw text to ingestion
- **Called by:** "Sync Raw Context" button (L303)
- **Calls:** `api()`, `FormData`
- **Side effects:** writes to server, clears `rawText` on success
- **Flag:** 🟢 CLEAN

**CRITICAL PATTERN — try/catch uniformity (lines 44-196):**
All 8 ingestion functions follow the same pattern:
```ts
setStatus("loading");
try {
  const r = await api(...);
  setStatus(r.ok ? "done" : "error");
} catch { setStatus("error"); }
```
This is **consistent** but **completely swallows error details**. The user sees "Saved successfully!" or "An error occurred." — there is no mechanism to surface server-side error messages in any ingestion tab except JSON import (which has `jsonError`) and portfolio/GitHub (which use per-source error fields).

- **Flag:** 🔵 HARDCODED — line 256-262 "Drop a fresh Resume PDF" section uses `document.getElementById("pdf-in")` instead of a React ref

**Template lazy-loading guard (lines 36-42):**
- `useEffect` only fires when `activeTab === "template"` and `!templateLoaded`
- Prevents redundant network calls when user switches away and back
- 🟢 CLEAN pattern

**Tab definitions (lines 199-208):**
- 8 tabs defined as const array with icon/description/accent metadata
- All tabs rendered unconditionally, content conditionally
- 🟢 CLEAN

**Animated alerts (lines 244-253):**
- `motion.div` for success/error toasts with enter animation
- 🟢 CLEAN

**Exports:**

| Export | Known importers |
|--------|----------------|
| `IngestionView` | `App.tsx` |

---

### `LeadInboxView.tsx`

**Purpose:** Two-panel lead creation page: manual lead form (URL + text) and free-source scan trigger. Simple, self-contained.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useState` from `react` | stdlib | yes | 🟢 CLEAN |
| `Icon` from `../components/Icon` | local | yes | 🟢 CLEAN |
| `ApiFetch`, `Lead` from `../types` | local | yes | 🟢 CLEAN |

**Functions:**

#### `LeadInboxView({ port, api, onCreated })`
- **Purpose:** Create leads manually or trigger free-source scan
- **Called by:** `App.tsx:199`
- **Calls:** `api()`
- **Side effects:** `onCreated()` callback on success
- **Hardcodes:** `kind = "job"` at L6
- **Flag:** 🟢 CLEAN

#### `submit()`
- **Purpose:** POST manual lead
- **Flag:** 🟢 CLEAN — proper `finally` block resets `busy` (L33-35)

#### `scanFree()`
- **Purpose:** POST free-source scan
- **Flag:** 🟢 CLEAN — identical pattern to `submit()`

**Exports:**

| Export | Known importers |
|--------|----------------|
| `LeadInboxView` | `App.tsx` |

---

### `PipelineView.tsx`

**Purpose:** Full lead management page: tabbed pipeline stages (All/Hot/New/Rated/Ready/Active/Discarded), search/filter/sort bar, bulk delete (Discarded tab only), CSV export. The most stateful view.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useEffect`, `useMemo`, `useState` from `react` | stdlib | yes | 🟢 CLEAN |
| `Icon` from `../components/Icon` | local | yes | 🟢 CLEAN |
| `LeadFilterBar` from `../components/LeadFilterBar` | local | yes | 🟢 CLEAN |
| `PipelineJobCard`, `PipelineSkeleton` from `../components/JobCard` | local | yes | 🟢 CLEAN |
| `ApiFetch`, `Lead`, `LeadSort`, `PipelineTab`, `SeniorityFilter` from `../types` | local | yes | 🟢 CLEAN |
| `PAGE_SIZE`, `leadSearchText`, `sortLeads`, `seniorityMatches`, `uniqueLeadValues` from `../lib/leadUtils` | local | yes | 🟢 CLEAN |

**State (lines 14-26):**
| Name | Type | Default | Purpose | Flag |
|------|------|---------|---------|------|
| `tab` | `PipelineTab` | `"all"` | Active pipeline stage | 🟢 |
| `search` | string | `""` | Text search | 🟢 |
| `platform` | string | `""` | Platform filter | 🟢 |
| `minSignal` | number | 0 | Min signal score | 🟢 |
| `minMatch` | number | 0 | Min match score | 🟢 |
| `sort` | `LeadSort` | `"recommended"` | Sort order | 🟢 |
| `budgetOnly` | boolean | false | Budget filter | 🟢 |
| `learningOnly` | boolean | false | Learning delta filter | 🟢 |
| `seniority` | `SeniorityFilter` | `"all"` | Seniority filter | 🟢 |
| `visibleCount` | number | `PAGE_SIZE` | Pagination | 🟡 SUSPECT — reset to `PAGE_SIZE` on any filter change (L28), loses user's "load more" progress |
| `bulkSelecting` | boolean | false | Bulk delete mode | 🟢 |
| `selected` | `Set<string>` | empty | Selected lead IDs | 🟢 |
| `exporting` | boolean | false | CSV export lock | 🟢 |

**Functions:**

#### `PipelineView({ leads, openDrawer, deleteLead, port, api, ... })`
- **Purpose:** Full pipeline management view
- **Called by:** `App.tsx:200`
- **Calls:** `LeadFilterBar`, `PipelineJobCard`, `PipelineSkeleton`, `leadSearchText()`, `sortLeads()`, `seniorityMatches()`, `uniqueLeadValues()`
- **Side effects:** `window.confirm()` in `bulkDelete()` (L85), DOM manipulation in `exportCsv()` (L98-103)
- **Hardcodes:** `PAGE_SIZE` (from leadUtils), CSV filename `"jhm_pipeline.csv"` (L101)

**Tab memoization (lines 32-55):**
- Uses `useMemo` with all filter/sort values as deps
- Each tab filters the master list independently based on tab-specific criteria
- `visibleCount` is reset via `useEffect` (L28) when filters change

**Bulk delete (lines 84-89):**
- `window.confirm()` confirmation dialog
- Iterates sequentially over selected IDs calling `deleteLead()` (no `Promise.all`)
- Resets selection afterward

**CSV Export (lines 91-107):**
- GET `/api/v1/leads/export.csv` → blob → download link with `URL.createObjectURL`
- Proper `finally` block resets `exporting` flag

**Exports:**

| Export | Known importers |
|--------|----------------|
| `PipelineView` | `App.tsx` |

---

### `ProfileView.tsx`

**Purpose:** Candidate Identity Graph viewer/editor. Displays skills (with inferred ranking), experience (timeline), and projects (grid). CRUD via `api(..., { method: "DELETE" })` and `api(..., { method: "PUT" })`. Has a map/relationship visualization with SVG connectors.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useCallback`, `useEffect`, `useMemo`, `useState` from `react` | stdlib | yes | 🟢 CLEAN |
| `Icon` from `../components/Icon` | local | yes | 🟢 CLEAN |
| `ApiFetch`, `View` from `../types` | local | yes | 🟢 CLEAN |

**State (lines 11-19):**
| Name | Type | Default | Purpose | Flag |
|------|------|---------|---------|------|
| `profile` | any | `null` | Full profile data | 🟡 SUSPECT — typed `any` |
| `profileErr` | string\|null | `null` | Profile load error | 🟢 |
| `actionError` | string\|null | `null` | CRUD action error | 🟢 |
| `editId` | string\|null | `null` | Currently editing item ID | 🟢 |
| `editData` | any | `null` | Edit form state | 🟡 SUSPECT — typed `any` |
| `editingCandidate` | boolean | false | Candidate name/summary editor | 🟢 |
| `candForm` | `{ n, s }` | empty | Candidate edit form | 🟢 |
| `activeProfileTab` | `"skills"\|"experience"\|"projects"` | `"skills"` | Detail tabs | 🟢 |
| `expandedProfileList` | boolean | false | Show all toggle | 🟢 |

**Functions:**

#### `stackItems(stack) → string[]`
- **Purpose:** Normalize stack values (handles array, string, comma-separated)
- **Called by:** `skillRanks` memo, render
- **Side effects:** none
- **Flag:** 🟢 CLEAN — defensive parsing

#### `fetchProfile()`
- **Purpose:** GET profile from backend with detailed error handling
- **Called by:** `useEffect` on mount, after CRUD operations
- **Calls:** `api()`, `setProfile()`, `setProfileErr()`
- **Side effects:** network read
- **Flag:** 🟢 CLEAN — validates response shape (L26-28)

#### `deleteItem(type, id)`
- **Purpose:** DELETE a skill/experience/project
- **Called by:** delete buttons in each tab
- **Calls:** `window.confirm()`, `api()`, `fetchProfile()`
- **Side effects:** writes to server, re-fetches profile
- **Flag:** 🟢 CLEAN — proper error fallback chain

#### `saveEdit(type, id)`
- **Purpose:** PUT updated item
- **Called by:** Save button in inline editor
- **Calls:** `api()`, `fetchProfile()`, `setEditId(null)`
- **Side effects:** writes to server
- **Flag:** 🟢 CLEAN

#### `saveCandidate()`
- **Purpose:** PUT candidate name/summary
- **Called by:** "Save Identity" button
- **Calls:** `api()`, `fetchProfile()`, `setEditingCandidate(false)`
- **Side effects:** writes to server
- **Flag:** 🟢 CLEAN

#### `skillRanks` (useMemo, lines 111-124)
- **Purpose:** Compute weighted skill ranking from skills + projects.stacks + experience.stack
- **Called by:** render for skills tab
- **Side effects:** none
- **Flag:** 🟢 CLEAN — smart accumulation with bump weights (skill=1, project.stack=3, exp.stack=2)

**Window event listener (lines 39-52):**
- `useEffect` registers a `profile-export` event listener on window
- On trigger, serializes profile as JSON download
- Proper cleanup via returned unsubscribe function
- 🟢 CLEAN pattern

**Exports:**

| Export | Known importers |
|--------|----------------|
| `ProfileView` | `App.tsx`, `ProfileView.test.tsx` |

---

### `ProfileView.test.tsx`

**Purpose:** Vitest test suite for ProfileView error visibility. 3 describe blocks covering `deleteItem`, `saveEdit`, and `saveCandidate` error states. Uses `@testing-library/react` with mocked `ApiFetch`.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `fireEvent`, `render`, `screen`, `waitFor` from `@testing-library/react` | 3rd-party | yes | 🟢 CLEAN |
| `afterEach`, `describe`, `expect`, `it`, `vi` from `vitest` | 3rd-party | yes | 🟢 CLEAN |
| `ProfileView` from `./ProfileView` | local | yes | 🟢 CLEAN |

**Test helpers (lines 19-40):**

| Helper | Purpose | Flag |
|--------|---------|------|
| `okResponse(body?)` | Creates 200 Response | 🟢 CLEAN |
| `errResponse(status, detail?)` | Creates error Response with optional detail body | 🟢 CLEAN |
| `makeApi()` | Creates mocked `ApiFetch` with default impl | 🟢 CLEAN |
| `renderView(api?)` | Renders `ProfileView` and waits for load | 🟢 CLEAN |

**Test coverage:**

| Test | What it verifies | Flag |
|------|-----------------|------|
| deleteItem 500 | Error text shown on server error | 🟢 CLEAN |
| deleteItem success | No error shown on success | 🟢 CLEAN |
| deleteItem 422 detail | Exact server detail shown | 🟢 CLEAN |
| deleteItem retry clears error | Error cleared on subsequent successful delete | 🟢 CLEAN |
| deleteItem fetch throw fallback | Fallback "Failed to delete item" on empty error | 🟢 CLEAN |
| saveEdit 500 | Error shown on server error | 🟢 CLEAN |
| saveEdit 422 detail | Exact server detail shown | 🟢 CLEAN |
| saveCandidate 500 | Error shown on server error | 🟢 CLEAN |
| saveCandidate 422 detail | Exact server detail shown | 🟢 CLEAN |
| saveCandidate retry clears error | Error cleared on subsequent success | 🟢 CLEAN |
| saveCandidate throw fallback | Fallback "Failed to save identity" on empty error | 🟢 CLEAN |

**Flag:** 🟢 CLEAN — comprehensive error-state coverage, well-structured test helpers

**Exports:** None (test file).

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P0 | 🔴 DEAD | `port` prop | `ApplyJobView.tsx:7` | Declared in props, checked in guard (L111), but never used for any actual port-dependent operation |
| P1 | 🔵 HARDCODED | Poll interval (1800) | `ApplyJobView.tsx:53` | Should be a module constant, not a magic number |
| P1 | 🔵 HARDCODED | `document.getElementById` | `IngestionView.tsx:260` | Uses string ID instead of React ref for file input trigger |
| P1 | 🔵 HARDCODED | Error swallowing | `IngestionView.tsx:44-196` | All 8 ingestion functions use `catch { setStatus("error") }` — no error detail surfaces to user |
| P2 | 🟡 SUSPECT | Log filter fragility | `ActivityView.tsx:37-39` | `msg.toLowerCase().includes()` could silently break if server changes log message format |
| P2 | 🟡 SUSPECT | Silent polling failure | `ApplyJobView.tsx:52` | `catch { /* keep waiting */ }` never informs user of persistent failures |
| P2 | 🟡 SUSPECT | `PentagonGraph` `any[]` param | `GraphView.tsx:4` | Should have a typed interface instead of `any[]` |
| P2 | 🟡 SUSPECT | visibleCount reset | `PipelineView.tsx:28` | Resets pagination to 1st page on ANY filter change, losing scroll position |
| P2 | 🟡 SUSPECT | Endpoint mapping switch | `IngestionView.tsx:59` | `type === "exp" ? "experience" : type` fragile if new types added |
| P2 | 🟡 SUSPECT | Profile/EditData typed `any` | `ProfileView.tsx:11,15` | `profile` and `editData` both typed `any` — no type safety |
| P3 | 🟢 CLEAN | General architecture | All files | Views are well-structured, props are explicit, side effects managed |
| P3 | 🟢 CLEAN | Test coverage | `ProfileView.test.tsx` | 11 tests covering error visibility with mocks, retry clearing, fallback messages |

---

## 5. Dependencies

**Inbound (other units depend on this):**
| Consumer | Imports |
|----------|---------|
| `App.tsx` | All 8 view components (lines 15-22, 197-204) |

**Outbound (this unit depends on others):**
| Unit | Used by | Files |
|------|---------|-------|
| `src/types` | All views | `ActivityView`, `ApplyJobView`, `DashboardView`, `GraphView`, `IngestionView`, `LeadInboxView`, `PipelineView`, `ProfileView` |
| `src/lib/leadUtils` | `DashboardView`, `ApplyJobView`, `PipelineView` | `getMark`, `getTone`, `leadDisplayHeading`, `leadSignal`, `roleFromLead`, `PAGE_SIZE`, `leadSearchText`, `sortLeads`, `seniorityMatches`, `uniqueLeadValues` |
| `src/components/Icon` | `DashboardView`, `GraphView`, `PipelineView`, `LeadInboxView`, `ApplyJobView`, `IngestionView`, `ProfileView` | `Icon` component |
| `src/components/LeadFilterBar` | `PipelineView` | `LeadFilterBar` |
| `src/components/JobCard` | `PipelineView` | `PipelineJobCard`, `PipelineSkeleton` |
| `@tauri-apps/plugin-opener` | `ApplyJobView` | `openUrl` |
| `framer-motion` | `IngestionView` | `motion` |

**External (third-party libs used):**

| Library | Used for | Version pin? | Flag |
|---------|----------|-------------|------|
| `react` | All views | via `package.json` | 🟢 |
| `@tauri-apps/plugin-opener` | Opening PDFs in system viewer | via `package.json` | 🟢 |
| `framer-motion` | Entry animations in IngestionView | via `package.json` | 🟢 |

---

## 6. First principles assessment

### `ActivityView.tsx`
1. **Does this file need to exist?** Yes — dedicated log stream page
2. **Does it do what it claims?** Yes — name matches
3. **Is it the right place for this logic?** Yes — UI-only, no business logic
4. **What would break if deleted?** The Activity tab in the app would render nothing; `App.tsx` would fail to import

### `ApplyJobView.tsx`
1. **Does this file need to exist?** Yes — distinct view for job customization package
2. **Does it do what it claims?** Yes
3. **Is it the right place for this logic?** Partially — the polling and PDF loading logic could arguably live in custom hooks, but inline is acceptable
4. **What would break if deleted?** The "Customize job" feature from dashboard, the "apply" view route in App.tsx

### `DashboardView.tsx`
1. **Does this file need to exist?** Yes — home screen
2. **Does it do what it claims?** Yes
3. **Is it the right place for this logic?** Yes — purely presentational
4. **What would break if deleted?** The entire app would have no landing page; `App.tsx` import breaks

### `GraphView.tsx`
1. **Does this file need to exist?** Yes — knowledge graph visualization
2. **Does it do what it claims?** Yes
3. **Is it the right place for this logic?** Yes
4. **What would break if deleted?** Graph tab would be missing; `App.tsx` import breaks

### `IngestionView.tsx`
1. **Does this file need to exist?** Yes — multi-tab ingestion is a core feature
2. **Does it do what it claims?** Yes
3. **Is it the right place for this logic?** No — 553 lines is too large for a single component; each tab could be extracted to `src/views/ingestion/*.tsx`
4. **What would break if deleted?** All 8 ingestion sources (resume, manual, LinkedIn, GitHub, portfolio, JSON, raw, template) would be inaccessible

### `LeadInboxView.tsx`
1. **Does this file need to exist?** Yes
2. **Does it do what it claims?** Yes
3. **Is it the right place for this logic?** Yes — small, focused
4. **What would break if deleted?** Manual lead creation and free-source scan would be gone

### `PipelineView.tsx`
1. **Does this file need to exist?** Yes
2. **Does it do what it claims?** Yes — pipeline management
3. **Is it the right place for this logic?** Yes — contains substantial filter/sort/pagination state that belongs in a view
4. **What would break if deleted?** Lead pipeline, bulk delete, CSV export, filters, sorting — core functionality

### `ProfileView.tsx`
1. **Does this file need to exist?** Yes
2. **Does it do what it claims?** Yes
3. **Is it the right place for this logic?** Yes — includes CRUD, inline editing, evidence map
4. **What would break if deleted?** Profile viewing/editing is inaccessible; `ProfileView.test.tsx` fails

### `ProfileView.test.tsx`
1. **Does this file need to exist?** Yes — only test file for views unit
2. **Does it do what it claims?** Yes — tests error visibility for CRUD operations
3. **Is it the right place for this logic?** Yes — collocated with tested component
4. **What would break if deleted?** No automated regression coverage for ProfileView error states
