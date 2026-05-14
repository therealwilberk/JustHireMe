# India References Cleanup

**Status:** Pending

**Source:** AGENTS.md

## Description

India-specific logic remains in 8 files across agents/ and frontend — _india_clause() in query_gen.py, India market guide in help_agent.py, "Remote India" in lead_intel.py, "india" in scoring.py location lists, INDIA_SOURCE_PRESET in frontend shared.tsx, India buttons in DiscoverySettings.tsx, India dropdown in OnboardingWizard.tsx.

## Current State

All 8 files still contain India-specific logic. Was scoped as "separate effort" from the job target externalization.

## Why Deferred

Separate branch effort — affects both backend agents and frontend components.

## Effort Estimate

Medium

## Dependencies

None
