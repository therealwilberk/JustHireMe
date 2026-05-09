# Mission

> **Living document.** Update this file when project goals, audience, or scope materially change.
> Agent: read this file before starting any feature work. Do not infer mission from the codebase alone.

---

## Project Name

JustHireMe (Linux fork)

---

## One-Line Purpose

A fully independent Linux port of JustHireMe — a local-first AI job intelligence workbench — that runs natively on Arch Linux + Hyprland with feature parity to the Windows upstream.

---

## Problem Statement

The upstream JustHireMe is cross-platform by design but Windows-focused: release pipeline, packaging, documentation, and testing all target Windows. Linux users — particularly on Arch/Hyprland — have no supported path to build, run, or package the app. System dependencies are undocumented, hardcoded Windows paths break at runtime, and the PyInstaller sidecar build fails on Linux. This fork closes that gap.

---

## Target Users

| User Type | Description | Technical Level |
|-----------|-------------|-----------------|
| Primary   | The maintainer — Linux-using job seeker on Arch/Hyprland | High — comfortable with Rust/Python/React, Tauri, Arch packaging |
| Secondary | Linux-using job seekers who find this fork via public sharing | Moderate-High — can follow setup docs, install Arch packages |

---

## Core Objectives

1. JustHireMe builds and runs on Arch Linux + Hyprland with all core features functional
2. All Windows-isms (hardcoded paths, missing bundle targets, PyInstaller build) are resolved
3. Linux packaging (AppImage/deb) exists alongside documented release process
4. Fork is maintainable — can rebase on upstream changes without constant breakage

---

## Explicit Non-Goals

- [ ] Multi-platform support beyond Arch Linux (no Ubuntu/Fedora/NixOS packages planned)
- [ ] Mobile client or web deployment
- [ ] KE-specific scrapers (deferred until core Linux port is stable)
- [ ] Upstream contributions (operating as fully independent fork)
- [ ] Commercial licensing or monetization
- [ ] OS keychain / encrypted API key storage (upstream hasn't built it either)

---

## Success Criteria

| Criterion | Indicator |
|-----------|-----------|
| Builds on Arch | `npm run tauri build` succeeds on Arch with Hyprland |
| All core features work | Scan, rank, evaluate, generate produce same results as Windows |
| Linux bundle exists | `npm run package:linux` produces valid AppImage or deb |
| Data dirs XDG-compliant | App stores data in `~/.local/share/JustHireMe/` |
| No Windows paths in code | `LOCALAPPDATA` references replaced with XDG equivalents |
| Fork can rebase upstream | `git rebase main` on linux-base succeeds with minimal conflicts |

---

## Project Type

- [ ] Greenfield (new project from scratch)
- [ ] Brownfield (existing codebase being extended)
- [x] Fork (based on upstream project — see `audit-report.md`)
- [ ] Prototype / spike
- [ ] Production system

---

## Relationship to Upstream (Forks Only)

- **Upstream repo:** `vasu-devs/JustHireMe`
- **Fork strategy:** Track upstream main via periodic rebase. Keep Linux-specific changes in `linux-base`. Cherry-pick upstream bug fixes. Do not merge upstream features without review — test against Linux first.
- **Divergence intent:** Add Linux support layer (XDG paths, bundle targets, CI, docs, browser paths) while keeping the core feature set identical. Later divergence possible but not planned.

---

## Stakeholders

| Role | Name / Handle | Responsibility |
|------|---------------|----------------|
| Owner | @therealwilberk | Final decisions on scope and direction |
| Developer | Agent | Implementation per approved specs |

---

*Last updated: 2026-05-09 — Agent*
