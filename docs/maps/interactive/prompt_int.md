# Prompt — Interactive System Map (OpenDesign)
> Builds a living, navigable HTML system map for the JustHireMe Linux fork.
> Working directory: `docs/maps/interactive/`
> Data source: `docs/maps/*.md`
> Design tokens: custom dark palette (see Design direction). OpenDesign daemon is running but has no project-specific design system for this repo.

---

## What you are building

A multi-page interactive HTML application that tells the story of this
codebase. Not a documentation viewer. Not a file browser.

A system map — where a developer can land, immediately understand how
the app is structured, trace how data flows through it, zoom into any
unit, and see what's healthy and what needs attention.

The `.md` files are your data source. Extract the facts from them.
Do not render them as prose. Transform them into visual structure.

Every page is a different lens on the same system.
Together they form a complete picture.

---

## Locked decisions (from discover session)

1. **Visual direction** — Vercel meets Warp terminal. Dark, precise, high density. Not brutalist — this is a developer tool/inspector (Sentry, Datadog, Linear vibe). Dark background, tight typography, color only carries meaning.
2. **Session scope** — 3 sessions. Quality gate between each. Agent coordinates.
3. **Design tokens** — OpenDesign daemon has no project-specific design system. Custom palette defined below (dark tech/utility). No separate DESIGN.md needed.
4. **Architecture** — SPA with pushState. One HTML shell, content swaps via JS, sidebar persists across routes.
5. **D3** — Yes, pinned CDN version for graph + flow diagrams.
6. **Flag colors** — OKLch values confirmed (see below). Square 8px dots, no emoji, hover tooltip shows name + reason.
7. **Data** — Individual JSON files per unit, lazy-loaded on navigation. Not a single JS blob.
8. **Naming** — `backend-services` module → `backend-services` route. `index-master` → "Index" under SYSTEM.

---

## Before writing any code

1. Read every file in `docs/maps/`:
   - `INDEX.md`
   - `flows.md`
   - `backend-config.md`
   - `backend-db.md`
   - `backend-evaluators.md`
   - `backend-foundations.md`
   - `backend-generators.md`
   - `backend-integrations.md`
   - `backend-main.md`
   - `backend-routes.md`
   - `backend-scrapers.md`
   - `backend-services.md`
   - `backend-tests.md`
   - `build-ci.md`
   - `frontend-components.md`
   - `frontend-core.md`
   - `frontend-hooks.md`
   - `frontend-settings.md`
   - `frontend-views.md`
   - `tauri.md`

2. Extract all structured data from `.md` files and emit as individual JSON files:
   - All units, their files, their flag counts
   - All flows and their participants
   - All flag instances (type, location, reason)
   - All dependency relationships between units
   - All identified dead code, hardcodes, coupling risks
   Confirm extraction is complete before proceeding.

3. Lock the visual direction tokens into `styles.css` `:root` before writing any page content.

---

## Design direction

**Aesthetic:** Vercel meets Warp terminal. Dark, precise, high density.
Clean edges, sharp typography, no decoration. Data-dense code inspector
with restrained color — only flags carry saturation. Monospace for code
identifiers, a display face with personality for headings.

**Color palette (`:root` tokens):**

```css
:root {
  /* Backgrounds */
  --bg-app:       oklch(12% 0.008 250);    /* main canvas */
  --bg-sidebar:   oklch(10% 0.006 250);    /* sidebar, darker */
  --bg-surface:   oklch(16% 0.008 250);    /* cards, panels */
  --bg-hover:     oklch(20% 0.012 250);    /* hover states */
  --bg-accent:    oklch(24% 0.04 255 / 0.15); /* accent wash for selected items */

  /* Text */
  --fg:           oklch(92% 0.006 250);    /* primary text */
  --fg-muted:     oklch(60% 0.012 250);    /* secondary, metadata */
  --fg-dim:       oklch(38% 0.012 250);    /* placeholders, dividers */

  /* Borders */
  --border:       oklch(24% 0.008 250);    /* hairline separators */

  /* Accent (used sparingly — active state, highlight) */
  --accent:       oklch(62% 0.18 255);     /* electric blue, like Vercel's */

  /* Status signals */
  --success:      oklch(55% 0.12 150);     /* restrained green */
  --warning:      oklch(65% 0.14 75);      /* amber */
  --danger:       oklch(52% 0.18 29);      /* clear red */
}
```

**Display typeface (headings):** Something with character, not Inter, not Space Grotesk, not Syne. Pick a geometric face with personality from Google Fonts. Options to evaluate: Satoshi, Manrope, Cabinet Grotesk, or similar — choose something that feels precise but distinct.

**Body:** System sans (`-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif`). Clean, readable at small sizes.

**Mono:** `'JetBrains Mono', 'IBM Plex Mono', ui-monospace, monospace` with `font-variant-numeric: tabular-nums`.

**Motion:**
- Page transitions: fade + translateY, 200ms, CSS class toggle
- Graph edges: draw-on animation on load
- Unit cards: border accent slides in on hover, 150ms
- Flag dots: pulse once on page load, then static
- Sidebar active state: smooth indicator slide

**Layout:**
- Persistent left sidebar: unit navigation + page list, always visible
- Main content area: changes per page
- No top navbar — sidebar owns navigation
- Generous spacing in content areas, tight density in sidebar
- Flag filter bar appears at top of pages where flags are displayed

---

## Page architecture (SPA)

Single-page application with pushState routing. `index.html` is the shell.
All pages are rendered by `app.js` which loads JSON data and renders
templates into the content mount point.

### Route table

| Route | Page | Data file | Description |
|-------|------|-----------|-------------|
| `/` | System Overview | `data/overview.json` | Force-directed graph of all units |
| `/flows` | Application Flows | `data/flows.json` | Animated flow diagrams |
| `/flags` | Flag Registry | `data/flags.json` | Full filterable flag table |
| `/index` | Master Index | `data/master-index.json` | Searchable file index |
| `/backend/config` | Config | `data/backend-config.json` | Unit detail |
| `/backend/db` | DB | `data/backend-db.json` | Unit detail |
| `/backend/evaluators` | Evaluators | `data/backend-evaluators.json` | Unit detail |
| `/backend/foundations` | Foundations | `data/backend-foundations.json` | Unit detail |
| `/backend/generators` | Generators | `data/backend-generators.json` | Unit detail |
| `/backend/integrations` | Integrations | `data/backend-integrations.json` | Unit detail |
| `/backend/main` | Main | `data/backend-main.json` | Unit detail |
| `/backend/routes` | Routes | `data/backend-routes.json` | Unit detail |
| `/backend/scrapers` | Scrapers | `data/backend-scrapers.json` | Unit detail |
| `/backend/services` | Services | `data/backend-services.json` | Unit detail |
| `/backend/tests` | Tests | `data/backend-tests.json` | Unit detail |
| `/frontend/components` | Components | `data/frontend-components.json` | Unit detail |
| `/frontend/core` | Core | `data/frontend-core.json` | Unit detail |
| `/frontend/hooks` | Hooks | `data/frontend-hooks.json` | Unit detail |
| `/frontend/settings` | Settings | `data/frontend-settings.json` | Unit detail |
| `/frontend/views` | Views | `data/frontend-views.json` | Unit detail |
| `/infra/tauri` | Tauri | `data/tauri.json` | Unit detail |
| `/infra/build-ci` | Build & CI | `data/build-ci.json` | Unit detail |

---

### Route: `/` — System Overview

**Story:** Land here. Understand the whole system in 30 seconds.

**What it shows:**
- A visual graph of all units as nodes, connected by dependency edges
  extracted from each unit's dependency section in the `.md` files
- Node size reflects file count in that unit
- Node color reflects overall health: proportion of clean vs flagged items
  (green-leaning = mostly clean, amber = mixed, red-leaning = issues)
- Clicking a node navigates to that unit's detail page via pushState
- A flag summary bar at the top: total counts per flag type across
  all units. Clicking a flag type filters the graph to highlight
  units containing that flag.
- Commit/branch indicator in the sidebar footer — reads from
  `.git/HEAD` if accessible, otherwise shows a static version field

**Do not show:** raw flag lists, file names, function names.
This page is altitude. Keep it high.

---

### Route: `/flows` — Application Flows

**Story:** How does data actually move through this system?

**What it shows:**
- All flows identified in `flows.md`, listed in a left panel
- Selecting a flow renders an animated flow diagram in the main area:
  - Each participant unit is a node
  - Directed edges show the sequence, labeled with the action
    (e.g. "HTTP POST", "persists lead", "broadcasts via WS")
  - Edges draw on sequentially when the flow is selected — not all at once
  - Entry point is visually distinct (e.g. a different border treatment)
  - Exit points (success / error / cancel) are labeled
- Below the diagram: a step-by-step breakdown as a numbered list
  Only function names and route paths — no prose repetition
- Flag callouts: if a flow contains flagged items, they appear as
  small inline indicators on the relevant node. Hovering shows the
  flag reason.

**Flows to render (minimum — add others from `flows.md`):**
- Scan flow
- Ghost mode flow
- Ingest flow
- Application fire flow
- WebSocket flow
- Settings flow
- Reevaluation flow
- Help/chat flow

---

### Route: `/flags` — Flag Registry

**Story:** What needs attention and where is it?

**What it shows:**
- Full filterable table of every flag across the entire codebase
- Columns: Flag type | Item | File | Line | Reason | Unit
- Filter bar: toggle any flag type on/off
- Secondary filter: by unit
- Sort: by flag severity (dead first) by default, sortable by unit or file
- A summary strip at top: count per flag type with a small bar
  showing proportion
- Clicking any row navigates to that unit's detail page,
  scrolled to the relevant section

---

### Routes: `/backend/*`, `/frontend/*`, `/infra/*` — Unit detail pages

One route per unit. Data loaded from the corresponding JSON file.

**Story:** Zoom into one unit. Understand what it owns, what it
connects to, and what needs work.

**Layout (consistent across all unit pages):**

**Header area:**
- Unit name (large, display font)
- One-sentence purpose (extracted from unit summary)
- Flag count summary: small colored squares, one per flag type present,
  with count. E.g. [RED 3] [AMBER 1] [BLUE 5]
- Breadcrumb link back to System Overview (top-left)

**Three-column content area:**

*Left column — File tree:*
- Every file in this unit listed
- Each file has its overall flag dot
- Clicking a file name scrolls the center column to that file's breakdown
- Active file highlighted with a left border accent

*Center column — File breakdowns:*
- For each file, in order:
  - File name (monospace, prominent)
  - Purpose paragraph (one sentence max — distill, don't copy)
  - Classes and functions as a structured list:
    - Name (monospace)
    - Flag dot(s) inline
    - Purpose (one line)
    - Hover expands: shows params, returns, calls, side effects
  - Import health: small indicator showing unused import count

*Right column — Connections:*
- Inbound: what other units depend on this one
- Outbound: what this unit depends on
- Each connection is a clickable link to that unit's page
- External dependencies listed below with version pin status

**Bottom section — First principles panel:**
A card for each "Does this need to exist?" assessment from the `.md`.
Three states rendered as distinct card styles:
- Needed: clean, minimal border
- Partially needed: amber left border
- Not needed: red left border, slightly reduced opacity

---

### Route: `/index` — Master Index

**Story:** The complete reference. Everything in one searchable place.

**What it shows:**
- Full searchable table of every file in the codebase
- Columns: File | Unit | Lines | Purpose | Flags
- Global search: filters rows in real time as you type
- Export button: copies current filtered view as markdown table
- At top: system-wide flag summary
- At bottom: three quick-reference panels side by side:
  - Dead code candidates (all DEAD flags)
  - Hardcode registry (all HARDCODED flags)
  - Coupling risks (all COUPLED flags)

---

## Flag color system (consistent across all pages)

```css
--flag-dead:        oklch(52% 0.18 29);     /* clear red */
--flag-stale:       oklch(65% 0.14 75);     /* amber */
--flag-suspect:     oklch(72% 0.12 95);     /* yellow, slightly muted */
--flag-hardcoded:   oklch(55% 0.15 250);    /* blue */
--flag-coupled:     oklch(48% 0.10 290);    /* purple, muted */
--flag-incomplete:  oklch(70% 0.01 240);    /* grey-white */
--flag-clean:       oklch(55% 0.12 150);    /* restrained green */
```

Rendered as 8px square dots, no emoji, no circles.
Hover reveals tooltip: flag name + reason text.

---

## Shared elements (apply to every page)

**Sidebar (persistent, left):**
```
[App name / logo mark]     ← small, top of sidebar

SYSTEM
  Overview
  Flows
  Flag Registry
  Index

BACKEND
  Config
  DB
  Evaluators
  Foundations
  Generators
  Integrations
  Main
  Routes
  Scrapers
  Services
  Tests

FRONTEND
  Components
  Core
  Hooks
  Settings
  Views

INFRASTRUCTURE
  Tauri
  Build & CI

[branch indicator]         ← bottom of sidebar
[version / last updated]
```

Active page: left border accent in accent color, 2px.
Hover: background shifts subtly, label brightens slightly.
No icons — text only.

**Sidebar width:** fixed, not collapsible. This is a desktop tool.

**Page transitions:**
SPA route changes: current content fades out (opacity 0, translateY -8px, 180ms).
New content fades in (opacity 0 → 1, translateY 8px → 0, 200ms).
CSS classes toggled by JS — no libraries.

---

## Dependencies

- **D3.js** — pinned CDN version for graph rendering and flow diagrams
- **Google Fonts** — one display typeface with personality (not Inter/Space Grotesk/Syne)
- **Zero other JS dependencies**

---

## Versioning and updates

The sidebar footer shows:
- Current git branch (read from `.git/HEAD` — if not accessible,
  show a `[branch]` placeholder that can be manually updated)
- `Last updated:` field populated from the most recent `.md`
  file modification date if accessible, otherwise a static field

When the maps are updated (new agent run, code changes), the HTML
regenerates from updated `.md` files. Only the data JSON files change —
the shell, CSS, and JS stay the same.

---

## File output

```
docs/maps/interactive/
├── index.html                           ← SPA shell (sidebar + content mount + nav)
├── styles.css                           ← all shared styles + token overrides
├── app.js                               ← SPA router, transitions, graph, filter, flow renderer
├── data/
│   ├── overview.json                    ← graph nodes + edges + flag aggregates
│   ├── flows.json                       ← flow definitions + step data
│   ├── flags.json                       ← all flag instances across codebase
│   ├── master-index.json                ← every file's metadata
│   ├── backend-config.json              ← unit detail data
│   ├── backend-db.json
│   ├── backend-evaluators.json
│   ├── backend-foundations.json
│   ├── backend-generators.json
│   ├── backend-integrations.json
│   ├── backend-main.json
│   ├── backend-routes.json
│   ├── backend-scrapers.json
│   ├── backend-services.json
│   ├── backend-tests.json
│   ├── build-ci.json
│   ├── frontend-components.json
│   ├── frontend-core.json
│   ├── frontend-hooks.json
│   ├── frontend-settings.json
│   ├── frontend-views.json
│   └── tauri.json
└── vendor/
    └── d3.min.js                        ← pinned D3 version (loaded locally for offline)
```

---

## Build order

Work in this sequence across 3 sessions. Quality gate between each.

**Session 1 — Data extraction + foundation:**
1. Extract all data from `.md` files into individual JSON files under `data/`
2. Build `styles.css` — tokens, layout, sidebar, components, flag colors, typography
3. Build `app.js` — SPA shell with pushState router, sidebar renderer, page transition handler
4. Build `index.html` — SPA entry point (minimal shell with mount point)
5. Verify: load `index.html`, navigate sidebar, confirm pushState works, transitions animate

**Session 2 — Core pages + interaction:**
6. Build overview graph renderer (D3 force-directed) in `app.js`
7. Build `/flows` page — flow list panel + animated D3 diagram + step list
8. Build `/flags` page — filterable table with sort, flag type toggles, unit filter
9. Build `/index` page — searchable master table with export
10. Verify: all 4 special pages render with real data, filters work, graph navigates

**Session 3 — All unit pages + polish:**
11. Build unit page renderer in `app.js` (shared template, data-driven)
12. Verify with 2-3 unit data files, fix layout issues
13. Generate remaining 17 unit JSON data files
14. Test all 20 unit routes render correctly
15. Final pass: test every sidebar link, every cross-page reference, every transition

---

## Rules

**Data first, markup second.** If the `.md` file doesn't say it,
don't show it. No invented content.

**No prose dumps.** If you find yourself copying a paragraph from
a `.md` file into the HTML, stop. Distill it to one line or a
structured visual element.

**Consistency over creativity on unit pages.** The system overview
and flows pages can be distinctive. Unit pages must be consistent
with each other — a developer jumping between units should feel
the same structure every time.

**Flag dots are always square, always 8px, never emoji.**

**Every link works.** Before declaring done, verify every
sidebar link, every node click, every cross-page reference.

**Smart zone rule.** Build one page at a time. Verify it renders
correctly before moving to the next. Do not attempt all 21 pages
in one session.
