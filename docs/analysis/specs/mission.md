# Mission

> **Living document.** Update this file when project goals, audience, or scope materially change.
> Agent: read this file before starting any feature work. Do not infer mission from the codebase alone.

---

## Project Name

`JustHireMe`

---

## One-Line Purpose

A local-first AI-powered job search intelligence desktop app that scrapes, scores, and tracks engineering roles — with tailored application generation.

---

## Problem Statement

Job hunting across multiple boards produces context-switching overhead, inconsistent tracking, and manual application material tailoring. This tool centralizes discovery, ranking, and generation so the user focuses on interviewing instead of admin.

---

## Target Users

| User Type | Description | Technical Level |
|-----------|-------------|-----------------|
| Primary   | Technical professionals (SWE, data, infra) actively job-hunting | Comfortable with CLI, env vars, basic config |
| Secondary | Career switchers or passive candidates exploring the market | Varies |

---

## Core Objectives

1. Aggregate jobs from 15+ sources into a unified, searchable pipeline
2. Score and rank leads objectively using deterministic rubrics + optional LLM
3. Generate tailored resumes and cover letters from the user's profile
4. Track application progress through a pipeline with follow-up reminders

---

## Explicit Non-Goals

- [x] This is NOT a multi-tenant SaaS product — local-first, single-user desktop app
- [x] This is NOT a general-purpose AI platform — LLMs are optional for scoring
- [x] This is NOT a mobile client — Tauri 2 desktop only (Linux primary target)

---

## Success Criteria

| Criterion | Indicator |
|-----------|-----------|
| User can configure scraping sources without editing code | Config files in data dir replace hardcoded source lists |
| All 150+ hardcoded values moved to typed config objects | No magic URLs, thresholds, or model names in source code |
| No silent failures | Zero `except: pass` in production code paths |
| API keys not stored in plaintext | Keys resolved from env vars, not SQLite |
| Full test suite passes in CI | All 100+ backend tests run on every push |

---

## Project Type

- [ ] Greenfield (new project from scratch)
- [ ] Brownfield (existing codebase being extended)
- [x] Fork (based on upstream project — see `audit-report.md`)
- [ ] Prototype / spike
- [ ] Production system

---

## Relationship to Upstream (Forks Only)

- **Upstream repo:** `https://github.com/vasu-devs/JustHireMe`
- **Fork strategy:** Solo fork. Watch upstream for major updates and cherry-pick valuable changes manually. Do not push changes upstream.
- **Divergence intent:** Our fork focuses on infrastructure hardening, Linux-first packaging, and user-configurable customization. Upstream features are evaluated per-merge.

---

## Stakeholders

| Role | Name / Handle | Responsibility |
|------|---------------|----------------|
| Owner | @kamaa | Final decisions on scope and direction |
| Developer | Agent (big-pickle) | Implementation per approved specs |

---

_Last updated: 2026-05-13 — Agent_
