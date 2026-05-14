# Loose Dependency Pins

**Status:** Pending

**Source:** docs/specs/roadmap.md Deferred section

## Description

All Python dependencies use `>=` with no upper bounds — risk of unexpected breaking changes on `uv sync`.

## Current State

All 22 prod deps + 2 dev deps in pyproject.toml use loose pins. uv.lock mitigates for local dev.

## Why Deferred

Low priority. uv.lock provides reproducibility for development.

## Effort Estimate

Small

## Dependencies

None
