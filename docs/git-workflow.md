# Git Workflow — JustHireMe Fork
> Enforced rules for agent-assisted development. Follow exactly. No exceptions.

---

## Remotes

| Remote | Points To | Purpose |
|--------|-----------|---------|
| `upstream` | `vasu-devs/JustHireMe` | Original repo. Never push here. |
| `origin` | `therealwilberk/JustHireMe` | Your fork. All pushes go here. |

**Setup (one time only):**
```bash
git remote add upstream https://github.com/vasu-devs/JustHireMe.git
```

---

## Branch Hierarchy

```
upstream/main
      ↓  (rebase only)
  origin/main          ← clean mirror of upstream. NEVER commit here.
      ↓  (rebase only)
  linux-base           ← permanent Linux port. All Linux-specific changes live here.
      ↓  (branch off)
  feature/*            ← short-lived. branch off linux-base. merge back when done.
  fix/*                ← short-lived. branch off linux-base. merge back when done.
  experiment/*         ← short-lived. branch off linux-base. merge back or discard.
```

---

## Branch Rules

### `main`
- **NEVER commit directly to `main`.**
- Only updated by pulling from `upstream`. No exceptions.
- No feature work, no fixes, no experiments.

### `linux-base`
- The permanent foundation for all Linux customization.
- Only updated by: merging finished `feature/*`, `fix/*`, or `experiment/*` branches into it, OR rebasing it onto `main` when upstream updates arrive.
- **NEVER branch off `main` for Linux work — always branch off `linux-base`.**

### `feature/*`
- Naming: `feature/short-description` (e.g., `feature/brightermondo-scraper`)
- Branch source: `linux-base`
- Merge target: `linux-base`
- Delete after merging.

### `fix/*`
- Naming: `fix/short-description` (e.g., `fix/sidecar-path-crash`)
- Branch source: `linux-base`
- Merge target: `linux-base`
- Delete after merging.

### `experiment/*`
- Naming: `experiment/short-description` (e.g., `experiment/ollama-ranking`)
- Branch source: `linux-base`
- Merge target: `linux-base` if kept, otherwise discard.
- These may be abandoned. That is fine.

---

## Workflows

### Starting new work
```bash
git checkout linux-base
git checkout -b feature/your-feature-name   # or fix/ or experiment/
```

### Finishing a branch
```bash
git checkout linux-base
git merge feature/your-feature-name
git branch -d feature/your-feature-name
git push origin linux-base
```

### Pulling upstream updates
```bash
# 1. Fetch upstream changes
git fetch upstream

# 2. Update main (clean mirror — fast-forward only)
git checkout main
git merge --ff-only upstream/main
git push origin main

# 3. Rebase linux-base onto updated main
git checkout linux-base
git rebase main

# 4. If conflicts: resolve → git add <file> → git rebase --continue

# 5. Push rebased linux-base (force required after rebase)
git push origin linux-base --force-with-lease
```

> ⚠️ Only `linux-base` is rebased against `main`. Short-lived branches are finished and merged back before upstream updates arrive. If a short-lived branch is still open during an upstream update, rebase it against `linux-base` after step 3, not against `main`.

---

## Commit Message Format

```
type: short description in present tense

[optional body if context is needed]
```

| Type | When to use |
|------|-------------|
| `feat` | New capability added |
| `fix` | Bug or crash resolved |
| `chore` | Build config, packaging, deps |
| `refactor` | Code restructure, no behavior change |
| `experiment` | Exploratory — may be reverted |

Examples:
```
feat: add BrighterMonday scraper module
fix: use os.path.join for cross-platform sidecar path
chore: configure Tauri AppImage build target for Linux
```

---

## What Never Goes in the Repo

Add these to `.gitignore` before any first push:

```
# Personal data
*.db
*.sqlite
resume.*
cover_letter.*
.env
.env.*

# API keys / credentials
config.local.*
secrets.*

# OS artifacts
.DS_Store
Thumbs.db
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start a feature | `git checkout linux-base && git checkout -b feature/name` |
| Start a fix | `git checkout linux-base && git checkout -b fix/name` |
| Finish a branch | `git checkout linux-base && git merge <branch> && git branch -d <branch>` |
| Pull upstream | `git fetch upstream && git checkout main && git merge --ff-only upstream/main` |
| Rebase foundation | `git checkout linux-base && git rebase main` |
| Check branch state | `git log --oneline --graph --all` |

---

## Agent Instructions

When assisting with this repo:

1. **Always confirm the current branch before writing or running any git command.** Run `git branch --show-current` first.
2. **Never suggest committing to `main` or pushing to `upstream`.**
3. **All new work starts from `linux-base`**, not `main`.
4. **Short-lived branches (`feature/*`, `fix/*`, `experiment/*`) must be merged back into `linux-base` before being closed**, not into `main`.
5. **When rebasing `linux-base` onto `main`, use `--force-with-lease`** on the push, never bare `--force`.
6. **If a conflict arises during rebase, stop and surface it** — do not auto-resolve without confirmation.
7. **Do not assume branch names** — verify with `git branch -a` if uncertain.
