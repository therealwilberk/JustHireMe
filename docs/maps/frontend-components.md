# Map: frontend-components
**File:** `docs/maps/frontend-components.md`
**Codebase path(s):** `src/components/*.tsx`
**Files in scope:** 11
**Total lines:** ~2,420
**Generated:** 2026-05-15

---

## 1. Unit summary

Collection of 11 React TSX components forming the top-level UI building blocks of the Tauri desktop app. Owns the sidebar navigation, topbar, job lead detail drawer, onboarding wizard, help chat, icon library, error boundary, update prompt, and filtering/list controls for the pipeline view. Depends on `src/types.ts` for shared types (`Lead`, `ApiFetch`, `View`, `LeadSort`, etc.) and `src/lib/leadUtils.ts` for display helpers. Consumed primarily by `src/App.tsx` and `src/views/PipelineView.tsx`.

---

## 2. File inventory

| # | File | Lines | Purpose | Flag |
|---|------|-------|---------|------|
| 1 | `ApprovalDrawer.tsx` | 642 | Full lead detail modal: PDF preview, versioning, feedback, outreach drafts, score display, auto-apply trigger | 🟠 |
| 2 | `ErrorBoundary.tsx` | 38 | Class-based React error boundary with retry button | 🟢 |
| 3 | `FormReader.tsx` | 279 | Reads ATS form fields from a job URL, shows extracted fields with confidence dots | 🟢 |
| 4 | `HelpChat.tsx` | 90 | In-app chat panel that POSTs questions to `/api/v1/help/chat` | 🟢 |
| 5 | `Icon.tsx` | 249 | SVG icon library: 30 icons rendered via a `switch` on `name` prop | 🟢 |
| 6 | `JobCard.tsx` | 256 | Three exports: `JobCard` (unused), `PipelineJobCard`, `PipelineSkeleton` | 🟠 |
| 7 | `LeadFilterBar.tsx` | 105 | Filter bar for pipeline view: search, platform, seniority, sort, signal/match thresholds | 🟢 |
| 8 | `OnboardingWizard.tsx` | 345 | Multi-step first-run wizard: resume import, AI setup, tour, demo job | 🟢 |
| 9 | `Sidebar.tsx` | 109 | Left nav with workspace links, lead count snapshot, online status | 🟢 |
| 10 | `Topbar.tsx` | 65 | View title/subtitle header, plus `StatCard` (unused) | 🟠 |
| 11 | `UpdatePrompt.tsx` | 110 | Tauri updater toast: checks, downloads, installs, dismisses | 🟢 |

---

## 3. Detailed breakdown

### `ApprovalDrawer.tsx`

**Purpose:** Modal drawer opened when a lead is selected for approval. Shows PDF preview (iframes via blob URLs), version history dropdown, keyword coverage visualization, lead signal/proof pack/outreach sections, score bar, feedback buttons, follow-up scheduling, match points, skill gaps, form reader integration, and the experimental auto-apply button. Core interaction point for lead disposition.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useCallback, useEffect, useState` | stdlib (react) | yes | 🟢 |
| `motion` | 3rd-party (framer-motion) | yes (line 231) | 🟢 |
| `openUrl` | 3rd-party (tauri) | yes (lines 170, 255) | 🟢 |
| `Icon` | local | yes | 🟢 |
| `ApiFetch, KeywordCoverage, Lead` | local (types) | yes | 🟢 |
| `cleanLeadText, getTone, leadDisplayHeading` | local (leadUtils) | yes | 🟢 |
| `FormReader` | local | yes (line 606) | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| (none — all state is component-local) |
| `firing` | boolean | false | `fire()` | 🟢 |
| `done` | boolean | false | render line 614 | 🟢 |
| `generating` | boolean | false | `generatePdf()`, 2x effects | 🟢 |
| `activeDoc` | `DocKind` | `"resume"` | tab toggle, PDF path derivation | 🟢 |
| `pdfBlobUrl` | string\|null | null | effect lines 90-113, render | 🟢 |
| `pdfLoadErr` | string\|null | null | effect lines 90-113, render | 🟢 |
| `generateErr` | string\|null | null | `generatePdf()` | 🟢 |
| `pipelineRunning` | boolean | false | `runPipeline()` | 🟢 |
| `pipelineMsg` | string\|null | null | `runPipeline()` | 🟢 |
| `fireErr` | string\|null | null | `fire()` | 🟢 |
| `feedbackBusy` | string\|null | null | `submitFeedback()` | 🟡 SUSPECT — typed as `string` but used as feedback ID string, effectively a boolean surrogate per-button |
| `feedbackErr` | string\|null | null | feedback/followup error display | 🟢 |
| `followupBusy` | number\|null | null | `scheduleFollowup()` | 🟢 |
| `versions` | VersionEntry[] | [] | `loadVersions()` | 🟢 |
| `selectedVersion` | number\|null | null | version selector | 🟢 |
| `versionErr` | string\|null | null | `loadVersions()` | 🟢 |
| `experimentalAutoApply` | boolean | false | settings fetch effect | 🟢 |

**Functions:**

#### `loadVersions() -> Promise<void>`
- **Purpose:** Fetches version history for the lead's generated documents
- **Called by:** mount effect (line 78)
- **Calls:** none in-file
- **Side effects:** 2 state sets (`setVersions`, `setSelectedVersion`)
- **Hardcodes:** `GET /api/v1/leads/${j.job_id}/versions`
- **Flag:** 🟢

#### `fire() -> Promise<void>`
- **Purpose:** Triggers experimental auto-apply via POST
- **Called by:** render (line 617 onClick)
- **Calls:** none in-file
- **Side effects:** 3 state sets, `setTimeout(onFired, 1500)`
- **Hardcodes:** `POST /api/v1/fire/${j.job_id}`
- **Flag:** 🟢

#### `generatePdf() -> Promise<void>`
- **Purpose:** POSTs to trigger PDF generation for this lead
- **Called by:** render (lines 284, 394 onClick)
- **Calls:** `loadVersions()`
- **Side effects:** 5 state sets, `window.dispatchEvent("leads-refresh")`
- **Hardcodes:** `POST /api/v1/leads/${j.job_id}/generate`
- **Flag:** 🟢

#### `runPipeline() -> Promise<void>`
- **Purpose:** Starts the full pipeline for this lead
- **Called by:** render (line 288 onClick)
- **Calls:** none in-file
- **Side effects:** 2 state sets, `setTimeout` to clear running flag after 3s
- **Hardcodes:** `POST /api/v1/leads/${j.job_id}/pipeline/run`
- **Flag:** 🟡 SUSPECT — hardcoded 3s timeout to reset `pipelineRunning` is a race condition; pipeline could finish before or after

#### `openPdf() -> void`
- **Purpose:** Opens PDF blob URL in system viewer via Tauri
- **Called by:** render (line 276 onClick)
- **Calls:** `openUrl(pdfBlobUrl)`
- **Side effects:** system process launch
- **Flag:** 🟢

#### `submitFeedback(feedback: string) -> Promise<void>`
- **Purpose:** Sends lead feedback (relevant/not_relevant/etc.) to backend
- **Called by:** render (line 511 onClick)
- **Calls:** none in-file
- **Side effects:** 2-3 state sets, API PUT
- **Hardcodes:** `PUT /api/v1/leads/${j.job_id}/feedback`
- **Flag:** 🟢

#### `scheduleFollowup(days: number) -> Promise<void>`
- **Purpose:** Schedules a follow-up reminder for N days
- **Called by:** render (line 527 onClick)
- **Calls:** none in-file
- **Side effects:** 2-3 state sets, API PUT
- **Hardcodes:** `PUT /api/v1/leads/${j.job_id}/followup`
- **Flag:** 🟢

**Exports:**

| Export | Known importers |
|--------|----------------|
| `ApprovalDrawer` | `src/App.tsx:210` |

**Re-render risk analysis (18 useState calls):**
- Every keypress or API call triggers cascading re-renders of the entire 642-line subtree including FormReader
- `feedbackBusy` changes on every feedback button click (6 buttons), rerenders all 6
- `followupBusy` changes on every follow-up click, rerenders all follow-up buttons
- Suggestion: split into smaller sub-components (ScoreSection, FeedbackBar, VersionSelector, PdfPane) to isolate re-render scope

---

### `ErrorBoundary.tsx`

**Purpose:** Class-based React error boundary. Catches render errors in children, displays a "failed to load" message with a retry button that resets state.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `React` | stdlib | yes | 🟢 |

**Classes:**

#### `ErrorBoundary`
- **Inherits from:** `React.Component<Props, State>`
- **Purpose:** Catch render errors in wrapped children
- **Still needed:** yes
- **Flag:** 🟢

| Method | Params | Returns | Purpose | Flag |
|--------|--------|---------|---------|------|
| `getDerivedStateFromError` | e: Error | `{ error }` | Capture error into state | 🟢 |
| `componentDidCatch` | e, info | void | Logs `[ErrorBoundary:label]` to console | 🟢 |
| `render` | none | JSX | Shows error UI or children | 🟢 |

**Exports:**

| Export | Known importers |
|--------|----------------|
| `ErrorBoundary` (default) | `src/App.tsx:14` |

---

### `FormReader.tsx`

**Purpose:** Embedded form reader inside ApprovalDrawer. Accepts a job URL, POSTs to `/api/v1/leads/{jobId}/form/read`, displays extracted fields with confidence indicators, copy buttons, screenshot, and unmatched field lists.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useState` | stdlib | yes | 🟢 |
| `ApiFetch, FormField, FormReadResult` | local (types) | yes | 🟢 |

**Functions:**

#### `readForm() -> Promise<void>`
- **Purpose:** POSTs URL to backend form reader API, sets result state
- **Called by:** render (line 100)
- **Calls:** none in-file
- **Side effects:** 2-4 state sets
- **Hardcodes:** `POST /api/v1/leads/${jobId}/form/read`
- **Flag:** 🟢

#### `copy(text, key) -> void`
- **Purpose:** Copies text to clipboard, shows "Copied!" for 1.5s
- **Called by:** `copyAll()`, individual copy buttons
- **Calls:** none
- **Side effects:** clipboard write, timeout
- **Flag:** 🟢

#### `copyAll() -> void`
- **Purpose:** Copies all found field answers as formatted text
- **Called by:** render (line 259)
- **Calls:** `copy()`
- **Flag:** 🟢

#### `confidenceDot(c) -> JSX.Element`
- **Purpose:** Renders green/yellow/gray dot by confidence level
- **Called by:** render (line 193)
- **Flag:** 🟢

**Exports:**

| Export | Known importers |
|--------|----------------|
| `FormReader` | `ApprovalDrawer.tsx:606` |

---

### `HelpChat.tsx`

**Purpose:** Floating help chat widget. FAB button toggles a chat panel that sends questions to `/api/v1/help/chat` with conversation history.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useMemo, useRef, useState` | stdlib | yes | 🟢 |
| `Icon` | local | yes | 🟢 |
| `ApiFetch` | local (types) | yes | 🟢 |

**Functions:**

#### `send() -> Promise<void>`
- **Purpose:** Posts question + history slice to help chat API
- **Called by:** Enter key handler, send button onClick
- **Calls:** none
- **Side effects:** 3 state sets, scrollTo
- **Hardcodes:** `POST /api/v1/help/chat`, history slice of 8 messages
- **Flag:** 🟢

**Exports:**

| Export | Known importers |
|--------|----------------|
| `HelpChat` | `src/App.tsx:25` |

---

### `Icon.tsx`

**Purpose:** SVG icon library. Exports a single default function component that switches on `name` to render one of 30 hand-drawn SVG icons.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `React` | stdlib | yes (for `CSSProperties` type) | 🟢 |

| Icon name | Lines | Flag |
|-----------|-------|------|
| `logo` | 25-31 | 🟢 |
| `home` | 33-38 | 🟢 |
| `layers` | 40-46 | 🟢 |
| `graph` | 48-57 | 🟢 |
| `pulse` | 59-63 | 🟢 |
| `user` | 65-70 | 🟢 |
| `settings` | 72-77 | 🟢 |
| `ghost` | 79-83 | 🟢 |
| `search` | 85-90 | 🟢 |
| `plus` | 92-96 | 🟢 |
| `x` | 98-102 | 🟢 |
| `arrow-right` | 104-108 | 🟢 |
| `arrow-up` | 110-114 | 🟢 |
| `upload` | 116-120 | 🟢 |
| `file` | 122-127 | 🟢 |
| `download` | 129-135 | 🟢 |
| `external` / `external-link` | 137-142 | 🟢 (alias, both names accepted) |
| `check` | 144-148 | 🟢 |
| `fire` | 150-154 | 🟢 |
| `spark` | 156-160 | 🟢 |
| `key` | 162-167 | 🟢 |
| `globe` | 169-174 | 🟢 |
| `link` | 176-181 | 🟢 |
| `filter` | 183-187 | 🟢 |
| `play` | 189-193 | 🟢 |
| `pause` | 195-199 | 🟢 |
| `clock` | 201-206 | 🟢 |
| `trending` | 208-213 | 🟢 |
| `calendar` | 215-220 | 🟢 |
| `brief` | 222-227 | 🟢 |
| `trash` | 229-233 | 🟢 |
| `edit` | 235-240 | 🟢 |
| default (fallback) | 242-247 | 🟢 — renders generic circle |

**Exports:**

| Export | Known importers |
|--------|----------------|
| `Icon` (default) | ApprovalDrawer, HelpChat, JobCard, OnboardingWizard, Topbar, Sidebar, LeadFilterBar, + 7 view/settings files |

---

### `JobCard.tsx`

**Purpose:** Houses three exports: `JobCard` (classic card), `PipelineJobCard` (pipeline-optimized horizontal card), and `PipelineSkeleton` (loading placeholder). `PipelineJobCard` and `PipelineSkeleton` are consumed by PipelineView.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useState` | stdlib | yes (in both JobCard and PipelineJobCard) | 🟢 |
| `openUrl` | 3rd-party (tauri) | yes | 🟢 |
| `Icon` | local | yes | 🟢 |
| `ApiFetch, Lead` | local (types) | yes | 🟢 |
| `getMark, getTone, leadDisplayHeading, leadSeniority, seniorityLabel, seniorityTone` | local (leadUtils) | yes | 🟢 |

**Functions:**

#### `JobCard(...)` — EXPORTED FUNCTION
- **Purpose:** Classic card rendering a single lead with description excerpt, signal/scores, quality reason, generate button, details link
- **Called by:** **UNKNOWN — 0 imports found across codebase**
- **Flag:** 🔴 DEAD — never imported anywhere. PipelineView uses `PipelineJobCard` instead.

#### `PipelineJobCard(...)` — EXPORTED FUNCTION
- **Purpose:** Pipeline-optimized horizontal card with score stack, action buttons, source URL, status badge
- **Called by:** `src/views/PipelineView.tsx`
- **Flag:** 🟢

#### `PipelineSkeleton()` — EXPORTED FUNCTION
- **Purpose:** Loading skeleton with 4 animated placeholder cards
- **Called by:** `src/views/PipelineView.tsx`
- **Flag:** 🟢

**Exports:**

| Export | Known importers |
|--------|----------------|
| `JobCard` | **none — 0 imports found** |
| `PipelineJobCard` | `src/views/PipelineView.tsx:4` |
| `PipelineSkeleton` | `src/views/PipelineView.tsx:4` |

---

### `LeadFilterBar.tsx`

**Purpose:** Filter control bar for the pipeline view. Props-drives all filter state (search, platform, seniority, sort, min scores, toggles). Pure presentational — no internal state.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `Icon` | local | yes | 🟢 |
| `LeadSort, SeniorityFilter` | local (types) | yes | 🟢 |

**Exports:**

| Export | Known importers |
|--------|----------------|
| `LeadFilterBar` | `src/views/PipelineView.tsx:3` |

**Props analysis:** 17 distinct props, all passed down from PipelineView state. The 17-prop interface suggests a sub-component extraction opportunity but is currently functional.

---

### `OnboardingWizard.tsx`

**Purpose:** Multi-step first-run wizard (Resume → AI Setup → Workspace Tour → Demo Job). Uploads resume, saves LLM provider/preferences, shows tour of app pages, and finishes with a demo job draft in the customize view.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useState` | stdlib | yes | 🟢 |
| `motion` | 3rd-party (framer-motion) | yes (lines 179-189) | 🟢 |
| `Icon` | local | yes | 🟢 |
| `ApiFetch` | local (types) | yes | 🟢 |
| `DEMO_JOB_DRAFT` | local (leadUtils) | yes (lines 17, 210) | 🟢 |

**Hardcoded data:** Contains 3 large lookup tables (60+ lines total):
- `keyField`: maps 16 provider names to settings API field names (lines 22-38)
- `modelField`: maps 16 provider names to model config field names (lines 39-55)
- `modelHints`: maps 16 provider names to suggested model names (lines 56-72)
- `providerNotes`: 16x provider descriptions (lines 73-90)
- `tourPages`: 8-page workspace tour content (lines 91-101)

**Flag:** 🔵 HARDCODED — provider list, field names, model hints, and descriptions are all encoded here and must stay in sync with backend's `config/llm.py`. These should be fetched from a `/api/v1/settings/providers` endpoint instead.

**Functions:**

#### `saveResume() -> Promise<void>`
- **Purpose:** Uploads resume file or raw text via FormData
- **Called by:** render (line 238)
- **Hardcodes:** `POST /api/v1/ingest`
- **Flag:** 🟢

#### `savePreferences() -> Promise<void>`
- **Purpose:** Saves LLM provider, key, model, market preferences as a batch PUT to settings
- **Called by:** render (line 307)
- **Hardcodes:** `POST /api/v1/settings`, provider key/model field names
- **Flag:** 🔵 HARDCODED — field names must match backend config exactly

**Exports:**

| Export | Known importers |
|--------|----------------|
| `OnboardingWizard` | `src/App.tsx:24` |

---

### `Sidebar.tsx`

**Purpose:** Persistent left sidebar with app logo, navigation links (8 views), lead count snapshot (ready/applied/interviewing), Setup Guide button, and connection status indicator with heartbeat.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `Icon` | local | yes | 🟢 |
| `View` | local (types) | yes | 🟢 |

**Module-level constants:**

| Name | Type | Used in file | Flag |
|------|------|-------------|------|
| `NAV` | `{id, label, icon, tone}[]` | render loop | 🟢 — 8 nav items |

**Exports:**

| Export | Known importers |
|--------|----------------|
| `Sidebar` | `src/App.tsx:12` |

---

### `Topbar.tsx`

**Purpose:** Top header bar showing current view title/subtitle, plus an Export Graph button when on Profile view.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `Icon` | local | yes | 🟢 |
| `View` | local (types) | yes | 🟢 |

**Functions:**

#### `Topbar({ view })`
- **Purpose:** Title + subtitle for each view
- **Called by:** `src/App.tsx:13`
- **Flag:** 🟢

#### `StatCard({ tone, label, value, sub, icon }: any)`
- **Purpose:** Dashboard stat card with colored background, icon, value display
- **Called by:** **UNKNOWN — 0 imports found**
- **Flag:** 🟡 SUSPECT — typed `any`, no type safety, never imported anywhere in codebase. Likely dead code or intended for DashboardView but DashboardView.tsx does not import it.

**Exports:**

| Export | Known importers |
|--------|----------------|
| `Topbar` | `src/App.tsx:13` |
| `StatCard` | **none — 0 imports found** |

---

### `UpdatePrompt.tsx`

**Purpose:** Tauri update toast. Checks for updates 4.5s after mount (respecting dismissed versions via localStorage), shows download progress bar, and triggers restart on install completion.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useEffect, useMemo, useState` | stdlib | yes | 🟢 |
| `check, DownloadEvent, Update` | 3rd-party (tauri updater) | yes | 🟢 |
| `relaunch` | 3rd-party (tauri process) | yes (line 100) | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Flag |
|------|------|---------------|------|
| `UpdateState` | type alias | `"checking" \| "available" \| "downloading" \| "ready" \| "error"` | 🟢 |
| `formatBytes` | function | utility | 🟢 |

**Functions:**

#### `install() -> Promise<void>`
- **Purpose:** Downloads and installs the update, tracks progress
- **Called by:** render (line 102 onClick)
- **Side effects:** multiple state sets, file download + install via Tauri
- **Flag:** 🟢

**Exports:**

| Export | Known importers |
|--------|----------------|
| `UpdatePrompt` | `src/App.tsx:26` |

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P0 | 🔴 DEAD | `JobCard` | JobCard.tsx:7 | Never imported anywhere in codebase |
| P0 | 🔴 DEAD | `StatCard` | Topbar.tsx:44 | Never imported anywhere — typed `any`, likely leftover |
| P1 | 🔵 HARDCODED | Provider/field/hint data | OnboardingWizard.tsx:22-90 | 3 lookup tables with 16 providers each — should be fetched from backend |
| P1 | 🟡 SUSPECT | `pipelineRunning` 3s timeout | ApprovalDrawer.tsx:163 | Race condition — pipeline may finish before/after 3s |
| P2 | 🟠 RISK | 18 useState calls | ApprovalDrawer.tsx:14-30 | Cascading re-renders on every interaction; no sub-component isolation |
| P2 | 🟡 SUSPECT | `feedbackBusy` typed as `string` | ApprovalDrawer.tsx:24 | Used as surrogate per-button busy flag but could be boolean |
| P3 | 🟢 CLEAN | ErrorBoundary | ErrorBoundary.tsx | Well-structured, minimal, does exactly one thing |
| P3 | 🟢 CLEAN | Icon.tsx | Icon.tsx | Straightforward switch-based SVG library, alias handled for external/external-link |
| P3 | 🟢 CLEAN | HelpChat | HelpChat.tsx | Focused scope, clean state management |
| P3 | 🟢 CLEAN | UpdatePrompt | UpdatePrompt.tsx | Clean lifecycle, proper cleanup on unmount, dismiss persistence via localStorage |
| P3 | 🟢 CLEAN | FormReader | FormReader.tsx | Focused responsibility, clean loading/error/result states |

---

## 5. Dependencies

**Inbound (other units depend on this):**
- `src/App.tsx` — imports `Sidebar`, `Topbar`, `ErrorBoundary`, `ApprovalDrawer`, `OnboardingWizard`, `HelpChat`, `UpdatePrompt`
- `src/views/PipelineView.tsx` — imports `LeadFilterBar`, `PipelineJobCard`, `PipelineSkeleton`
- `src/views/DashboardView.tsx` — imports `Icon`
- `src/views/ApplyJobView.tsx` — imports `Icon`
- `src/views/LeadInboxView.tsx` — imports `Icon`
- `src/views/PipelineView.tsx` — imports `Icon`
- `src/views/GraphView.tsx` — imports `Icon`
- `src/views/IngestionView.tsx` — imports `Icon`
- `src/views/ProfileView.tsx` — imports `Icon`
- `src/SettingsModal.tsx` — imports `Icon`
- `src/settings/shared.tsx` — imports `Icon`

**Outbound (this unit depends on others):**
- `src/types.ts` — `ApiFetch`, `Lead`, `View`, `KeywordCoverage`, `LeadSort`, `SeniorityFilter`, `FormField`, `FormReadResult`
- `src/lib/leadUtils.ts` — `cleanLeadText`, `getTone`, `leadDisplayHeading`, `getMark`, `leadSeniority`, `seniorityLabel`, `seniorityTone`, `DEMO_JOB_DRAFT`

**External (third-party libs used):**

| Library | Used for | Flag |
|---------|----------|------|
| `react` | React, hooks | 🟢 |
| `framer-motion` | Animated mount/exit transitions (ApprovalDrawer, OnboardingWizard) | 🟢 |
| `@tauri-apps/plugin-opener` | Open URLs in system browser (ApprovalDrawer, JobCard) | 🟢 |
| `@tauri-apps/plugin-updater` | Update check/download/install (UpdatePrompt) | 🟢 |
| `@tauri-apps/plugin-process` | App relaunch after update (UpdatePrompt) | 🟢 |

---

## 6. First principles assessment

### `ApprovalDrawer.tsx`
1. **Does it need to exist?** Yes — it's the primary detail view for lead review.
2. **Does it do what it claims?** Yes — draws a modal with all lead detail sections.
3. **Is it the right place?** Partially — 642 lines is too large. PDF pane, score/feedback sections, and version selector should be extracted.
4. **What would break if deleted?** Lead detail modal would be missing from App.tsx.

### `ErrorBoundary.tsx`
1. **Does it need to exist?** Yes.
2. **Does it do what it claims?** Yes.
3. **Is it the right place?** Yes.
4. **What would break if deleted?** Uncaught render errors would crash entire app with no fallback UI.

### `FormReader.tsx`
1. **Does it need to exist?** Yes.
2. **Does it do what it claims?** Yes.
3. **Is it the right place?** Yes — embedded inside ApprovalDrawer makes sense contextually.
4. **What would break if deleted?** Form reader section in ApprovalDrawer would be missing.

### `HelpChat.tsx`
1. **Does it need to exist?** Yes.
2. **Does it do what it claims?** Yes.
3. **Is it the right place?** Yes.
4. **What would break if deleted?** Help chat widget would be removed.

### `Icon.tsx`
1. **Does it need to exist?** Yes.
2. **Does it do what it claims?** Yes — name matches purpose as SVG icon library.
3. **Is it the right place?** Yes — centralized single file for all icons.
4. **What would break if deleted?** Nearly every UI component across the app.

### `JobCard.tsx`
1. **Does it need to exist?** Yes — `PipelineJobCard` and `PipelineSkeleton` are used. But `JobCard` is dead code.
2. **Does it do what it claims?** Partially — only `PipelineJobCard` and `PipelineSkeleton` are actually consumed.
3. **Is it the right place?** Yes — co-locating related card variants is reasonable.
4. **What would break if deleted?** PipelineView would lose `PipelineJobCard` and `PipelineSkeleton`; `JobCard` removal would affect nothing.

### `LeadFilterBar.tsx`
1. **Does it need to exist?** Yes.
2. **Does it do what it claims?** Yes.
3. **Is it the right place?** Yes — pure presentational component.
4. **What would break if deleted?** PipelineView filter bar would be missing.

### `OnboardingWizard.tsx`
1. **Does it need to exist?** Yes — provides the first-run onboarding flow.
2. **Does it do what it claims?** Yes.
3. **Is it the right place?** Partially — 3 hardcoded provider lookup tables should be fetched from backend.
4. **What would break if deleted?** No first-run setup flow.

### `Sidebar.tsx`
1. **Does it need to exist?** Yes.
2. **Does it do what it claims?** Yes.
3. **Is it the right place?** Yes.
4. **What would break if deleted?** No navigation or status display.

### `Topbar.tsx`
1. **Does it need to exist?** Yes — `Topbar` is consumed. But `StatCard` is dead code.
2. **Does it do what it claims?** Yes for `Topbar`, no for `StatCard` (unused and untyped).
3. **Is it the right place?** `StatCard` co-location with `Topbar` is questionable — should be in DashboardView or a shared cards component.
4. **What would break if deleted?** `Topbar` removal breaks App.tsx header; `StatCard` removal affects nothing.

### `UpdatePrompt.tsx`
1. **Does it need to exist?** Yes.
2. **Does it do what it claims?** Yes.
3. **Is it the right place?** Yes — self-contained toast component.
4. **What would break if deleted?** No update notification UI.
