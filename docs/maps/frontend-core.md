# Map: frontend-core
**File:** `docs/maps/frontend-core.md`
**Codebase path(s):** `src/App.tsx`, `src/main.tsx`, `src/types.ts`, `src/SettingsModal.tsx`, `src/index.css`
**Files in scope:** 5
**Total lines:** ~3313
**Generated:** 2026-05-15

---

## 1. Unit summary

The frontend-core unit is the application shell. It owns the React entry point (`main.tsx`), the root `App` component that wires together every view, all shared TypeScript types (`types.ts`), the settings modal (`SettingsModal.tsx`), and the entire design system (`index.css`). It depends on every view, component, and hook module. Every frontend unit depends on `types.ts` for its type definitions.

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `src/App.tsx` | 320 | Root component — state orchestration, conditional view rendering, modals, keyboard shortcuts | 🟢 |
| 2 | `src/main.tsx` | 34 | React entry point — mounts `<App />` into DOM with fatal-error fallback | 🟢 |
| 3 | `src/types.ts` | 84 | Shared TypeScript type definitions used across all frontend modules | 🟢 |
| 4 | `src/SettingsModal.tsx` | 85 | Settings modal dialog — fetch/save config, sub-panel composition | 🟢 |
| 5 | `src/index.css` | 2790 | Global styles — Tailwind import, design tokens, component classes, responsive breakpoints | 🟢 |

---

## 3. Detailed breakdown

### `src/App.tsx`

**Purpose:** Root React component. It initializes the WebSocket connection, creates the `ApiFetch` helper, fetches leads/followups/stats, manages 15+ pieces of UI state, conditionally renders 8 views inside `ErrorBoundary` wrappers, and hosts the modal drawer (`ApprovalDrawer`, `SettingsModal`, `OnboardingWizard`), help chat, and update prompt.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useCallback, useEffect, useMemo, useState` | stdlib (react) | yes | 🟢 |
| `AnimatePresence` | 3rd-party (framer-motion) | yes — wraps modals/drawer | 🟢 |
| `SettingsModal` | local | yes — line 213 | 🟢 |
| `./index.css` | local (side-effect) | yes | 🟢 |
| `ApiFetch, Lead, View` | local (./types) | yes | 🟢 |
| `ONBOARDING_KEY` | local (./lib/leadUtils) | yes — lines 46, 61, 221 | 🟢 |
| `useWS` | local (./hooks/useWS) | yes | 🟢 |
| `useLeads` | local (./hooks/useLeads) | yes | 🟢 |
| `useDueFollowups` | local (./hooks/useDueFollowups) | yes | 🟢 |
| `useGraphStats` | local (./hooks/useGraphStats) | yes | 🟢 |
| `useKeyboardShortcuts` | local (./hooks/useKeyboardShortcuts) | yes | 🟢 |
| `Sidebar` | local (./components/Sidebar) | yes | 🟢 |
| `Topbar` | local (./components/Topbar) | yes | 🟢 |
| `ErrorBoundary` | local (./components/ErrorBoundary) | yes — wraps every view | 🟢 |
| `DashboardView, LeadInboxView, ApplyJobView, PipelineView, GraphView, ActivityView, ProfileView, IngestionView` | local (./views/) | yes | 🟢 |
| `ApprovalDrawer` | local (./components/ApprovalDrawer) | yes | 🟢 |
| `OnboardingWizard` | local (./components/OnboardingWizard) | yes | 🟢 |
| `HelpChat` | local (./components/HelpChat) | yes | 🟢 |
| `UpdatePrompt` | local (./components/UpdatePrompt) | yes | 🟢 |

**Module-level constants & state:** None. All state is component-local.

**Functions:**

#### `App() -> JSX.Element`
- **Purpose:** Root component — state management hub and view router
- **Called by:** `main.tsx` `<React.StrictMode><App /></React.StrictMode>`
- **Calls:** `useWS`, `useLeads`, `useDueFollowups`, `useGraphStats`, `useKeyboardShortcuts`, `useMemo` (ApiFetch), `useCallback` (closeDrawer, focusApplyView, openSettings, openSetupGuide, onScan, onStopScan, onReevaluateJobs, onStopReevaluate, onCleanupLeads, deleteLead)
- **Side effects:** Event listeners (`scan-done`, `reevaluate-done`, `cleanup-done`), startup timer interval, keyboard shortcut registration
- **Hardcodes:** `"http://127.0.0.1:${port}"` (line 35), lead status string literals (lines 177-185), event names (`"scan-done"`, `"reevaluate-done"`, `"cleanup-done"`, `"leads-refresh"`)
- **Flag:** 🟢

#### `StartupScreen({ conn, port, seconds, sidecarError }) -> JSX.Element`
- **Purpose:** Renders a waiting screen while the backend sidecar is starting up. Shows connection state, elapsed time, and error details.
- **Called by:** `App()` line 188
- **Calls:** none
- **Side effects:** none (stateless presentational)
- **Hardcodes:** threshold `>= 20` for "slow" warning (line 236), macOS-specific instruction string (line 274)
- **Flag:** 🟡 SUSPECT — macOS-specific copy in cross-platform app; consider platform detection

#### `BackendUnavailable({ title, conn, port }) -> JSX.Element`
- **Purpose:** Shown when a specific view is selected but backend isn't ready yet
- **Called by:** `App()` lines 203-204
- **Calls:** none
- **Side effects:** none
- **Flag:** 🟢

**Exports:**

| Export | Known importers |
|--------|----------------|
| `App` (default) | `main.tsx` (line 3) |

**State management breakdown (15 `useState` calls):**

| # | State | Type | Init | Purpose | Flag |
|---|-------|------|------|---------|------|
| 1 | `view` | `View` | `"dashboard"` | Current active view | 🟢 |
| 2 | `sel` | `Lead \| null` | `null` | Selected lead for drawer | 🟢 |
| 3 | `showSettings` | `boolean` | `false` | Settings modal visibility | 🟢 |
| 4 | `showOnboarding` | `boolean` | `localStorage` check | Onboarding wizard visibility | 🟢 |
| 5 | `applyDraft` | `string` | `""` | Draft text pre-filled into Apply view | 🟢 |
| 6 | `applyAutoFocus` | `boolean` | `false` | Auto-focus flag for Apply input | 🟢 |
| 7 | `scanning` | `boolean` | `false` | Scan in progress | 🟢 |
| 8 | `reevaluating` | `boolean` | `false` | Re-evaluation in progress | 🟢 |
| 9 | `cleaning` | `boolean` | `false` | Cleanup in progress | 🟢 |
| 10 | `scanErr` | `string \| null` | `null` | Scan/reeval/cleanup error message | 🟢 |
| 11 | `startupSeconds` | `number` | `0` | Elapsed seconds since mount (no api) | 🟢 |

Plus derived: `liveSel`, `leadCounts`, `api` (useMemo), plus state from hooks (`leads`, `dueFollowups`, `stats`, `conn`, `port`, `apiToken`, `sidecarError`, `logs`, `beat`, `wsAddLog`).

---

### `src/main.tsx`

**Purpose:** Application entry point. Renders `<App />` into the DOM via `ReactDOM.createRoot`. Catches synchronous render errors and displays a styled fallback via `renderFatalStartupError`.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `React` | stdlib | yes — `React.StrictMode` | 🟢 |
| `ReactDOM` | 3rd-party | yes — `createRoot` | 🟢 |
| `App` | local | yes | 🟢 |
| `./index.css` | local (side-effect) | yes | 🟢 |

**Module-level constants & state:** None.

**Functions:**

#### `renderFatalStartupError(error: unknown) -> void`
- **Purpose:** Handles catastrophic render failures by replacing the DOM root with a styled error card containing the error message (HTML-escaped)
- **Called by:** `catch` block at module level (line 33)
- **Calls:** none
- **Side effects:** Direct DOM mutation (`root.innerHTML = ...`)
- **Hardcodes:** Inline styles for error card (lines 12-20), HTML entity mapping (line 17)
- **Flag:** 🟢 — intentional: this runs before any CSS is loaded

**Exports:** None (entry point, no exports).

---

### `src/types.ts`

**Purpose:** Single source of truth for all shared TypeScript types used across frontend modules. No business logic, no imports.

**Imports:** None.

**Module-level constants & state:** None.

**Type/Interface definitions:**

| Name | Kind | Used by (in this unit) | Flag |
|------|------|------------------------|------|
| `ConnSt` | union type | only `useWS` hook — not used in this unit | 🟢 — defined here for central access |
| `View` | union type | `App.tsx:41` | 🟢 |
| `PipelineTab` | union type | not in this unit | 🟢 — used by PipelineView |
| `LeadSort` | union type | not in this unit | 🟢 — used by PipelineView |
| `SeniorityFilter` | union type | not in this unit | 🟢 — used by PipelineView |
| `KeywordCoverage` | interface | `Lead` interface | 🟢 |
| `ContactLookup` | interface | `Lead` interface | 🟢 |
| `Lead` | interface | `App.tsx:42-56`, `liveSel` | 🟢 |
| `GraphStats` | interface | `App.tsx:40` | 🟢 |
| `LogLine` | interface | not in App.tsx (used by ActivityView) | 🟢 |
| `ApiFetch` | type alias | `App.tsx:30` | 🟢 |
| `FormField` | interface | via FormReadResult | 🟢 — used by ApplyJobView |
| `FormReadResult` | interface | not in this unit | 🟢 — used by ApplyJobView |

**Exports:** All named exports — used across every frontend unit.

---

### `src/SettingsModal.tsx`

**Purpose:** Settings modal dialog. Fetches current config from `/api/v1/settings` on mount, allows editing via composed sub-panels (`GlobalSettings`, `StepSettings`, `DiscoverySettings`, `AutomationSettings`), and saves via POST. Manages save/saved/saveError state.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useEffect, useState` | stdlib (react) | yes | 🟢 |
| `Icon` | local (./components/Icon) | yes — line 64 | 🟢 |
| `AutomationSettings` | local | yes | 🟢 |
| `DiscoverySettings` | local | yes | 🟢 |
| `GlobalSettings` | local | yes | 🟢 |
| `StepSettings` | local | yes | 🟢 |
| `EMPTY, type Cfg` | local (./settings/shared) | yes | 🟢 |
| `ApiFetch` | local (./types) | yes — `Props` interface | 🟢 |

**Module-level constants & state:** None.

**Functions:**

#### `SettingsModal({ api, onClose }) -> JSX.Element`
- **Purpose:** Renders the settings modal with composed sub-panels and save/cancel actions
- **Called by:** `App.tsx:213`
- **Calls:** `api("/api/v1/settings")` (GET), `save`, `set`, `onChange`
- **Side effects:** On save, requests notification permission if `x_enable_notifications === "true"` (line 43-45)
- **Hardcodes:** `"/api/v1/settings"` endpoint (lines 19, 36), `"ollama"` default provider (line 52)
- **Flag:** 🟢

**Internal helpers:**

| Name | Type | Purpose | Flag |
|------|------|---------|------|
| `set(k: keyof Cfg)` | closure | Returns change-event handler that updates a single key | 🟢 |
| `onChange(k, v)` | function | Direct key/value setter (for non-event-driven components) | 🟢 |
| `save()` | async function | POSTs config, sets save/saved/saveError states | 🟢 |
| `prov` | derived | `cfg.llm_provider \|\| "ollama"` — passed to sub-panels | 🟢 |

**State:**

| State | Type | Init | Purpose |
|-------|------|------|---------|
| `cfg` | `Cfg` | `EMPTY` | Current configuration values |
| `saving` | `boolean` | `false` | Save in progress |
| `saved` | `boolean` | `false` | Transient "saved" confirmation (clears after 2s) |
| `saveError` | `string \| null` | `null` | Error message from last save attempt |

**Error handling:** Errors from GET fetch are silently caught (line 22 `.catch(() => {})`). Errors from POST are caught and stored in `saveError` (line 48), displayed in the footer bar (line 76). The save button is disabled while `saving` (line 78).

**Flag:** 🟡 SUSPECT — GET fetch errors are silently swallowed; `set` function uses `React.ChangeEvent<...>` typing which may be too narrow (line 26); `cfg` is spread as `{ ...c, ...d }` which could lose keys if API returns a subset.

---

### `src/index.css`

**Purpose:** Global stylesheet. Contains all design tokens (CSS custom properties), layout utilities, component styles (sidebar, buttons, cards, pipeline, profile, graph, ingestion, help chat, toggles, animations, spinners, update toast), and responsive breakpoints. Tailwind CSS is imported at line 1.

**Organization (by section):**
1. Design tokens (`@theme`) — lines 6-71
2. Base/reset — lines 76-145
3. Layout utilities — lines 151-179
4. App shell (`.app-main`, `.sidebar`, `.topbar`) — lines 185-214
5. Navigation — lines 220-252
6. Cards — lines 258-269
7. Buttons — lines 275-345
8. Pipeline UI — lines 347-1115
9. Typography — lines 1121-1151
10. Pills, dots, status — lines 1157-1195
11. Lift/hover — lines 1201-1208
12. Terminal — lines 1214-1224
13. Form fields — lines 1230-1270
14. Ingestion / Add Context — lines 1273-1499
15. Toggle switches — lines 1503-1538
16. Graph / Profile pages — lines 1544-2616
17. Drawer / modal overlay — lines 2622-2665
18. Save/success state — lines 2671-2675
19. App layout — lines 2681-2686
20. Animations / Spinners — lines 2692-2714
21. Update toast — lines 2716-2790

**Imports:**
| Import | Type | Used | Flag |
|--------|------|------|------|
| `tailwindcss` | 3rd-party (CSS) | yes — utility classes | 🟢 |

**Flag:** 🟢 — Well-organized, consistent token system, responsive breakpoints at 1180px, 980px, 920px, 900px, 860px, 760px, 680px, 640px, 560px. Some duplicated selectors (`.profile-page` declared twice at lines 1546 and 2143; `.profile-map-node` at lines 1948 and 2306; `.profile-main-panel` at lines 1890 and 2261; `.profile-shell-compact` at lines 1863 and 2155; `.profile-workspace` at lines 1869 and 2159 — later declarations override earlier ones). This appears to be intentional polish/refinement rather than accidental duplication.

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P2 | 🟡 SUSPECT | macOS-specific copy | `App.tsx:274` | "On macOS, use Privacy & Security..." — platform-specific instruction in cross-platform app |
| P2 | 🟡 SUSPECT | GET errors silently swallowed | `SettingsModal.tsx:22` | `.catch(() => {})` on settings fetch — user sees no feedback if load fails |
| P3 | 🟡 SUSPECT | Narrow event typing | `SettingsModal.tsx:26` | `set` typed for `ChangeEvent<HTMLInputElement \| HTMLTextAreaElement>` — will not work for select/button elements, but `onChange` is the alternative path |
| P3 | 🟢 CLEAN | Duplicate CSS selectors | `index.css:1546+2143` | Later declarations override earlier ones (profile-page, profile-map-node, etc.) — appears to be intentional polish pass |
| P3 | 🟢 CLEAN | All types exported | `types.ts` | Every type/interface is exported; no dead or internal-only types |
| P3 | 🟢 CLEAN | useMemo for ApiFetch | `App.tsx:30-37` | Properly memoized on `[port, apiToken]` |

---

## 5. Dependencies

**Inbound (other units depend on this):**
- Every view module depends on `types.ts` (all TypeScript interfaces/types)
- `App.tsx` imports every view, component, and hook module

**Outbound (this unit depends on others):**

| Dependency | Imported by | From |
|------------|-------------|------|
| `./hooks/useWS` | App.tsx | backend-core (hooks) |
| `./hooks/useLeads` | App.tsx | backend-core (hooks) |
| `./hooks/useDueFollowups` | App.tsx | backend-core (hooks) |
| `./hooks/useGraphStats` | App.tsx | backend-core (hooks) |
| `./hooks/useKeyboardShortcuts` | App.tsx | frontend-utils |
| `./components/Sidebar` | App.tsx | frontend-components |
| `./components/Topbar` | App.tsx | frontend-components |
| `./components/ErrorBoundary` | App.tsx | frontend-components |
| `./components/ApprovalDrawer` | App.tsx | frontend-components |
| `./components/OnboardingWizard` | App.tsx | frontend-components |
| `./components/HelpChat` | App.tsx | frontend-components |
| `./components/UpdatePrompt` | App.tsx | frontend-components |
| `./components/Icon` | SettingsModal.tsx | frontend-components |
| `./settings/GlobalSettings` | SettingsModal.tsx | frontend-settings |
| `./settings/StepSettings` | SettingsModal.tsx | frontend-settings |
| `./settings/DiscoverySettings` | SettingsModal.tsx | frontend-settings |
| `./settings/AutomationSettings` | SettingsModal.tsx | frontend-settings |
| `./settings/shared` | SettingsModal.tsx | frontend-settings |
| `./views/DashboardView` | App.tsx | frontend-views |
| `./views/LeadInboxView` | App.tsx | frontend-views |
| `./views/ApplyJobView` | App.tsx | frontend-views |
| `./views/PipelineView` | App.tsx | frontend-views |
| `./views/GraphView` | App.tsx | frontend-views |
| `./views/ActivityView` | App.tsx | frontend-views |
| `./views/ProfileView` | App.tsx | frontend-views |
| `./views/IngestionView` | App.tsx | frontend-views |
| `./lib/leadUtils` | App.tsx | frontend-lib |
| `./types` | App.tsx, SettingsModal.tsx | self (this unit) |

**External (third-party libs used):**

| Library | Used by | Used for | Version pin? | Flag |
|---------|---------|----------|-------------|------|
| `react` | main.tsx, App.tsx, SettingsModal.tsx | Component framework | via package.json | 🟢 |
| `react-dom` | main.tsx | DOM rendering | via package.json | 🟢 |
| `framer-motion` | App.tsx | `AnimatePresence` for modal transitions | via package.json | 🟢 |
| `tailwindcss` | index.css | CSS utility classes | via package.json | 🟢 |

---

## 6. First principles assessment

### `src/App.tsx`
1. **Does this file need to exist?** Yes — root component is the single entry point for the app.
2. **Does it do what it claims?** Yes — `App` component manages app state and renders views.
3. **Is it the right place for this logic?** Partially — the 8 action callbacks (`onScan`, `onStopScan`, etc.) are tightly coupled to App.tsx; some could be extracted to a custom hook, but the current pattern is acceptable for a single-page desktop app.
4. **What would break if deleted?** The entire app — no other module creates the React root or owns the state hub.

### `src/main.tsx`
1. **Does this file need to exist?** Yes — standard React entry point.
2. **Does it do what it claims?** Yes — mounts the app.
3. **Is it the right place for this logic?** Yes.
4. **What would break if deleted?** Nothing would render — no DOM mount point.

### `src/types.ts`
1. **Does this file need to exist?** Yes — central type definitions avoid circular imports and duplication.
2. **Does it do what it claims?** Yes — provides all shared types.
3. **Is it the right place for this logic?** Yes.
4. **What would break if deleted?** Every frontend file that imports from `./types` — compilation would fail everywhere.

### `src/SettingsModal.tsx`
1. **Does this file need to exist?** Yes — settings UI is a distinct modal component.
2. **Does it do what it claims?** Yes — fetches, displays, and saves settings.
3. **Is it the right place for this logic?** Yes.
4. **What would break if deleted?** Settings modal would not appear; `App.tsx` line 213 would fail.

### `src/index.css`
1. **Does this file need to exist?** Yes — all visual styling.
2. **Does it do what it claims?** Yes — provides global styles and design tokens.
3. **Is it the right place for this logic?** Yes — single stylesheet is appropriate for this scale; CSS custom properties provide theme consistency.
4. **What would break if deleted?** Entire app would be unstyled (no layout, no colors, no component styling).
