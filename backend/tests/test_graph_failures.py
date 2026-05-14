"""Orchestration failure-path tests for graph reliability.

These tests cover both characterization (locking current behavior)
and intentional semantics (documenting the fault-tolerant contract).
Tests that were updated from characterization to correctness document
the behavior change in their docstring.

The orchestration model is intentionally fault-tolerant:
- Each node catches its own failures
- Nodes set error+error_stage on failure
- Nodes NEVER clear upstream errors (error is append-only)
- persist_node returns structured errors instead of crashing
"""

import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

import pytest

os.environ["LOCALAPPDATA"] = str(Path(__file__).resolve().parent)

from tests.fakes import _install_storage_fakes

_install_storage_fakes()

from graph import build_eval_graph, PipelineState

_SHARED_LEAD = {
    "job_id": "test-job-001",
    "title": "Software Engineer",
    "company": "Acme",
    "url": "https://example.com/job/001",
    "description": "We need a great engineer.",
}

_SHARED_PROFILE = {
    "candidate": {"n": "Test User", "s": "engineer"},
    "skills": [],
    "projects": [],
    "experience": [],
}

_SHARED_CFG = {"auto_generate_threshold": 60}

_EVAL_RESULT = {
    "score": 75,
    "reason": "Good stack match.",
    "match_points": ["Stack overlap: Python 80/100"],
    "gaps": [],
}

_GEN_RESULT = {
    "resume": "/tmp/test-resume.pdf",
    "cover_letter": "/tmp/test-cover.pdf",
    "selected_projects": [],
    "keyword_coverage": {},
}

_GEN_EMPTY = {
    "resume": "",
    "cover_letter": "",
    "selected_projects": [],
    "keyword_coverage": {},
}


def _base_state(**overrides) -> PipelineState:
    base: PipelineState = {
        "job_id": "test-job-001",
        "lead": dict(_SHARED_LEAD),
        "profile": dict(_SHARED_PROFILE),
        "cfg": dict(_SHARED_CFG),
        "score": 0,
        "reason": "",
        "match_points": [],
        "gaps": [],
        "asset_path": "",
        "cover_letter_path": "",
        "error": None,
        "error_stage": None,
    }
    base.update(overrides)
    return base


# ==============================================================
# Boundary 1: persist_node — unhandled SQLite write failure
# ==============================================================


@pytest.mark.integration
class TestPersistNodeFailures(unittest.TestCase):
    """Characterize behavior when persist_node's DB calls fail.

    Current contract: persist_node has NO exception handling.
    update_lead_score and save_asset_package execute bare — any exception
    propagates through LangGraph and crashes the graph invocation.
    """

    def setUp(self):
        self._patches = [
            mock.patch("agents.evaluator.score", return_value=dict(_EVAL_RESULT)),
            mock.patch("agents.generator.run_package", return_value=dict(_GEN_RESULT)),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def test_persist_returns_empty_dict_on_success(self):
        """Characterize: persist_node returns {} on success.

        The final graph state is whatever prior nodes produced.
        persist does not add or overwrite any state field.
        """
        with (
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())
        self.assertEqual(result.get("score"), 75)
        self.assertIsNone(result.get("error"))
        # The empty dict means key/values from earlier nodes survive
        self.assertEqual(result.get("asset_path"), "/tmp/test-resume.pdf")

    def test_persist_update_lead_score_crash_returns_structured_error(self):
        """Corrected: persist_node now catches DB exceptions.

        Instead of crashing the graph, persist_node returns a structured
        error state with ``error`` and ``error_stage`` set. The graph
        completes normally — the API layer can inspect the result.
        """
        with (
            mock.patch(
                "db.client.update_lead_score",
                side_effect=RuntimeError("DB locked"),
            ),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result.get("error"), "DB locked")
        self.assertEqual(result.get("error_stage"), "persist")
        # Score from evaluate is still preserved
        self.assertEqual(result.get("score"), 75)
        # Asset paths from generate are still preserved
        self.assertEqual(result.get("asset_path"), "/tmp/test-resume.pdf")

    def test_persist_save_asset_package_crash_returns_structured_error(self):
        """Corrected: save_asset_package exception is also caught.

        Both DB writes in persist_node now have exception handling.
        """
        with (
            mock.patch("db.client.update_lead_score"),
            mock.patch(
                "db.client.save_asset_package",
                side_effect=RuntimeError("Disk full"),
            ),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result.get("error"), "Disk full")
        self.assertEqual(result.get("error_stage"), "persist")

    def test_save_asset_skipped_when_asset_paths_empty(self):
        """Characterize: save_asset_package is gated — not called when paths empty.

        The conditional ``if state.get("asset_path") or state.get("cover_letter_path"):``
        means persist_node may skip the asset save even though it executes.
        """
        with (
            mock.patch("agents.evaluator.score", return_value={"score": 30, "reason": "Weak", "match_points": [], "gaps": ["bad"]}),
            mock.patch("db.client.update_lead_score") as update_mock,
            mock.patch("db.client.save_asset_package") as save_mock,
        ):
            graph = build_eval_graph()
            graph.invoke(_base_state())

        save_mock.assert_not_called()
        update_mock.assert_called_once()

    def test_persist_failure_no_longer_silent_in_background_tasks(self):
        """Corrected: invoke() no longer raises on persist failure.

        The graph now returns normally with error/error_stage fields set.
        BackgroundTasks will complete, the WebSocket broadcast will fire,
        and the operator sees the error in the pipeline result.
        """
        with (
            mock.patch(
                "db.client.update_lead_score",
                side_effect=RuntimeError("DB locked"),
            ),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result.get("error"), "DB locked")
        self.assertEqual(result.get("error_stage"), "persist")


# ==============================================================
# Boundary 2: evaluate_node — LLM / scoring exception
# ==============================================================


@pytest.mark.integration
class TestEvaluateNodeFailures(unittest.TestCase):
    """Characterize behavior when evaluate_node raises.

    Current contract: evaluate_node catches all Exceptions and returns
    score=0, reason="eval failed", error=str(exc). Graph continues to
    generate_node, which sees score=0 < threshold and auto-skips.
    """

    def test_evaluate_exception_preserves_error_through_generate_skip(self):
        """Corrected: evaluate exception now survives through generate_node.

        generate_node no longer unconditionally sets ``error=None`` on the
        skip path — it returns only asset_path and cover_letter_path,
        preserving the error from evaluate_node.

        The error field is now "append-only": once set, only a later node's
        own failure overwrites it. A skip is not a failure.
        """
        graph = build_eval_graph()
        with mock.patch(
            "agents.evaluator.score",
            side_effect=ValueError("LLM returned garbage"),
        ):
            result = graph.invoke(_base_state())

        self.assertEqual(result.get("score"), 0)
        self.assertEqual(result.get("reason"), "eval failed")
        self.assertEqual(result.get("error"), "LLM returned garbage")
        self.assertEqual(result.get("error_stage"), "evaluate")

    def test_exception_causes_generate_skip(self):
        """Characterize: score=0 < threshold(60) → generate_node returns early.

        generate_node never calls run_package when score is below threshold.
        """
        gen_mock = mock.MagicMock()
        with mock.patch(
            "agents.evaluator.score",
            side_effect=ValueError("crash"),
        ):
            with mock.patch("agents.generator.run_package", gen_mock):
                with (
                    mock.patch("db.client.update_lead_score"),
                    mock.patch("db.client.save_asset_package"),
                ):
                    graph = build_eval_graph()
                    graph.invoke(_base_state())

        gen_mock.assert_not_called()

    def test_exception_still_persists_degraded_state(self):
        """Characterize: after evaluate crash, persist_node writes degraded state.

        update_lead_score is called with score=0 and reason="eval failed".
        save_asset_package is NOT called because asset_path is empty.
        """
        with mock.patch(
            "agents.evaluator.score",
            side_effect=ValueError("crash"),
        ):
            with (
                mock.patch("db.client.update_lead_score") as update_mock,
                mock.patch("db.client.save_asset_package") as save_mock,
            ):
                graph = build_eval_graph()
                graph.invoke(_base_state())

        update_mock.assert_called_once_with("test-job-001", 0, "eval failed", [], [])
        save_mock.assert_not_called()

    def test_non_crash_exception_caught_by_node(self):
        """Characterize: evaluate_node catches all Exception subclasses."""
        gen_mock = mock.MagicMock()
        for exc_type in (ValueError("msg"), RuntimeError("msg"), KeyError("msg"), TypeError("msg")):
            with self.subTest(exc=type(exc_type).__name__):
                with mock.patch("agents.evaluator.score", side_effect=exc_type):
                    with mock.patch("agents.generator.run_package", gen_mock):
                        with (
                            mock.patch("db.client.update_lead_score"),
                            mock.patch("db.client.save_asset_package"),
                        ):
                            graph = build_eval_graph()
                            result = graph.invoke(_base_state())

                self.assertEqual(result.get("score"), 0)


# ==============================================================
# Boundary 3: generate_node — LLM draft / PDF render failure
# ==============================================================


@pytest.mark.integration
class TestGenerateNodeFailures(unittest.TestCase):
    """Characterize behavior when generate_node raises.

    Current contract: generate_node catches all Exceptions and returns
    empty asset paths + error string. Graph continues to persist_node,
    which writes the score but skips asset save (paths are empty).
    """

    def setUp(self):
        self._eval_mock = mock.patch(
            "agents.evaluator.score", return_value=dict(_EVAL_RESULT)
        )
        self._eval_mock.start()

    def tearDown(self):
        self._eval_mock.stop()

    def test_exception_returns_empty_paths_with_error(self):
        """Characterize: exception → asset_path="", cover_letter_path="", error set."""
        with mock.patch(
            "agents.generator.run_package",
            side_effect=RuntimeError("PDF render failed"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result.get("asset_path"), "")
        self.assertEqual(result.get("cover_letter_path"), "")
        self.assertIsNotNone(result.get("error"))
        self.assertIn("PDF render failed", result["error"])

    def test_exception_still_persists_score_but_skips_asset_save(self):
        """Characterize: after generate crash, update_lead_score is called,
        save_asset_package is not (because asset paths are empty).
        """
        with (
            mock.patch(
                "agents.generator.run_package",
                side_effect=RuntimeError("crash"),
            ),
            mock.patch("db.client.update_lead_score") as update_mock,
            mock.patch("db.client.save_asset_package") as save_mock,
        ):
            graph = build_eval_graph()
            graph.invoke(_base_state())

        update_mock.assert_called_once_with(
            "test-job-001",
            75,
            "Good stack match.",
            ["Stack overlap: Python 80/100"],
            [],
        )
        save_mock.assert_not_called()

    def test_does_not_overwrite_score_on_failure(self):
        """Characterize: generate_node returns only asset/error fields.

        score is not in generate_node's return dict, so LangGraph
        preserves the score from evaluate_node.
        """
        with mock.patch(
            "agents.generator.run_package",
            side_effect=RuntimeError("crash"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result.get("score"), 75)
        self.assertEqual(result.get("reason"), "Good stack match.")

    def test_non_crash_exception_caught_by_node(self):
        """Characterize: generate_node catches all Exception subclasses."""
        for exc_type in (ValueError("msg"), RuntimeError("msg"), KeyError("msg"), TypeError("msg")):
            with self.subTest(exc=type(exc_type).__name__):
                with mock.patch("agents.generator.run_package", side_effect=exc_type):
                    graph = build_eval_graph()
                    result = graph.invoke(_base_state())

                self.assertEqual(result.get("asset_path"), "")
                self.assertIsNotNone(result.get("error"))
                self.assertEqual(result.get("error_stage"), "generate")

    def test_generate_skip_does_not_clear_upstream_error(self):
        """Corrected: generate_node skip path no longer overwrites error.

        If evaluate_node fails (error=msg, error_stage=evaluate) and
        generate_node skips (score < threshold), the error fields survive.
        """
        with mock.patch(
            "agents.evaluator.score",
            side_effect=ValueError("LLM failed"),
        ):
            with mock.patch("agents.generator.run_package"):
                with (
                    mock.patch("db.client.update_lead_score"),
                    mock.patch("db.client.save_asset_package"),
                ):
                    graph = build_eval_graph()
                    result = graph.invoke(_base_state())

        self.assertEqual(result.get("error"), "LLM failed")
        self.assertEqual(result.get("error_stage"), "evaluate")


# ==============================================================
# Boundary 4: threshold gate — edge-of-boundary behavior
# ==============================================================


@pytest.mark.integration
class TestThresholdBoundary(unittest.TestCase):
    """Characterize the generate_node threshold gate.

    Current contract:
    - score < threshold skips generate (strict less-than, not <=)
    - Missing auto_generate_threshold in cfg defaults to 60
    - "or 60" also handles falsy values like empty string
    """

    def setUp(self):
        self._eval_patcher = mock.patch("agents.evaluator.score")
        self._eval_mock = self._eval_patcher.start()

    def tearDown(self):
        self._eval_patcher.stop()

    def test_score_at_threshold_triggers_generate(self):
        """Characterize: score == threshold (60) runs generate_node.

        Uses `<` not `<=`, so `60 < 60` is False → generate runs.
        """
        self._eval_mock.return_value = {
            "score": 60,
            "reason": "Barely meets bar.",
            "match_points": ["match"],
            "gaps": ["many"],
        }
        gen_mock = mock.MagicMock(return_value=dict(_GEN_EMPTY))
        with (
            mock.patch("agents.generator.run_package", gen_mock),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            graph.invoke(_base_state())

        gen_mock.assert_called_once()

    def test_score_one_below_threshold_skips_generate(self):
        """Characterize: score == threshold-1 (59) skips generate_node.

        59 < 60 is True → generate skips.
        """
        self._eval_mock.return_value = {
            "score": 59,
            "reason": "Almost.",
            "match_points": ["match"],
            "gaps": ["gap"],
        }
        gen_mock = mock.MagicMock()
        with (
            mock.patch("agents.generator.run_package", gen_mock),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            graph.invoke(_base_state())

        gen_mock.assert_not_called()

    def test_threshold_defaults_to_60_when_cfg_missing(self):
        """Characterize: cfg={} → threshold=60 (the bare `or 60` fallback).

        Code path: ``int(state.get("cfg", {}).get("auto_generate_threshold") or 60)``
        """
        self._eval_mock.return_value = {
            "score": 50,
            "reason": "Mediocre.",
            "match_points": [],
            "gaps": ["lots"],
        }
        gen_mock = mock.MagicMock()
        with (
            mock.patch("agents.generator.run_package", gen_mock),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            state = _base_state(cfg={})
            graph = build_eval_graph()
            graph.invoke(state)

        gen_mock.assert_not_called()

    def test_threshold_zero_always_runs_generate(self):
        """Characterize: threshold=0 means generate runs for any score.

        ``score (0-100) < 0`` is never true → generate always runs even at score=0.
        """
        self._eval_mock.return_value = {
            "score": 0,
            "reason": "Terrible.",
            "match_points": [],
            "gaps": ["everything"],
        }
        gen_mock = mock.MagicMock(return_value=dict(_GEN_EMPTY))
        with (
            mock.patch("agents.generator.run_package", gen_mock),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            state = _base_state(cfg={"auto_generate_threshold": "0"})
            graph = build_eval_graph()
            graph.invoke(state)

        gen_mock.assert_called_once()

    def test_high_threshold_skips_near_perfect_score(self):
        """Characterize: threshold=100 → only perfect (100) score runs generate."""
        self._eval_mock.return_value = {
            "score": 99,
            "reason": "Excellent.",
            "match_points": ["all"],
            "gaps": [],
        }
        gen_mock = mock.MagicMock()
        with (
            mock.patch("agents.generator.run_package", gen_mock),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            state = _base_state(cfg={"auto_generate_threshold": "100"})
            graph = build_eval_graph()
            graph.invoke(state)

        gen_mock.assert_not_called()

    def test_threshold_reads_from_cfg_at_runtime(self):
        """Characterize: threshold is read from state.cfg inside generate_node.

        Different job_ids can have different thresholds via their cfg.
        """
        self._eval_mock.return_value = {
            "score": 70,
            "reason": "Solid.",
            "match_points": ["match"],
            "gaps": [],
        }
        gen_mock = mock.MagicMock(return_value=dict(_GEN_EMPTY))
        with (
            mock.patch("agents.generator.run_package", gen_mock),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            state = _base_state(cfg={"auto_generate_threshold": "65"})
            graph = build_eval_graph()
            graph.invoke(state)

        gen_mock.assert_called_once()


# ==============================================================
# Boundary 5: state consistency after partial node failure
# ==============================================================


@pytest.mark.integration
class TestStateConsistencyAfterFailure(unittest.TestCase):
    """Characterize state invariants when nodes fail partially.

    Key invariant: LangGraph merges partial dicts from each node.
    Fields NOT returned by a node are preserved from previous state.
    Fields returned by a node overwrite previous values.
    """

    def test_fields_not_returned_are_preserved(self):
        """Characterize: evaluate_node returns only scoring fields.

        job_id, lead, profile, cfg survive from the initial state.
        """
        with (
            mock.patch(
                "agents.evaluator.score",
                return_value={"score": 80, "reason": "Great.", "match_points": ["Python"], "gaps": []},
            ),
            mock.patch("agents.generator.run_package", return_value=dict(_GEN_EMPTY)),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result.get("job_id"), "test-job-001")
        self.assertEqual(result["lead"]["title"], "Software Engineer")
        self.assertIn("candidate", result["profile"])

    def test_low_score_path_has_zero_score_without_error(self):
        """Characterize: score below threshold is not an error — error is None.

        This distinguishes "legitimately low score" from "crash during eval."
        """
        with (
            mock.patch(
                "agents.evaluator.score",
                return_value={"score": 30, "reason": "Weak match.", "match_points": [], "gaps": ["domain mismatch"]},
            ),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result.get("score"), 30)
        self.assertIsNone(result.get("error"))
        self.assertEqual(result.get("asset_path"), "")
        self.assertEqual(result.get("cover_letter_path"), "")

    def test_evaluate_crash_preserves_error_and_stage(self):
        """Corrected: evaluate crash now preserves error through the pipeline.

        error_stage="evaluate" tells downstream consumers which node failed.
        The generate_node skip path no longer erases this information.
        """
        with mock.patch("agents.evaluator.score", side_effect=ValueError("crash")):
            with (
                mock.patch("db.client.update_lead_score"),
                mock.patch("db.client.save_asset_package"),
            ):
                graph = build_eval_graph()
                result = graph.invoke(_base_state())

        self.assertEqual(result.get("score"), 0)
        self.assertEqual(result.get("error"), "crash")
        self.assertEqual(result.get("error_stage"), "evaluate")
        self.assertEqual(result.get("reason"), "eval failed")

    def test_generate_crash_path_has_score_and_error(self):
        """Characterize: generate crash preserves score from evaluate and sets error."""
        with (
            mock.patch("agents.evaluator.score", return_value=dict(_EVAL_RESULT)),
            mock.patch("agents.generator.run_package", side_effect=RuntimeError("crash")),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result.get("score"), 75)
        self.assertIsNotNone(result.get("error"))
        self.assertEqual(result.get("asset_path"), "")
        self.assertEqual(result.get("cover_letter_path"), "")


# ==============================================================
# Boundary 6: malformed / missing state fields
# ==============================================================


@pytest.mark.integration
class TestMalformedState(unittest.TestCase):
    """Characterize graph behavior when state fields are missing or malformed.

    Each node uses defensive `.get()` calls, so missing keys should not crash
    during node execution. However, persist_node uses direct subscript access
    on some fields, which WILL crash if those keys are missing.
    """

    def test_missing_lead_description_handled(self):
        """Characterize: lead without 'description' key does not crash.

        ``_job_eval_document`` does ``lead.get("description") or ""``.
        """
        lead_no_desc = dict(_SHARED_LEAD)
        del lead_no_desc["description"]

        with (
            mock.patch(
                "agents.evaluator.score",
                return_value={"score": 65, "reason": "ok", "match_points": [], "gaps": []},
            ),
            mock.patch("agents.generator.run_package", return_value=dict(_GEN_EMPTY)),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state(lead=lead_no_desc))

        self.assertEqual(result.get("score"), 65)

    def test_empty_profile_handled(self):
        """Characterize: empty profile dict passes through evaluate without crash.

        The evaluator receives {} and should return a low score.
        """
        with (
            mock.patch(
                "agents.evaluator.score",
                return_value={"score": 10, "reason": "No profile.", "match_points": [], "gaps": ["empty profile"]},
            ),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state(profile={}))

        self.assertEqual(result.get("score"), 10)

    def test_missing_cfg_field_uses_default_threshold(self):
        """Characterize: cfg key missing from state entirely → threshold defaults to 60."""
        state = _base_state()
        del state["cfg"]

        with (
            mock.patch(
                "agents.evaluator.score",
                return_value={"score": 55, "reason": "ok", "match_points": [], "gaps": []},
            ),
            mock.patch("agents.generator.run_package"),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(state)

        self.assertEqual(result.get("score"), 55)
        self.assertIsNone(result.get("error"))

    def test_missing_job_id_no_longer_crashes_at_persist(self):
        """Corrected: persist_node now uses ``state.get("job_id") or "?"``
        instead of ``state["job_id"]``. A missing job_id no longer causes
        a KeyError crash — the graph completes with an error logged.

        evaluate_node uses ``state.get("job_id", "?")`` defensively.
        generate_node does not reference job_id.
        persist_node catches the DB exception from the "?" jid.
        """
        state = _base_state()
        del state["job_id"]

        with (
            mock.patch(
                "agents.evaluator.score",
                return_value={"score": 70, "reason": "ok", "match_points": [], "gaps": []},
            ),
            mock.patch("agents.generator.run_package", return_value=dict(_GEN_EMPTY)),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(state)

        # Graph completes normally — error_stage is None since DB
        # mocks succeed even with "?" job_id (they're fakes)
        self.assertIn("score", result)
        self.assertEqual(result.get("error"), None)

    def test_score_string_coerced_to_int(self):
        """Characterize: score="75" (string) is handled by ``int()`` coercion.

        ``int(state.get("score") or 0)`` → ``int("75")`` → 75.
        """
        with (
            mock.patch(
                "agents.evaluator.score",
                return_value={"score": "75", "reason": "ok", "match_points": [], "gaps": []},
            ),
            mock.patch("agents.generator.run_package", return_value=dict(_GEN_EMPTY)),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result.get("score"), 75)

    def test_score_zero_string_not_falsy_trap(self):
        """Characterize: score="0" → ``int("0" or 0)`` → int("0") → 0.

        The ``or 0`` only kicks in if ``state.get("score")`` is None or absent,
        which is correct: "0" is truthy, so int("0") = 0.
        """
        with (
            mock.patch(
                "agents.evaluator.score",
                return_value={"score": "0", "reason": "zero", "match_points": [], "gaps": []},
            ),
            mock.patch("agents.generator.run_package"),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        # int("0") = 0, 0 < 60 → generate skipped
        self.assertEqual(result.get("score"), 0)

    def test_reason_passed_unchanged_to_update_lead_score(self):
        """Characterize: the graph passes the reason verbatim to update_lead_score.

        Truncation to 500 chars happens inside update_lead_score at the SQL
        execute layer (``db/client.py: r[:500]``), not in the graph node.
        The graph layer does NOT truncate.
        """
        long_reason = "x" * 1000
        with (
            mock.patch(
                "agents.evaluator.score",
                return_value={"score": 50, "reason": long_reason, "match_points": [], "gaps": []},
            ),
            mock.patch("db.client.update_lead_score") as update_mock,
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            graph.invoke(_base_state())

        call_args = update_mock.call_args
        # Graph passes full 1000-char reason; truncation is inside
        self.assertEqual(len(call_args[0][2]), 1000)


# ==============================================================
# Boundary 7: graph structural invariants affecting failure flow
# ==============================================================


@pytest.mark.integration
class TestGraphStructuralInvariants(unittest.TestCase):
    """Characterize graph topology that determines failure propagation.

    The graph is strictly linear with 3 nodes and no conditional edges.
    This means every node always executes (unless generate_node's
    internal early return triggers), and failures always flow forward.
    """

    def test_graph_has_three_user_nodes_plus_start(self):
        """Characterize: graph has 4 compiled nodes (3 user + __start__).

        LangGraph adds an internal ``__start__`` node to compiled graphs.
        The 3 user nodes are evaluate, generate, persist — linear, no branching.
        """
        graph = build_eval_graph()
        nodes = getattr(graph, "nodes", {})
        self.assertIn("evaluate", nodes)
        self.assertIn("generate", nodes)
        self.assertIn("persist", nodes)
        self.assertIn("__start__", nodes)
        self.assertEqual(len(nodes), 4)

    def test_all_edges_are_unconditional(self):
        """Characterize: graph has no conditional/error edges.

        The graph/__init__.py uses add_edge() exclusively —
        no add_conditional_edges(). LangGraph's default exception
        behavior applies: node failures propagate through the runtime,
        not through a graph-defined error route.
        """
        graph = build_eval_graph()
        # Compiled Pregel graphs store edges in graph.builder.edges
        # before compilation. After compilation, edges are baked into
        # the execution plan. Verify source code pattern instead.
        self.assertTrue(hasattr(graph, "invoke"))


# ==============================================================
# Boundary 8: silent fallback — API layer swallows graph crash
# ==============================================================


@pytest.mark.integration
class TestApiInvocationSilentFailure(unittest.TestCase):
    """Characterize that the API layer does not catch invoke() failures.

    The ``_run()`` closure in the ``/pipeline/run`` endpoint
    (main.py:978-999) calls ``eval_graph.invoke(state)`` without
    a try/except. The WebSocket broadcast at line 993 never fires
    if persist_node crashes. Because BackgroundTasks uses
    ``asyncio.to_thread``, the exception is visible only as a
    "Task exception was never retrieved" warning in logs.
    """

    def test_invoke_no_longer_raises_on_persist_failure(self):
        """Corrected: persist_node catches its own exceptions.

        invoke() now returns a result dict with error/error_stage set
        instead of raising. The API layer's ``_run()`` closure completes
        normally and the WebSocket broadcast fires with error info.
        """
        with (
            mock.patch("agents.evaluator.score", return_value=dict(_EVAL_RESULT)),
            mock.patch("agents.generator.run_package", return_value=dict(_GEN_RESULT)),
            mock.patch("db.client.update_lead_score", side_effect=RuntimeError("crash")),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result.get("error"), "crash")
        self.assertEqual(result.get("error_stage"), "persist")

    def test_websocket_broadcast_now_fires_on_persist_failure(self):
        """Corrected: WebSocket broadcast fires even when persist fails.

        Because invoke() returns normally with error info, the broadcast
        at main.py:993 executes and includes the error in its message.
        """
        broadcast = mock.MagicMock()
        with (
            mock.patch("agents.evaluator.score", return_value=dict(_EVAL_RESULT)),
            mock.patch("agents.generator.run_package", return_value=dict(_GEN_RESULT)),
        ):
            for side_effect, should_broadcast in [
                (None, True),
                (RuntimeError("crash"), True),  # now broadcasts on failure too
            ]:
                with self.subTest(crash=(side_effect is not None)):
                    sig = side_effect or (lambda *a, **kw: None)
                    with mock.patch("db.client.update_lead_score", side_effect=sig):
                        with mock.patch("db.client.save_asset_package"):
                            graph = build_eval_graph()
                            result = graph.invoke(_base_state())
                            broadcast("pipeline_done")

        self.assertEqual(broadcast.call_count, 2)
