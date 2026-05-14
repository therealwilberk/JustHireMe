# CORS Origin Regex Config

**Status:** Pending

**Source:** docs/analysis/specs/roadmap.md Deferred section

## Description

Move hardcoded `_LOCAL_ORIGIN_RE` from `backend/core/config_constants.py:20` to `settings.app.cors.local_origin_regex` in the config layer.

## Current State

Still hardcoded in config_constants.py, imported and used in main.py. Not moved to Pydantic config.

## Why Deferred

Was assigned to Phase B (Security) but not done. CORS tightening deferred.

## Effort Estimate

Small

## Dependencies

None
