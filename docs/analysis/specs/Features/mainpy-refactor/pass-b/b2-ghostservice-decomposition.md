# Pass B2 — GhostService Decomposition

**Mode:** HITL  
**Branch:** `feature/mainpy-refactor-pass-b`  
**Blocked by:** Pass B1 (ScanManager class)

---

## Goal

Decompose `_ghost_tick_impl` (~139 lines, 6 phases) into named phase methods on a `GhostService` class. Each phase becomes independently readable, testable, and maintainable.

## Current State

`services/ghost.py` has:
- `_ghost_tick()` — lock acquisition wrapper (12 lines)
- `_ghost_tick_impl()` — 139-line monolith doing:

  1. **Preflight** — check ghost mode enabled, load config/profile
  2. **X scan** — call `_run_x_signal_scan()`
  3. **Free scan** — call `_run_free_source_scan()`
  4. **Board scout** — generate queries, scout via Apify
  5. **Evaluation** — score discovered leads
  6. **Generation** — generate resume/cover letter for approved leads
  7. **Auto-apply** — submit applications (if enabled)

## Target Structure

```python
class GhostService:
    def __init__(self, scan_manager: ScanManager):
        self._scan_manager = scan_manager

    async def run(self):
        """Public entrypoint — runs one complete ghost cycle."""
        ...

    async def _phase_preflight(self) -> tuple[dict, ...] | None:
        """Check ghost mode, load config. Returns None to skip."""
        ...

    async def _phase_x_scan(self, cfg, profile):
        """Run X signal scout."""
        ...

    async def _phase_free_scan(self, cfg, profile):
        """Run free source scout."""
        ...

    async def _phase_scout(self, cfg, profile, boards):
        """Generate queries and scout job boards."""
        ...

    async def _phase_eval(self, cfg, profile) -> list[dict]:
        """Score discovered leads, return approved list."""
        ...

    async def _phase_gen(self, approved: list[dict]) -> list[dict]:
        """Generate assets for approved leads."""
        ...

    async def _phase_apply(self, generated: list[dict]):
        """Submit applications if auto-apply is enabled."""
        ...
```

## Phase Boundaries

Each phase should be:
- Under 30 lines
- Self-contained (input params → side effects → return)
- Testable in isolation

The `run()` method becomes a sequential orchestration:

```python
async def run(self):
    ctx = new_context(workflow_type="ghost_scan", subsystem="scheduler")
    token = set_context(ctx)
    try:
        result = await self._phase_preflight()
        if result is None:
            return
        cfg, profile, boards = result
        await self._phase_x_scan(cfg, profile)
        await self._phase_free_scan(cfg, profile)
        await self._phase_scout(cfg, profile, boards)
        approved = await self._phase_eval(cfg, profile)
        if not approved:
            return
        generated = await self._phase_gen(approved)
        await self._phase_apply(generated)
    finally:
        reset_context(token)
```

## Verification

```bash
cd backend && uv run python -m pytest tests/ -q --tb=line
```

All 300 tests must pass. The ghost mode is only testable via integration tests (it requires scheduler + DB), so the main verification is that `_ghost_tick` still fires and the phases execute sequentially without error.

## Commit

```
refactor(b2): decompose ghost tick into GhostService phase methods
```
