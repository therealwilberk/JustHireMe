# Textarea Input Validation Gap

**Status:** Pending

**Source:** AGENTS.md Known Issues

## Description

The `job_boards` textarea (frontend → POST /api/v1/settings) has no input validation. Entries like `site:opp ("jobs" OR "careers")` pass through unscathed. Validation only runs on the new PUT /api/v1/settings/job-targets CRUD API.

## Current State

Confirmed in `backend/routes/settings.py:72-96` — POST /api/v1/settings calls save_settings(payload) with NO validation on job_boards. Contrast with lines 112-149 which calls validate_job_targets().

## Why Deferred

Phase 5 frontend work — needs UI changes.

## Effort Estimate

Medium

## Dependencies

Frontend CRUD UI (Phase 5)
