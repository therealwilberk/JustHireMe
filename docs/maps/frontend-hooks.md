# Map: frontend-hooks

**File:** `docs/maps/frontend-hooks.md`
**Codebase path(s):** `src/hooks/`
**Files in scope:** 5
**Total lines:** ~285
**Generated:** 2026-05-15

---

## 1. Unit summary

The frontend hooks layer provides React state management and side-effect orchestration for the JustHireMe desktop app. `useWS` owns the WebSocket connection lifecycle (connect, heartbeat, reconnect, Tauri sidecar bridge) and dispatches custom DOM events consumed by sibling hooks. `useLeads` maintains the canonical lead list via hybrid polling (5s background) + real-time WS events, with Tauri desktop notifications for high-scoring leads. `useDueFollowups` and `useGraphStats` are simple polling hooks with hardcoded intervals. `useKeyboardShortcuts` registers global keyboard shortcuts. All hooks are consumed exclusively by `App.tsx`, which wires the WebSocket-derived `addLog` callback into `useLeads` to correlate backend agent logs with lead state.

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `src/hooks/useWS.ts` | 133 | WebSocket lifecycle, sidecar bridge, event dispatch, log accumulator | 🟠 — complex state machine with hardcoded retry/reconnect values |
| 2 | `src/hooks/useLeads.ts` | 95 | Lead CRUD via polling + WS custom events, desktop notifications | 🟠 — dual-path state management, several hardcoded thresholds |
| 3 | `src/hooks/useDueFollowups.ts` | 17 | 60s polling for due followups | 🟡 — trivially simple, hardcoded interval and limit |
| 4 | `src/hooks/useGraphStats.ts` | 12 | 10s polling for graph statistics | 🟡 — trivially simple, hardcoded interval |
| 5 | `src/hooks/useKeyboardShortcuts.ts` | 28 | Global keyboard shortcut registration | 🟢 — clean, well-contained, configurable via params |

---

## 3. Detailed breakdown

### `src/hooks/useWS.ts`

**Purpose:** Manages the entire WebSocket lifecycle — connection, heartbeat monitoring, automatic reconnection on close/error, and Tauri sidecar orchestration (polling for port/token, listening for Tauri events). Accumulates structured log lines for the UI. Dispatches custom DOM events (`lead-updated`, `hot-x-lead`, `scan-done`, `reevaluate-done`, `cleanup-done`, `leads-refresh`, `auto_discard_done`) consumed by `useLeads` and `App.tsx`. Still needed, name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `{ useCallback, useEffect, useRef, useState }` from `react` | 3rd-party (react) | yes | 🟢 |
| `{ listen }` from `@tauri-apps/api/event` | 3rd-party (tauri) | yes | 🟢 |
| `{ invoke }` from `@tauri-apps/api/core` | 3rd-party (tauri) | yes | 🟢 |
| `type { ConnSt, Lead, LogLine }` from `../types` | local | yes | 🟢 |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `MAX_SIDECAR_RETRIES` | const | 30 | `useWS` effect (line 92) | 🔵 HARDCODED — 30s total wait baked in, not configurable |

**Functions:**

#### `useWS() -> { conn, port, apiToken, sidecarError, logs, beat, addLog }`

- **Purpose:** Root hook for WebSocket connectivity. Returns connection state, sidecar metadata, accumulated logs, and a heartbeat counter.
- **Called by:** `App.tsx:29`
- **Calls:** `addLog` (internal), `connect` (internal), `listen` (Tauri), `invoke` (Tauri)
- **Side effects:** Creates WebSocket connections, registers Tauri event listeners, sets intervals, dispatches `window` CustomEvents
- **Hardcodes:** `ws://127.0.0.1:${p}/ws?token=${token}` URL scheme (line 28), 3s reconnect delay (line 61), 150 log cap (line 21), 1000ms sidecar poll interval (line 100), heartbeat log every 10 beats (line 36)
- **Flag:** 🟡 SUSPECT — WebSocket URL path `/ws?token=` is an assumption about backend routing; if backend changes URL structure this breaks silently

#### `addLog(msg, kind, src) -> void` (local, useCallback)
- **Purpose:** Appends a structured `LogLine` to the rolling log buffer (max 150 entries). Assigns auto-incrementing IDs.
- **Called by:** `connect` handlers, effect error paths
- **Side effects:** `setLogs` state update
- **Hardcodes:** 150 entry cap
- **Flag:** 🟢 CLEAN

#### `connect(port, token) -> void` (local, useCallback)
- **Purpose:** Opens a WebSocket to the backend at `ws://127.0.0.1:${port}/ws?token=${token}`. Registers `onopen`, `onmessage`, `onclose`, `onerror` handlers. On close, auto-reconnects after 3s.
- **Called by:** effect line 86 (via `syncSidecar`), Tauri event listeners lines 105/110, `onclose` handler line 61
- **Calls:** `addLog`, `setConn`, `window.dispatchEvent`
- **Side effects:** Creates `WebSocket`, dispatches custom DOM events (`scan-done`, `reevaluate-done`, `cleanup-done`, `leads-refresh`, `auto_discard_done`, `lead-updated`, `hot-x-lead`), triggers browser Notification for hot-x-lead
- **Hardcodes:** `ws://127.0.0.1:${p}/ws?token=${encodeURIComponent(token)}` (line 28), 3s reconnect delay (line 61)
- **Flags:**
  - 🔵 HARDCODED — WebSocket URL structure (assumes `/ws` path with query token)
  - 🟡 SUSPECT — `d.uptime_seconds.toFixed(0)` (line 37) assumes field always present on heartbeat
  - 🟢 CLEAN — reconnection guard `wsRef.current?.readyState === WebSocket.OPEN` prevents duplicate connections

**Effect block (lines 65–130):**
- **Purpose:** On mount, polls Tauri sidecar for port + token (1s interval, 30 retries max), registers permanent Tauri event listeners (`sidecar-port`, `sidecar-token`, `sidecar-error`), and initiates first connection attempt.
- **Hardcodes:** `MAX_SIDECAR_RETRIES = 30`, 1000ms poll interval
- **Flag:** 🟡 SUSPECT — the `retryCount` is incremented every 1s regardless of whether `syncSidecar` actually succeeded; if Tauri is slow to respond, retries may be exhausted before sidecar is ready

**Exports:**

| Export | Known importers |
|--------|----------------|
| `useWS` | `src/App.tsx` |

---

### `src/hooks/useLeads.ts`

**Purpose:** Maintains the canonical lead list via dual-path updates: (1) initial fetch + background polling every 5 seconds, (2) real-time patching via `lead-updated` custom event (dispatched by `useWS`). Fetches event log on init. Invokes Tauri desktop notification for strong leads (score >= 80). Filters out freelance-type leads. Name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `{ useEffect, useRef, useState }` from `react` | 3rd-party (react) | yes | 🟢 |
| `{ invoke }` from `@tauri-apps/api/core` | 3rd-party (tauri) | yes | 🟢 |
| `type { ApiFetch, Lead, LogLine }` from `../types` | local | yes | 🟢 |

**Module-level constants & state:** None (all hardcodes inline)

**Functions:**

#### `useLeads(api, addLog?) -> { leads, setLeads, loading, error }`

- **Purpose:** Manages lead list state with two-phase loading, background polling, and reactive updates from WS events.
- **Called by:** `App.tsx:38`
- **Calls:** `invoke("notify_high_score_lead", ...)`, `window.addEventListener/removeEventListener`, `api()`, `setLeads`, `setLoading`, `setLoaded`, `setError`
- **Side effects:** Tauri notification invocation, custom event listeners on `window`, DOM event dispatch, fetch calls every 5s
- **Hardcodes:**
  - `5` second polling interval (line 86)
  - `200` event limit (line 76)
  - `80` score threshold for notification (line 15)
  - Freelance filter: `(l.kind || "job") !== "freelance"` (line 37)
  - `"/api/v1/leads"` endpoint (line 33)
  - `"/api/v1/events"` endpoint (line 76)
- **Flags:**
  - 🔵 HARDCODED — polling interval, event limit, score threshold, API paths
  - 🟡 SUSPECT — freelance filter is inline business logic that probably belongs in the backend or a config
  - 🟡 SUSPECT — `leads.find(l => l.job_id === sel.job_id)` in `App.tsx:44` makes `setLeads` externally accessible (returned from hook) which is a coupling risk
  - 🟢 CLEAN — `alive` flag pattern prevents state updates after unmount

#### `notifyStrongLead(lead) -> void` (local)
- **Purpose:** Invokes Tauri `notify_high_score_lead` if max(score, signal_score) >= 80.
- **Called by:** `lead-updated` event handler (line 64)
- **Side effects:** Tauri desktop notification
- **Hardcodes:** 80 threshold
- **Flag:** 🔵 HARDCODED — threshold should be configurable

**Exports:**

| Export | Known importers |
|--------|----------------|
| `useLeads` | `src/App.tsx` |

---

### `src/hooks/useDueFollowups.ts`

**Purpose:** Fetches due follow-up leads from `/api/v1/followups/due?limit=25` every 60 seconds. Returns an array of `Lead`. Minimal, straightforward. Name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `{ useEffect, useState }` from `react` | 3rd-party | yes | 🟢 |
| `type { ApiFetch, Lead }` from `../types` | local | yes | 🟢 |

**Module-level constants & state:** None

**Functions:**

#### `useDueFollowups(api) -> Lead[]`

- **Purpose:** Polling hook for due followups.
- **Called by:** `App.tsx:39`
- **Calls:** `api()`, `setLeads`
- **Side effects:** HTTP fetch every 60s, state update
- **Hardcodes:** `60000`ms interval, `25` limit, `"/api/v1/followups/due"` path
- **Flags:**
  - 🔵 HARDCODED — interval, limit, API path
  - 🟡 SUSPECT — `.catch(() => {})` silently swallows all errors (line 11)

**Exports:**

| Export | Known importers |
|--------|----------------|
| `useDueFollowups` | `src/App.tsx` |

---

### `src/hooks/useGraphStats.ts`

**Purpose:** Fetches graph entity counts from `/api/v1/graph` every 10 seconds. Returns a `GraphStats` object with zero-valued defaults. Minimal. Name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `{ useEffect, useState }` from `react` | 3rd-party | yes | 🟢 |
| `type { ApiFetch, GraphStats }` from `../types` | local | yes | 🟢 |

**Module-level constants & state:** None

**Functions:**

#### `useGraphStats(api) -> GraphStats`

- **Purpose:** Polling hook for graph stats.
- **Called by:** `App.tsx:40`
- **Calls:** `api()`, `setStats`
- **Side effects:** HTTP fetch every 10s, state update
- **Hardcodes:** `10000`ms interval, `"/api/v1/graph"` path, initial zero values `{ candidate: 0, skill: 0, project: 0, experience: 0, joblead: 0 }`
- **Flags:**
  - 🔵 HARDCODED — interval and API path
  - 🟢 CLEAN — default zero state prevents null-checking in consumers

**Exports:**

| Export | Known importers |
|--------|----------------|
| `useGraphStats` | `src/App.tsx` |

---

### `src/hooks/useKeyboardShortcuts.ts`

**Purpose:** Registers global `keydown` listeners on `window` and maps Escape, Cmd+K, Cmd+, to config callbacks. Properly cleans up on unmount via effect return. Name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `{ useEffect }` from `react` | 3rd-party | yes | 🟢 |

**Module-level constants & state:** None

**Functions:**

#### `useKeyboardShortcuts(config: { onEscape, onCmdK, onCmdComma }) -> void`

- **Purpose:** Registers keydown handler, delegates to config callbacks. Cmd+K and Cmd+, call `e.preventDefault()`.
- **Called by:** `App.tsx:80`
- **Calls:** `addEventListener("keydown", ...)`, `removeEventListener("keydown", ...)`
- **Side effects:** Window event listener lifetime managed by effect lifecycle
- **Hardcodes:** None — all callbacks passed via config
- **Flags:** 🟢 CLEAN — well-abstracted, no baked-in values, proper cleanup

**Exports:**

| Export | Known importers |
|--------|----------------|
| `useKeyboardShortcuts` | `src/App.tsx` |

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P1 | 🔵 HARDCODED | `MAX_SIDECAR_RETRIES = 30` | `useWS.ts:6` | Sidecar timeout baked in, not configurable |
| P1 | 🔵 HARDCODED | `ws://127.0.0.1:${p}/ws?token=...` | `useWS.ts:28` | WS URL structure assumes backend routing |
| P1 | 🔵 HARDCODED | 3s reconnect delay | `useWS.ts:61` | Reconnect interval not configurable |
| P1 | 🔵 HARDCODED | 5s lead polling interval | `useLeads.ts:86` | No way to tune without editing source |
| P1 | 🔵 HARDCODED | Score ≥ 80 notification threshold | `useLeads.ts:15` | Business rule baked in |
| P1 | 🔵 HARDCODED | 60s followup polling | `useDueFollowups.ts:13` | No configuration path |
| P1 | 🔵 HARDCODED | 10s graph polling | `useGraphStats.ts:9` | No configuration path |
| P1 | 🔵 HARDCODED | API endpoint paths | multiple | All hooks bake `v1` paths |
| P2 | 🟡 SUSPECT | `retryCount` ignores success/failure | `useWS.ts:98` | Increments every 1s regardless of syncSidecar result |
| P2 | 🟡 SUSPECT | `d.uptime_seconds` assumed present | `useWS.ts:37` | Heartbeat without uptime would crash |
| P2 | 🟡 SUSPECT | Freelance filter inline | `useLeads.ts:37` | Business logic in hook, should be backend or config |
| P2 | 🟡 SUSPECT | `setLeads` externally exposed | `useLeads.ts` | Returned from hook, `App.tsx` can mutate directly |
| P2 | 🟡 SUSPECT | Silent error swallow | `useDueFollowups.ts:11` | `.catch(() => {})` drops all errors |
| P3 | 🟢 CLEAN | `useKeyboardShortcuts` | `useKeyboardShortcuts.ts` | Well-abstracted, no hardcodes, proper cleanup |
| P3 | 🟢 CLEAN | `alive` flag pattern | `useLeads.ts:29` | Correct async cleanup guard |
| P3 | 🟢 CLEAN | Connection dedup guard | `useWS.ts:26` | Prevent duplicate WS connections |

---

## 5. Dependencies

**Inbound (other units depend on this):**
- `src/App.tsx` — imports all 5 hooks

**Outbound (this unit depends on others):**
- `src/types.ts` — imports `Lead`, `ApiFetch`, `LogLine`, `GraphStats`, `ConnSt`

**External (third-party libs used):**

| Library | Used for | Version pin | Flag |
|---------|----------|-------------|------|
| `react` (incl. hooks) | State management, effects, refs | `^19.1.0` | 🟢 caret acceptable |
| `@tauri-apps/api/core` | IPC to backend (invoke) | `^2.11.0` | 🟢 caret acceptable |
| `@tauri-apps/api/event` | Tauri event bridge (listen) | `^2.11.0` | 🟢 caret acceptable |

---

## 6. First principles assessment

### `src/hooks/useWS.ts`
1. **Does this file need to exist?** Yes — the WebSocket + sidecar bridge is a distinct concern requiring persistent state, retry logic, and event dispatch.
2. **Does it do what it claims?** Yes — manages WebSocket lifecycle, reconnection, heartbeat logging, and Tauri bridge.
3. **Is it the right place for this logic?** Partially — event dispatch for `lead-updated`, `hot-x-lead`, etc. bridges WS and hooks layers, but creates an implicit coupling through `window` CustomEvents that could be replaced by a shared store or context.
4. **What would break if deleted?** Everything — `useLeads` depends on `lead-updated` and `leads-refresh` events; `App.tsx` depends on `conn`, `port`, `apiToken`, `logs`; sidecar orchestration would be lost.

### `src/hooks/useLeads.ts`
1. **Does this file need to exist?** Yes — lead state is the core data model and requires polling + real-time updates.
2. **Does it do what it claims?** Yes — fetches, updates, and exposes leads with loading/error states.
3. **Is it the right place for this logic?** Partially — the freelance filter (`kind !== "freelance"`) and score notification threshold (≥80) are business rules that belong in backend or config, not a React hook.
4. **What would break if deleted?** All lead-dependent views (InboxView, PipelineView, ApplyJobView, etc.) via `App.tsx`.

### `src/hooks/useDueFollowups.ts`
1. **Does this file need to exist?** Yes — due followups is a distinct endpoint with different polling cadence than leads.
2. **Does it do what it claims?** Yes — polls and returns due followup leads.
3. **Is it the right place for this logic?** Yes — but it could share a generic polling hook given its simplicity.
4. **What would break if deleted?** The followup indicator in the UI (consumed by `App.tsx`).

### `src/hooks/useGraphStats.ts`
1. **Does this file need to exist?** Yes — graph statistics is a distinct visualization concern.
2. **Does it do what it claims?** Yes — polls and returns graph entity counts.
3. **Is it the right place for this logic?** Yes — but arguably could be in a generic polling utility given near-identical pattern to `useDueFollowups`.
4. **What would break if deleted?** GraphView stats display (via `App.tsx`).

### `src/hooks/useKeyboardShortcuts.ts`
1. **Does this file need to exist?** Yes — keyboard shortcuts are a self-contained concern with specific cleanup requirements.
2. **Does it do what it claims?** Yes — registers and unregisters global keyboard handlers.
3. **Is it the right place for this logic?** Yes — properly abstracted from presentation.
4. **What would break if deleted?** Escape-to-close-drawer, Cmd+K-to-apply, and Cmd+, -to-settings shortcuts.
