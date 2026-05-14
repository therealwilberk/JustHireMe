# OS Keychain Integration

**Status:** Pending

**Source:** docs/analysis/specs/roadmap.md Deferred section

## Description

Encrypt API keys at rest using OS keychain integration (libsecret on Linux).

## Current State

grep for "keychain" returns only text mentions in help_agent.py ("OS keychain storage is planned" — no implementation). grep for "libsecret" returns 0 hits. All 17 provider keys stored in SQLite settings table as plaintext.

## Why Deferred

Needs system-level integration (libsecret), not blocking for current use.

## Effort Estimate

Large

## Dependencies

None
