# Stop Scan Button UI State Bug

**Status:** Partial

**Source:** AGENTS.md Known Issues

## Description

POST /api/v1/scan/stop force-cancels the running task and releases the ghost lock. Backend returns `{"status": "stopping"}` and broadcasts an eval_done WS event. If the button stays stuck, AgentOnline component likely isn't handling the HTTP response or WS event correctly.

## Current State

Partial — basic plumbing exists (src/App.tsx:118-122 has onStopScan, src/hooks/useWS.ts:40 handles eval_done event to dispatch scan-done). But AgentOnline component's state management needs investigation.

## Why Deferred

Frontend state management issue, not blocking core functionality.

## Effort Estimate

Small

## Dependencies

None
