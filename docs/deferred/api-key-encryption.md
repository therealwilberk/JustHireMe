# API Key Encryption

**Status:** Pending

**Source:** docs/specs/roadmap.md Deferred section

## Description

Implement actual API key encryption at rest. Docs claim AES-256/DPAPI but keys stored in plaintext SQLite.

## Current State

grep for "encrypt", "AES", "DPAPI" — zero results. No encryption exists. All keys stored via save_settings() in SQLite without encryption.

## Why Deferred

Upstream concern. Fork will adopt upstream fix when available.

## Effort Estimate

Large

## Dependencies

Upstream implementation
