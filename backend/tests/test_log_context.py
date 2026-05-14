import asyncio
import uuid

import pytest

from log_context import (
    CorrelationContext,
    get_context,
    new_context,
    reset_context,
    set_context,
    enrich,
)


class TestContextBasics:
    def test_new_context_has_uuid4(self):
        ctx = new_context(workflow_type="test")
        assert ctx.workflow_type == "test"
        assert len(ctx.correlation_id) == 36
        assert ctx.correlation_id.count("-") == 4

    def test_get_context_returns_none_when_not_set(self):
        assert get_context() is None

    def test_set_and_get_context(self):
        ctx = new_context(workflow_type="test")
        token = set_context(ctx)
        try:
            assert get_context() is ctx
        finally:
            reset_context(token)

    def test_reset_restores_prior_state(self):
        ctx_a = new_context(workflow_type="a")
        ctx_b = new_context(workflow_type="b")
        token_a = set_context(ctx_a)
        set_context(ctx_b)
        reset_context(token_a)
        assert get_context() is None

    def test_enrich_creates_new_instance(self):
        ctx = new_context(workflow_type="base")
        token = set_context(ctx)
        try:
            token2 = enrich(workflow_type="enriched", lead_id="123")
            enriched = get_context()
            assert enriched is not ctx
            assert enriched.workflow_type == "enriched"
            assert enriched.lead_id == "123"
            assert enriched.correlation_id == ctx.correlation_id
            reset_context(token2)
            assert get_context().workflow_type == "base"
        finally:
            reset_context(token)

    def test_enrich_raises_when_no_context(self):
        with pytest.raises(RuntimeError, match="No correlation context"):
            enrich(lead_id="123")

    def test_context_fields_default_to_none(self):
        ctx = new_context()
        assert ctx.lead_id is None
        assert ctx.job_id is None
        assert ctx.node is None
        assert ctx.subsystem is None
        assert ctx.degraded is False
        assert ctx.retrying is False


class TestContextIsolation:
    def test_tasks_do_not_share_context(self):
        results = []

        async def task_a():
            ctx = new_context(workflow_type="a")
            token = set_context(ctx)
            try:
                await asyncio.sleep(0.01)
                results.append(("a", get_context().workflow_type))
            finally:
                reset_context(token)

        async def task_b():
            ctx = new_context(workflow_type="b")
            token = set_context(ctx)
            try:
                await asyncio.sleep(0.02)
                results.append(("b", get_context().workflow_type))
            finally:
                reset_context(token)

        async def run():
            await asyncio.gather(task_a(), task_b())

        asyncio.run(run())
        assert ("a", "a") in results
        assert ("b", "b") in results

    def test_enrich_in_one_task_does_not_affect_another(self):
        results = []

        async def task_a():
            ctx = new_context(workflow_type="a")
            token = set_context(ctx)
            try:
                enrich(lead_id="lead-a")
                await asyncio.sleep(0.01)
                c = get_context()
                results.append(("a", c.workflow_type, c.lead_id))
            except RuntimeError:
                results.append(("a", "error", None))
            finally:
                reset_context(token)

        async def task_b():
            ctx = new_context(workflow_type="b")
            token = set_context(ctx)
            try:
                await asyncio.sleep(0.02)
                c = get_context()
                results.append(("b", c.workflow_type, c.lead_id))
            finally:
                reset_context(token)

        async def run():
            await asyncio.gather(task_a(), task_b())

        asyncio.run(run())
        assert ("a", "a", "lead-a") in results
        assert ("b", "b", None) in results
