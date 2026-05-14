# Map: frontend-settings
**File:** `docs/maps/frontend-settings.md`
**Codebase path(s):** `src/settings/`
**Files in scope:** 5
**Total lines:** ~835
**Generated:** 2026-05-15

---

## 1. Unit summary

The `src/settings/` directory is the frontend settings layer — the UI counterpart to `backend/config/`. It owns the `Cfg` interface (77 keys, all strings — no typed value constraints), the `EMPTY` default configuration, the `PROVIDERS`/`MODEL_HINTS`/`STEPS` static data tables, and four React component files that render the settings modal sections. It depends on `src/components/Icon` and `src/types` (for `ApiFetch`). It is consumed exclusively by `src/SettingsModal.tsx`. The unit is structurally clean but has significant hardcoding, validation gaps, and India-market embedded references that the `docs/deferred/india-references-cleanup.md` tracks as deferred.

---

## 2. File inventory

| # | File | Lines | Purpose | Overall flag |
|---|------|-------|---------|-------------|
| 1 | `shared.tsx` | 364 | `Cfg` interface + `EMPTY` defaults + `PROVIDERS`/`MODEL_HINTS`/`STEPS` static data + UI helper components | 🟠 HARDCODED — provider lists, source presets, model hints all baked in |
| 2 | `DiscoverySettings.tsx` | 329 | Job discovery UI: Apify, LinkedIn, X signals, free sources, custom connectors, job board management with market focus toggle | 🟠 STALE — India market hardcoding, duplicated preset definitions |
| 3 | `GlobalSettings.tsx` | 102 | Global LLM provider selection, API key input, model selection, key validation UI | 🟢 CLEAN |
| 4 | `StepSettings.tsx` | 16 | Thin wrapper rendering `StepCard` for each `STEPS` entry | 🟢 CLEAN |
| 5 | `AutomationSettings.tsx` | 24 | Three experimental automation toggles (ghost mode, auto apply, headed browser) | 🟢 CLEAN |

---

## 3. Detailed breakdown

### `shared.tsx`

**Purpose:** Central data & component hub. Defines the `Cfg` interface (77 string keys — the frontend's config schema), `EMPTY` defaults, `PROVIDERS` (17 LLM providers), `MODEL_HINTS` (per-provider model suggestions), `STEPS` (5 workflow stages), `GLOBAL_SOURCE_PRESET` (18 lines) and `INDIA_SOURCE_PRESET` (13 lines) of hardcoded job sources, `KEY_FIELD`/`GLOBAL_MODEL_FIELD` provider-to-config-key maps, and 7 UI helper components. Name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useState` from `react` | 3rd-party | yes — `StepCard` | 🟢 CLEAN |
| `Icon` from `../components/Icon` | local | yes — `StepCard`, `BigToggle` | 🟢 CLEAN |

**Module-level constants & state:**

| Name | Type | Value/Default | Used by | Flag |
|------|------|---------------|---------|------|
| `Cfg` | interface | 77 string keys | all 4 settings components + `SettingsModal` | 🟠 INCOMPLETE — all values are `string`, no boolean/number types despite numeric semantics (`x_max_requests_per_scan`, etc.) |
| `EMPTY` | `Cfg` | defaults mix of `""`, `"false"`, and provider-specific model names | `SettingsModal.tsx:13` | 🟠 SUSPECT — defaults like `"z-ai/glm-5.1"` (nvidia_model) and `"openai/gpt-oss-120b"` (huggingface_model) look like copy-paste artifacts |
| `PROVIDERS` | `Array` | 17 entries with id/label/tone/sub | `ProviderPills`, UI rendering | 🔵 HARDCODED — no way to add/remove providers without code change |
| `MODEL_HINTS` | `Record<string, string[]>` | 17 entries, 2–5 model strings each | `ModelChips` | 🔵 HARDCODED — model names go stale as providers release new models |
| `STEPS` | `Array` | 5 entries: scout, evaluator, generator, ingestor, actuator | `StepCard`, `StepSettings` | 🟢 CLEAN |
| `GLOBAL_SOURCE_PRESET` | string | 18 job source URLs/lines joined by newline | `DiscoverySettings` (quick-add "Global preset") | 🔵 HARDCODED — relates to `chore/externalize-job-targets` plan |
| `INDIA_SOURCE_PRESET` | string | 13 India-specific job source lines | `DiscoverySettings` (quick-add "India preset") | 🔵 HARDCODED — tracked in `docs/deferred/india-references-cleanup.md` |
| `KEY_FIELD` | `Record<string, keyof Cfg>` | maps 16 provider IDs to API key fields (excludes ollama) | `GlobalSettings`, `ApiKeyInput` | 🟢 CLEAN |
| `GLOBAL_MODEL_FIELD` | `Record<string, keyof Cfg>` | maps 16 provider IDs to model fields (excludes ollama) | `GlobalSettings`, `ModelChips` | 🟢 CLEAN |

**Functions & components:**

#### `LabelledField({ label, hint, children }) -> JSX`
- **Purpose:** Layout wrapper for a labeled form field with optional hint
- **Called by:** `DiscoverySettings`, `GlobalSettings`
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

#### `SectionLabel({ label, sub }) -> JSX`
- **Purpose:** Section heading with optional mono sub-label
- **Called by:** `GlobalSettings`, `StepSettings`, `DiscoverySettings`, `AutomationSettings`
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

#### `ProviderPills({ value, onChange, small }) -> JSX`
- **Purpose:** Row of button pills for LLM provider selection; iterates `PROVIDERS`
- **Called by:** `GlobalSettings`, `StepCard`
- **Calls:** none (renders `PROVIDERS` directly)
- **Side effects:** none
- **Hardcodes:** references `PROVIDERS`, ties UI to module-level constant
- **Flag:** 🟢 CLEAN (but coupled to hardcoded `PROVIDERS`)

#### `ModelChips({ provider, value, onChange }) -> JSX`
- **Purpose:** Clickable model-name chips + manual text input for model selection
- **Called by:** `GlobalSettings`, `StepCard`
- **Calls:** none (renders `MODEL_HINTS` directly)
- **Side effects:** none
- **Hardcodes:** reads from `MODEL_HINTS[provider]`
- **Flag:** 🟢 CLEAN (but coupled to hardcoded `MODEL_HINTS`)

#### `ApiKeyInput({ value, onChange, provider, isStep, disabled, placeholder }) -> JSX | null`
- **Purpose:** Password input for API keys; returns null for ollama; has per-provider placeholder hints
- **Called by:** `GlobalSettings`, `StepCard`
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** per-provider placeholder hints map (line 250-255)
- **Flag:** 🟡 SUSPECT — placeholder hints repeated in component, partially overlap with provider metadata

#### `StepCard({ step, cfg, onChange }) -> JSX`
- **Purpose:** Card UI for configuring a single pipeline step's provider, API key, and model; supports global-vs-custom toggle
- **Called by:** `StepSettings`
- **Calls:** `ProviderPills`, `ApiKeyInput`, `ModelChips`
- **Side effects:** none (except local `useState` for `forceStepKey`)
- **Hardcodes:** none (reads from `cfg`, `step`, `PROVIDERS`)
- **Flag:** 🟢 CLEAN

#### `BigToggle({ active, onToggle, icon, label, badge, sub, tone }) -> JSX`
- **Purpose:** Large card-style toggle with icon, label, badge, subtext, and tone color
- **Called by:** `DiscoverySettings`, `AutomationSettings`
- **Calls:** none (renders `Icon`)
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

**Exports:**

| Export | Known importers |
|--------|----------------|
| `Cfg` (interface) | `SettingsModal`, `GlobalSettings`, `StepSettings`, `DiscoverySettings`, `AutomationSettings` |
| `EMPTY` | `SettingsModal` |
| `PROVIDERS` | `ProviderPills` (same file), external consumers of `shared.tsx` — none found beyond this unit |
| `MODEL_HINTS` | `ModelChips` (same file) |
| `STEPS` | `StepSettings` |
| `GLOBAL_SOURCE_PRESET` | `DiscoverySettings` |
| `INDIA_SOURCE_PRESET` | `DiscoverySettings` |
| `KEY_FIELD` | `GlobalSettings` |
| `GLOBAL_MODEL_FIELD` | `GlobalSettings` |
| `LabelledField` | `DiscoverySettings`, `GlobalSettings` |
| `SectionLabel` | `GlobalSettings`, `StepSettings`, `DiscoverySettings`, `AutomationSettings` |
| `ProviderPills` | `GlobalSettings`, `StepCard` (same file) |
| `ModelChips` | `GlobalSettings`, `StepCard` (same file) |
| `ApiKeyInput` | `GlobalSettings`, `StepCard` (same file) |
| `StepCard` | `StepSettings` |
| `BigToggle` | `DiscoverySettings`, `AutomationSettings` |

---

### `DiscoverySettings.tsx`

**Purpose:** Full job discovery configuration form — Apify/LinkedIn credentials, X/Twitter signal settings, free source stack (GitHub/HN/Reddit/ATS), custom JSON connectors, and the job board textarea with quick-add presets. Largest file in the unit. Name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useState` + `type ChangeEvent` from `react` | 3rd-party | yes | 🟢 CLEAN |
| `type Cfg` from `./shared` | local | yes | 🟢 CLEAN |
| `BigToggle`, `GLOBAL_SOURCE_PRESET`, `INDIA_SOURCE_PRESET`, `LabelledField`, `SectionLabel` from `./shared` | local | yes | 🟢 CLEAN |

**Functions:**

#### `sourceTargetFromSite(raw: string) -> string`
- **Purpose:** Transforms a user-entered domain/site into a search query string; detects ATS/preset prefixes and raw URLs vs plain domains
- **Called by:** `addSiteSource` (same file), preview div (line 253)
- **Calls:** none
- **Side effects:** none
- **Hardcodes:** line 19: appends `("jobs" OR "careers" OR "hiring" OR "open roles") (remote OR hybrid OR onsite OR India OR global)` to generic domains — the `India` reference is a hardcoded India market term
- **Flag:** 🟡 SUSPECT — the India/global clause is a location qualifier applied unconditionally to plain domains

#### `addSiteSource() -> void`
- **Purpose:** Takes `siteDraft`, transforms via `sourceTargetFromSite`, appends to `job_boards` if not duplicate
- **Called by:** "Add source" button and Enter key handler
- **Calls:** `sourceTargetFromSite`
- **Side effects:** modifies `cfg.job_boards` via `onChange`, clears `siteDraft`
- **Hardcodes:** none (delegates to `sourceTargetFromSite`)
- **Flag:** 🟢 CLEAN

#### `DiscoverySettings({ cfg, set, onChange }) -> JSX`
- **Purpose:** Main component — renders all discovery UI sections
- **Called by:** `SettingsModal`
- **Calls:** `BigToggle`, `LabelledField`, `SectionLabel`, `addSiteSource`
- **Side effects:** none
- **Hardcodes:** Notable hardcoded data within the render:
  - Quick-add source buttons (lines 259-279) — 20 button definitions including India-specific ones (Naukri, Instahyre, Cutshort, Foundit, Internshalla) — 🔵 HARDCODED
  - Market focus buttons (lines 214-231): "Global market" vs "India market" — 🔵 HARDCODED — relates to `docs/deferred/india-references-cleanup.md`
  - X search query placeholders (lines 81-85) — mention `India`
  - placeholder lists reference India multiple times
- **Flag:** 🟠 STALE — India market references should be externalized or made configurable

---

### `GlobalSettings.tsx`

**Purpose:** Global LLM provider selection and key validation. User picks a default provider, enters its API key (or Ollama URL), selects a model, and can run key validation against `/api/v1/settings/validate`. Name matches content.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `useEffect`, `useState` from `react` | 3rd-party | yes | 🟢 CLEAN |
| `type Cfg` from `./shared` | local | yes | 🟢 CLEAN |
| `ApiKeyInput`, `GLOBAL_MODEL_FIELD`, `KEY_FIELD`, `ModelChips`, `ProviderPills`, `SectionLabel` from `./shared` | local | yes | 🟢 CLEAN |
| `type ApiFetch` from `../types` | local | yes | 🟢 CLEAN |

**Functions:**

#### `GlobalSettings({ cfg, set, onChange, prov, api }) -> JSX`
- **Purpose:** Main component — renders provider pills, API key/Ollama URL input, model chips, key-check button with status badges
- **Called by:** `SettingsModal`
- **Calls:** `ProviderPills`, `ApiKeyInput`, `ModelChips`, `SectionLabel`
- **Side effects:** calls `api("/api/v1/settings/validate")` on key check; sets auto-clearing results/error state with 30s timer (line 14-20)
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

#### `checkKeys() -> Promise<void>` (closure in component)
- **Purpose:** POST to `/api/v1/settings/validate`, parse JSON validation results, display per-provider status badges
- **Called by:** "Check keys" button
- **Calls:** `api()` fetch
- **Side effects:** sets `results` or `err` state; 30s auto-clear via `useEffect`
- **Hardcodes:** API path `/api/v1/settings/validate`
- **Flag:** 🟢 CLEAN

---

### `StepSettings.tsx`

**Purpose:** Thin component that renders a `StepCard` for each step in the pipeline. 16 lines — essentially a loop over `STEPS`.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `type Cfg` from `./shared` | local | yes | 🟢 CLEAN |
| `SectionLabel`, `STEPS`, `StepCard` from `./shared` | local | yes | 🟢 CLEAN |

**Functions:**

#### `StepSettings({ cfg, onChange }) -> JSX`
- **Purpose:** Maps `STEPS` array to `StepCard` components
- **Called by:** `SettingsModal`
- **Calls:** `StepCard` for each step
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN — minimal delegation, justified as its own file for semantic clarity

---

### `AutomationSettings.tsx`

**Purpose:** Three toggles for experimental browser automation features. All marked as "unsupported lab" in UI copy.

**Imports:**

| Import | Type | Used in file | Flag |
|--------|------|-------------|------|
| `type Cfg` from `./shared` | local | yes | 🟢 CLEAN |
| `BigToggle`, `SectionLabel` from `./shared` | local | yes | 🟢 CLEAN |

**Functions:**

#### `AutomationSettings({ cfg, onChange }) -> JSX`
- **Purpose:** Renders ghost mode, auto apply, and headed browser toggles
- **Called by:** `SettingsModal`
- **Calls:** `BigToggle` (3 times)
- **Side effects:** none
- **Hardcodes:** none
- **Flag:** 🟢 CLEAN

---

## 4. Flags summary

| Priority | Flag | Item | File:Line | Reason |
|----------|------|------|-----------|--------|
| P1 | 🔵 HARDCODED | `PROVIDERS` array | `shared.tsx:54` | 17 LLM provider definitions baked into source — no plugin/config mechanism |
| P1 | 🔵 HARDCODED | `MODEL_HINTS` record | `shared.tsx:74` | Per-provider model lists baked in — will go stale |
| P1 | 🔵 HARDCODED | `GLOBAL_SOURCE_PRESET` | `shared.tsx:107` | 18 job source lines embedded — tracked by `chore/externalize-job-targets` |
| P1 | 🔵 HARDCODED | `INDIA_SOURCE_PRESET` | `shared.tsx:129` | 13 India-specific job source lines — tracked by `docs/deferred/india-references-cleanup.md` |
| P1 | 🔵 HARDCODED | India market quick-add buttons | `DiscoverySettings.tsx:259-279` | "Naukri", "Instahyre", "Cutshort", "Foundit", "Internshala" buttons embedded |
| P1 | 🔵 HARDCODED | Market focus buttons | `DiscoverySettings.tsx:214-231` | "Global market" vs "India market" hardcoded as the only two options |
| P1 | 🔵 HARDCODED | `sourceTargetFromSite` India clause | `DiscoverySettings.tsx:19` | Appends `India OR global` unconditionally to plain-domain queries |
| P2 | 🟠 INCOMPLETE | `Cfg` all-string typing | `shared.tsx:4` | 77 keys all typed `string` — numeric fields (`x_max_requests_per_scan`, score thresholds) and booleans (`ghost_mode`, `auto_apply`) should use `number`/`boolean` with proper parsing in the backend boundary |
| P2 | 🟠 INCOMPLETE | No frontend validation | `shared.tsx:4` | `Cfg` allows any string in any field — no min/max enforcement for numeric fields, no required-key checks, no provider/key consistency validation on the frontend |
| P2 | 🟡 SUSPECT | `EMPTY` default model values | `shared.tsx:30-38` | Several defaults look like copy-paste artifacts: `nvidia_model` default `"z-ai/glm-5.1"` (NVIDIA doesn't serve GLM?), `huggingface_model` default `"openai/gpt-oss-120b"` (not a HuggingFace endpoint), `together_model` default `"openai/gpt-oss-120b"` (not Together's naming) |
| P2 | 🟡 SUSPECT | `ApiKeyInput` placeholder map duplication | `shared.tsx:250-255` | Per-provider key format placeholders duplicate knowledge that could live in `PROVIDERS` metadata |
| P3 | 🟢 CLEAN | `GlobalSettings.tsx` | all | Well-structured, clear responsibilities, proper separation |
| P3 | 🟢 CLEAN | `StepSettings.tsx` | all | Minimal, clear delegation |
| P3 | 🟢 CLEAN | `AutomationSettings.tsx` | all | Simple toggles with clear UI labels |
| P3 | 🟢 CLEAN | `KEY_FIELD` / `GLOBAL_MODEL_FIELD` | `shared.tsx:145,154` | Clean mapping pattern matching provider IDs to `Cfg` keys |
| P3 | 🟢 CLEAN | `StepCard` component | `shared.tsx:265` | Well-structured compound component with clear global/custom toggle pattern |

---

## 5. Dependencies

**Inbound (other units depend on this):**
- `src/SettingsModal.tsx` — imports all 5 files; uses `EMPTY`, `Cfg`, and all four settings components

**Outbound (this unit depends on others):**
- `src/components/Icon` — used by `StepCard`, `BigToggle` in `shared.tsx`
- `src/types` (specifically `ApiFetch`) — used by `GlobalSettings.tsx`

**External (third-party libs used):**
| Library | Used for | Version pin? | Flag |
|---------|----------|-------------|------|
| `react` (useState, useEffect, ChangeEvent) | Component state and event typing | via project `package.json` | 🟢 CLEAN |

---

## 6. First principles assessment

### `shared.tsx`
1. **Does this file need to exist?** Yes — central config schema + shared UI primitives.
2. **Does it do what it claims?** Partially — name suggests "shared" which is accurate, but it also contains non-trivial static data (`GLOBAL_SOURCE_PRESET`, `INDIA_SOURCE_PRESET`) that is domain-specific rather than shared.
3. **Is it the right place for this logic?** Partially — source presets would better live in a config data file; provider/model definitions are reasonable here but the hardcoding is a concern.
4. **What would break if deleted?** Everything — `Cfg` + `EMPTY` are the foundation; all 4 settings components + `SettingsModal` would fail.

### `DiscoverySettings.tsx`
1. **Does this file need to exist?** Yes — job discovery is a distinct settings domain.
2. **Does it do what it claims?** Yes — handles discovery configuration.
3. **Is it the right place for this logic?** Partially — India market references violate separation of concerns; market-specific logic should be externalized.
4. **What would break if deleted?** Settings modal would lack the entire scraping/discovery section.

### `GlobalSettings.tsx`
1. **Does this file need to exist?** Yes — global LLM config is a distinct concern.
2. **Does it do what it claims?** Yes.
3. **Is it the right place for this logic?** Yes — clean separation.
4. **What would break if deleted?** Users couldn't configure their default LLM provider.

### `StepSettings.tsx`
1. **Does this file need to exist?** Borderline — at 16 lines it could be inlined into `SettingsModal` or `shared.tsx`. But the semantic separation is defensible.
2. **Does it do what it claims?** Yes.
3. **Is it the right place for this logic?** Yes — but could be merged upward for brevity.
4. **What would break if deleted?** Per-step configuration would disappear; could be trivially inlined.

### `AutomationSettings.tsx`
1. **Does this file need to exist?** Yes — experimental automation is a distinct settings domain.
2. **Does it do what it claims?** Yes.
3. **Is it the right place for this logic?** Yes — clearly scoped and self-contained.
4. **What would break if deleted?** Three toggles would disappear from the settings modal.
