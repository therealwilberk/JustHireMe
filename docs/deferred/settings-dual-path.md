# Settings Dual Path Consolidation

**Status:** Pending

**Source:** docs/analysis/specs/roadmap.md Deferred section

## Description

Consolidate the dual config path — `get_setting()` reads from SQLite settings table directly, while `backend/config/` Pydantic schemas are a separate path. Agents bypass the config layer and read SQLite directly.

## Current State

`get_setting()` still heavily used in agents (evaluator.py, actuator.py, selectors.py, contact_lookup.py). Config layer has zero `get_setting` calls. Dual path remains unresolved.

## Why Deferred

Was assigned to Phase C (Reliability) but not done.

## Effort Estimate

Large

## Dependencies

None
