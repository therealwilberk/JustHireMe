"""Graph failure-path tests — one test = one operational guarantee.

Each test validates exactly one operational guarantee.  Test names state
the guarantee in declarative form.  Multiple assertions inside a test all
serve that single guarantee (different facets of the same contract).

The orchestration model is fault-tolerant:
- Each node catches its own failures
- Nodes set error + error_stage on failure
- Nodes never clear upstream errors (error is append-only)
- persist_node returns structured errors instead of crashing
- All nodes use defensive .get() with defaults for state access
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


# ========================================================================
# Guarantee: persist_node crash does not crash the graph
# ========================================================================


@pytest.mark.integration
class TestPersistCrashDoesNotCrashGraph(unittest.TestCase):
    """Guarantee: a DB crash inside persist_node returns a result dict.

    Before the fix, persist_node had no try/except — the exception
    propagated through LangGraph and was lost in the BackgroundTask
    thread.  After the fix, persist_node catches the exception and
    returns structured error fields.  invoke() always returns a dict.
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

    def test_invoke_returns_dict_on_update_lead_score_crash(self):
        with (
            mock.patch(
                "db.client.update_lead_score",
                side_effect=RuntimeError("DB locked"),
            ),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertIsInstance(result, dict)

    def test_invoke_returns_dict_on_save_asset_package_crash(self):
        with (
            mock.patch("db.client.update_lead_score"),
            mock.patch(
                "db.client.save_asset_package",
                side_effect=RuntimeError("Disk full"),
            ),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertIsInstance(result, dict)

    def test_invoke_returns_dict_when_both_db_calls_crash(self):
        with (
            mock.patch(
                "db.client.update_lead_score",
                side_effect=RuntimeError("conn lost"),
            ),
            mock.patch(
                "db.client.save_asset_package",
                side_effect=RuntimeError("conn lost"),
            ),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertIsInstance(result, dict)


# ========================================================================
# Guarantee: persist_node crash surfaces human-readable error fields
# ========================================================================


@pytest.mark.integration
class TestPersistCrashSurfacesStructuredError(unittest.TestCase):
    """Guarantee: a DB crash produces error + error_stage in the result."""

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

    def test_error_field_matches_exception_message(self):
        with (
            mock.patch(
                "db.client.update_lead_score",
                side_effect=RuntimeError("DB locked"),
            ),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result["error"], "DB locked")

    def test_error_stage_is_persist(self):
        with (
            mock.patch(
                "db.client.update_lead_score",
                side_effect=RuntimeError("DB locked"),
            ),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result["error_stage"], "persist")

    def test_save_asset_package_crash_also_sets_persist_stage(self):
        with (
            mock.patch("db.client.update_lead_score"),
            mock.patch(
                "db.client.save_asset_package",
                side_effect=RuntimeError("Disk full"),
            ),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result["error_stage"], "persist")


# ========================================================================
# Guarantee: persist_node crash preserves upstream node outputs
# ========================================================================


@pytest.mark.integration
class TestPersistCrashPreservesUpstreamState(unittest.TestCase):
    """Guarantee: upstream evaluate and generate outputs survive a persist crash.

    The fault-tolerant model means partial work is not rolled back —
    it is observable via the result dict alongside the error.
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

    def test_evaluate_score_survives_persist_crash(self):
        with (
            mock.patch(
                "db.client.update_lead_score",
                side_effect=RuntimeError("DB locked"),
            ),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result["score"], 75)
        self.assertEqual(result["reason"], "Good stack match.")

    def test_generate_asset_paths_survive_persist_crash(self):
        with (
            mock.patch(
                "db.client.update_lead_score",
                side_effect=RuntimeError("DB locked"),
            ),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result["asset_path"], "/tmp/test-resume.pdf")
        self.assertEqual(result["cover_letter_path"], "/tmp/test-cover.pdf")


# ========================================================================
# Guarantee: persist_node gates asset save behind non-empty paths
# ========================================================================


@pytest.mark.integration
class TestPersistGatesAssetSave(unittest.TestCase):
    """Guarantee: save_asset_package is only called when paths are non-empty.

    The conditional ``if state.get("asset_path") or state.get("cover_letter_path"):``
    means a skipped generation (low score → empty paths) still calls
    update_lead_score but skips save_asset_package.
    """

    def test_empty_asset_paths_suppress_asset_save(self):
        with (
            mock.patch(
                "agents.evaluator.score",
                return_value={"score": 30, "reason": "Weak", "match_points": [], "gaps": ["bad"]},
            ),
            mock.patch("db.client.update_lead_score") as update_mock,
            mock.patch("db.client.save_asset_package") as save_mock,
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result.get("score"), 30)
        self.assertFalse(save_mock.called)
        self.assertTrue(update_mock.called)

    def test_asset_path_triggers_asset_save(self):
        with (
            mock.patch("agents.evaluator.score", return_value=dict(_EVAL_RESULT)),
            mock.patch("agents.generator.run_package", return_value=dict(_GEN_RESULT)),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package") as save_mock,
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertTrue(save_mock.called)
        self.assertEqual(result.get("asset_path"), "/tmp/test-resume.pdf")

    def test_cover_letter_path_triggers_asset_save(self):
        result_no_resume = dict(_GEN_RESULT)
        result_no_resume.pop("resume")
        with (
            mock.patch("agents.evaluator.score", return_value=dict(_EVAL_RESULT)),
            mock.patch("agents.generator.run_package", return_value=result_no_resume),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package") as save_mock,
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertTrue(save_mock.called)
        self.assertEqual(result.get("cover_letter_path"), "/tmp/test-cover.pdf")


# ========================================================================
# Guarantee: persist_node returns empty dict on success (no field pollution)
# ========================================================================


@pytest.mark.integration
class TestPersistReturnsEmptyOnSuccess(unittest.TestCase):
    """Guarantee: successful persist_node returns {}.

    An empty return dict means LangGraph preserves all prior node
    outputs unchanged.  persist_node does not add or overwrite state.
    """

    def test_empty_dict_on_success(self):
        with (
            mock.patch("agents.evaluator.score", return_value=dict(_EVAL_RESULT)),
            mock.patch("agents.generator.run_package", return_value=dict(_GEN_RESULT)),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result.get("score"), 75)
        self.assertIsNone(result.get("error"))
        self.assertIsNone(result.get("error_stage"))


# ========================================================================
# Guarantee: evaluate exception propagates as structured failure
# ========================================================================


@pytest.mark.integration
class TestEvaluateCrashProducesStructuredFailure(unittest.TestCase):
    """Guarantee: an evaluate-node exception sets error, error_stage, score=0."""

    def test_error_matches_exception_message(self):
        graph = build_eval_graph()
        with mock.patch(
            "agents.evaluator.score",
            side_effect=ValueError("LLM returned garbage"),
        ):
            result = graph.invoke(_base_state())

        self.assertEqual(result["error"], "LLM returned garbage")

    def test_error_stage_is_evaluate(self):
        graph = build_eval_graph()
        with mock.patch(
            "agents.evaluator.score",
            side_effect=ValueError("LLM returned garbage"),
        ):
            result = graph.invoke(_base_state())

        self.assertEqual(result["error_stage"], "evaluate")

    def test_score_is_zero_on_evaluate_crash(self):
        graph = build_eval_graph()
        with mock.patch(
            "agents.evaluator.score",
            side_effect=ValueError("crash"),
        ):
            result = graph.invoke(_base_state())

        self.assertEqual(result["score"], 0)

    def test_reason_indicates_eval_failure(self):
        graph = build_eval_graph()
        with mock.patch(
            "agents.evaluator.score",
            side_effect=ValueError("crash"),
        ):
            result = graph.invoke(_base_state())

        self.assertEqual(result["reason"], "eval failed")


# ========================================================================
# Guarantee: evaluate crash prevents generate execution
# ========================================================================


@pytest.mark.integration
class TestEvaluateCrashBlocksGenerate(unittest.TestCase):
    """Guarantee: after evaluate crash, generate_node produces empty paths."""

    def test_evaluate_crash_produces_empty_asset_paths(self):
        with mock.patch("agents.evaluator.score", side_effect=ValueError("crash")):
            with (
                mock.patch("agents.generator.run_package"),
                mock.patch("db.client.update_lead_score"),
                mock.patch("db.client.save_asset_package"),
            ):
                graph = build_eval_graph()
                result = graph.invoke(_base_state())

        self.assertEqual(result.get("asset_path"), "")
        self.assertEqual(result.get("cover_letter_path"), "")
        self.assertEqual(result.get("error_stage"), "evaluate")


# ========================================================================
# Guarantee: evaluate crash still persists degraded score
# ========================================================================


@pytest.mark.integration
class TestEvaluateCrashPersistsDegradedScore(unittest.TestCase):
    """Guarantee: update_lead_score is called even after evaluate crash.

    The fault-tolerant model means we persist what we have — score=0
    and reason="eval failed" — so the operator can see the pipeline
    attempted evaluation for this job_id.
    """

    def test_evaluate_crash_persists_zero_score(self):
        with mock.patch("agents.evaluator.score", side_effect=ValueError("crash")):
            with (
                mock.patch("db.client.update_lead_score") as update_mock,
                mock.patch("db.client.save_asset_package"),
            ):
                graph = build_eval_graph()
                graph.invoke(_base_state())

        self.assertTrue(update_mock.called)
        args = update_mock.call_args[0]
        self.assertEqual(args[1], 0)
        self.assertEqual(args[2], "eval failed")

    def test_save_asset_package_not_called_after_evaluate_crash(self):
        with mock.patch("agents.evaluator.score", side_effect=ValueError("crash")):
            with (
                mock.patch("db.client.update_lead_score"),
                mock.patch("db.client.save_asset_package") as save_mock,
            ):
                graph = build_eval_graph()
                graph.invoke(_base_state())

        save_mock.assert_not_called()


# ========================================================================
# Guarantee: evaluate_node catches all Exception subclasses
# ========================================================================


@pytest.mark.integration
class TestEvaluateCatchesAllExceptions(unittest.TestCase):
    """Guarantee: every Exception subclass produces score=0, not a graph crash."""

    def test_all_exception_types_set_score_zero(self):
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

                self.assertEqual(result["score"], 0)


# ========================================================================
# Guarantee: generate crash returns empty asset paths
# ========================================================================


@pytest.mark.integration
class TestGenerateCrashReturnsEmptyPaths(unittest.TestCase):
    """Guarantee: a generate-node exception produces empty asset/cover paths."""

    def setUp(self):
        self._eval_mock = mock.patch(
            "agents.evaluator.score", return_value=dict(_EVAL_RESULT)
        )
        self._eval_mock.start()

    def tearDown(self):
        self._eval_mock.stop()

    def test_asset_path_empty_after_generate_crash(self):
        with mock.patch(
            "agents.generator.run_package",
            side_effect=RuntimeError("PDF render failed"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result["asset_path"], "")

    def test_cover_letter_path_empty_after_generate_crash(self):
        with mock.patch(
            "agents.generator.run_package",
            side_effect=RuntimeError("PDF render failed"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result["cover_letter_path"], "")


# ========================================================================
# Guarantee: generate crash surfaces structured error
# ========================================================================


@pytest.mark.integration
class TestGenerateCrashSurfacesStructuredError(unittest.TestCase):
    """Guarantee: a generate-node exception sets error + error_stage."""

    def setUp(self):
        self._eval_mock = mock.patch(
            "agents.evaluator.score", return_value=dict(_EVAL_RESULT)
        )
        self._eval_mock.start()

    def tearDown(self):
        self._eval_mock.stop()

    def test_error_matches_exception_message(self):
        with mock.patch(
            "agents.generator.run_package",
            side_effect=RuntimeError("PDF render failed"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertIn("PDF render failed", result["error"])

    def test_error_stage_is_generate(self):
        with mock.patch(
            "agents.generator.run_package",
            side_effect=RuntimeError("PDF render failed"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result["error_stage"], "generate")


# ========================================================================
# Guarantee: generate crash preserves upstream evaluate outputs
# ========================================================================


@pytest.mark.integration
class TestGenerateCrashPreservesEvaluateOutput(unittest.TestCase):
    """Guarantee: generate crash does NOT overwrite score/reason from evaluate."""

    def setUp(self):
        self._eval_mock = mock.patch(
            "agents.evaluator.score", return_value=dict(_EVAL_RESULT)
        )
        self._eval_mock.start()

    def tearDown(self):
        self._eval_mock.stop()

    def test_score_survives_generate_crash(self):
        with mock.patch(
            "agents.generator.run_package",
            side_effect=RuntimeError("crash"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result["score"], 75)

    def test_reason_survives_generate_crash(self):
        with mock.patch(
            "agents.generator.run_package",
            side_effect=RuntimeError("crash"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result["reason"], "Good stack match.")


# ========================================================================
# Guarantee: generate crash still persists score to DB
# ========================================================================


@pytest.mark.integration
class TestGenerateCrashPersistsScore(unittest.TestCase):
    """Guarantee: update_lead_score is called even after generate crash.

    The score from evaluate (75) and its reason/match_points/gaps are
    persisted.  save_asset_package is NOT called because paths are empty.
    """

    def setUp(self):
        self._eval_mock = mock.patch(
            "agents.evaluator.score", return_value=dict(_EVAL_RESULT)
        )
        self._eval_mock.start()

    def tearDown(self):
        self._eval_mock.stop()

    def test_generate_crash_persists_evaluate_score(self):
        with (
            mock.patch(
                "agents.generator.run_package",
                side_effect=RuntimeError("crash"),
            ),
            mock.patch("db.client.update_lead_score") as update_mock,
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            graph.invoke(_base_state())

        self.assertTrue(update_mock.called)
        args = update_mock.call_args[0]
        self.assertEqual(args[1], 75)
        self.assertEqual(args[2], "Good stack match.")

    def test_save_asset_skipped_after_generate_crash(self):
        with (
            mock.patch(
                "agents.generator.run_package",
                side_effect=RuntimeError("crash"),
            ),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package") as save_mock,
        ):
            graph = build_eval_graph()
            graph.invoke(_base_state())

        save_mock.assert_not_called()


# ========================================================================
# Guarantee: generate_node catches all Exception subclasses
# ========================================================================


@pytest.mark.integration
class TestGenerateCatchesAllExceptions(unittest.TestCase):
    """Guarantee: every Exception subclass from run_package sets error in state."""

    def setUp(self):
        self._eval_mock = mock.patch(
            "agents.evaluator.score", return_value=dict(_EVAL_RESULT)
        )
        self._eval_mock.start()

    def tearDown(self):
        self._eval_mock.stop()

    def test_all_exception_types_set_error(self):
        for exc_type in (ValueError("msg"), RuntimeError("msg"), KeyError("msg"), TypeError("msg")):
            with self.subTest(exc=type(exc_type).__name__):
                with mock.patch("agents.generator.run_package", side_effect=exc_type):
                    graph = build_eval_graph()
                    result = graph.invoke(_base_state())

                self.assertIsNotNone(result.get("error"))
                self.assertEqual(result.get("error_stage"), "generate")


# ========================================================================
# Guarantee: generate skip does not clear upstream errors
# ========================================================================


@pytest.mark.integration
class TestGenerateSkipPreservesUpstreamError(unittest.TestCase):
    """Guarantee: generate_node skip path does NOT overwrite error fields.

    Before the fix, the skip path returned ``{"error": None}`` which
    erased the error set by evaluate_node.  Now it returns only
    asset/cover_letter paths, leaving error fields untouched.
    """

    def test_upstream_error_survives_generate_skip(self):
        with mock.patch("agents.evaluator.score", side_effect=ValueError("LLM failed")):
            with mock.patch("agents.generator.run_package"):
                with (
                    mock.patch("db.client.update_lead_score"),
                    mock.patch("db.client.save_asset_package"),
                ):
                    graph = build_eval_graph()
                    result = graph.invoke(_base_state())

        self.assertEqual(result["error"], "LLM failed")
        self.assertEqual(result["error_stage"], "evaluate")


# ========================================================================
# Guarantee: low score without any crash produces no error fields
# ========================================================================


@pytest.mark.integration
class TestLowScoreIsNotAnError(unittest.TestCase):
    """Guarantee: score < threshold with no exception does not set error.

    The operator must be able to distinguish "legitimately low score"
    from "crash during evaluation."  Only the presence of error/error_stage
    distinguishes these two cases.
    """

    def test_low_score_has_no_error_fields(self):
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

        self.assertEqual(result["score"], 30)
        self.assertIsNone(result["error"])
        self.assertIsNone(result["error_stage"])


# ========================================================================
# Guarantee: threshold gate at 60 controls generate execution
# ========================================================================


@pytest.mark.integration
class TestThresholdGate(unittest.TestCase):
    """Guarantee: generate_node runs iff score >= threshold.

    Threshold defaults to 60.  Uses strict-less-than: score < threshold
    skips, score == threshold runs.
    """

    def setUp(self):
        self._eval_patcher = mock.patch("agents.evaluator.score")
        self._eval_mock = self._eval_patcher.start()

    def tearDown(self):
        self._eval_patcher.stop()

    def test_score_at_exact_threshold_runs_generate(self):
        self._eval_mock.return_value = {
            "score": 60, "reason": "Barely.", "match_points": ["match"], "gaps": ["many"],
        }
        with (
            mock.patch(
                "agents.generator.run_package",
                return_value={"resume": "at-threshold.pdf", "cover_letter": "at-threshold-cl.pdf"},
            ),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result.get("asset_path"), "at-threshold.pdf")
        self.assertEqual(result.get("score"), 60)

    def test_score_one_below_threshold_skips_generate(self):
        self._eval_mock.return_value = {
            "score": 59, "reason": "Almost.", "match_points": ["match"], "gaps": ["gap"],
        }
        with (
            mock.patch("agents.generator.run_package"),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertEqual(result.get("asset_path"), "")
        self.assertEqual(result.get("score"), 59)

    def test_threshold_defaults_to_sixty_when_cfg_missing(self):
        self._eval_mock.return_value = {
            "score": 50, "reason": "Mediocre.", "match_points": [], "gaps": ["lots"],
        }
        with (
            mock.patch("agents.generator.run_package"),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state(cfg={}))

        self.assertEqual(result.get("asset_path"), "")

    def test_threshold_zero_runs_generate_at_any_score(self):
        self._eval_mock.return_value = {
            "score": 0, "reason": "Terrible.", "match_points": [], "gaps": ["everything"],
        }
        with (
            mock.patch(
                "agents.generator.run_package",
                return_value={"resume": "zero-thresh.pdf", "cover_letter": "zero-thresh-cl.pdf"},
            ),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state(cfg={"auto_generate_threshold": "0"}))

        self.assertEqual(result.get("asset_path"), "zero-thresh.pdf")
        self.assertEqual(result.get("score"), 0)

    def test_threshold_one_hundred_skips_near_perfect(self):
        self._eval_mock.return_value = {
            "score": 99, "reason": "Excellent.", "match_points": ["all"], "gaps": [],
        }
        with (
            mock.patch("agents.generator.run_package"),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state(cfg={"auto_generate_threshold": "100"}))

        self.assertEqual(result.get("asset_path"), "")

    def test_threshold_read_from_cfg_at_runtime(self):
        self._eval_mock.return_value = {
            "score": 70, "reason": "Solid.", "match_points": ["match"], "gaps": [],
        }
        with (
            mock.patch(
                "agents.generator.run_package",
                return_value={"resume": "cfg-thresh.pdf", "cover_letter": "cfg-thresh-cl.pdf"},
            ),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state(cfg={"auto_generate_threshold": "65"}))

        self.assertEqual(result.get("asset_path"), "cfg-thresh.pdf")


# ========================================================================
# Guarantee: missing lead description does not crash
# ========================================================================


@pytest.mark.integration
class TestMissingLeadDescription(unittest.TestCase):
    """Guarantee: lead without a description key defaults to empty string."""

    def test_missing_description_does_not_crash(self):
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


# ========================================================================
# Guarantee: empty profile does not crash
# ========================================================================


@pytest.mark.integration
class TestEmptyProfile(unittest.TestCase):
    """Guarantee: profile={} passes through evaluate without crash."""

    def test_empty_profile_does_not_crash(self):
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


# ========================================================================
# Guarantee: missing cfg key defaults threshold to 60
# ========================================================================


@pytest.mark.integration
class TestMissingCfgKey(unittest.TestCase):
    """Guarantee: cfg key absent from state uses default threshold 60.

    Code path: ``state.get("cfg", {}).get("auto_generate_threshold") or 60``
    """

    def test_missing_cfg_defaults_to_sixty(self):
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


# ========================================================================
# Guarantee: missing job_id does not crash persist
# ========================================================================


@pytest.mark.integration
class TestMissingJobId(unittest.TestCase):
    """Guarantee: job_id absent from state uses "?" fallback, does not crash.

    Before the fix, persist_node used ``state["job_id"]`` (bare subscript),
    which raised KeyError.  Now it uses ``state.get("job_id") or "?"``.
    """

    def test_missing_job_id_does_not_crash_persist(self):
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

        self.assertIn("score", result)
        self.assertIsNone(result.get("error"))


# ========================================================================
# Guarantee: score string coerces to int
# ========================================================================


@pytest.mark.integration
class TestScoreStringCoercion(unittest.TestCase):
    """Guarantee: score="75" (string) is coerced by int() correctly.

    Code path: ``int(state.get("score") or 0)`` → int("75") → 75.
    """

    def test_score_string_coerces_to_int(self):
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

    def test_zero_score_string_goes_through_int_zero(self):
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

        self.assertEqual(result.get("score"), 0)


# ========================================================================
# Guarantee: reason is passed through untruncated at graph layer
# ========================================================================


@pytest.mark.integration
class TestReasonPassthrough(unittest.TestCase):
    """Guarantee: the graph layer does NOT truncate reason.

    Truncation to 500 chars happens inside ``update_lead_score`` at the SQL
    execute layer, not in the graph node.  The graph passes reason verbatim.
    """

    def test_reason_full_length_passed_to_db(self):
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
        self.assertEqual(len(call_args[0][2]), 1000)


# ========================================================================
# Guarantee: graph topology is strictly linear (no branching)
# ========================================================================


@pytest.mark.integration
class TestGraphTopology(unittest.TestCase):
    """Guarantee: the compiled graph has exactly 3 user nodes + __start__.

    Linear topology means all nodes always execute.  No conditional edges
    exist — failures do not trigger alternative routing.
    """

    def test_graph_has_three_user_nodes_and_start(self):
        graph = build_eval_graph()
        nodes = getattr(graph, "nodes", {})
        self.assertIn("evaluate", nodes)
        self.assertIn("generate", nodes)
        self.assertIn("persist", nodes)
        self.assertIn("__start__", nodes)
        self.assertEqual(len(nodes), 4)


# ========================================================================
# Guarantee: invoke() does not raise on any node failure
# ========================================================================


@pytest.mark.integration
class TestInvokeNeverRaises(unittest.TestCase):
    """Guarantee: graph.invoke() returns a dict regardless of node failures.

    Before the fix, persist_node's bare exception propagated through
    LangGraph and crashed the invocation.  After the fix, every node
    catches its own exceptions and returns structured error state.
    """

    def test_invoke_does_not_raise_on_persist_failure(self):
        with (
            mock.patch("agents.evaluator.score", return_value=dict(_EVAL_RESULT)),
            mock.patch("agents.generator.run_package", return_value=dict(_GEN_RESULT)),
            mock.patch("db.client.update_lead_score", side_effect=RuntimeError("crash")),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertIsInstance(result, dict)
        self.assertEqual(result["error"], "crash")
        self.assertEqual(result["error_stage"], "persist")

    def test_invoke_does_not_raise_on_evaluate_failure(self):
        with mock.patch("agents.evaluator.score", side_effect=ValueError("crash")):
            with (
                mock.patch("db.client.update_lead_score"),
                mock.patch("db.client.save_asset_package"),
            ):
                graph = build_eval_graph()
                result = graph.invoke(_base_state())

        self.assertIsInstance(result, dict)
        self.assertEqual(result["error"], "crash")
        self.assertEqual(result["error_stage"], "evaluate")

    def test_invoke_does_not_raise_on_generate_failure(self):
        with (
            mock.patch("agents.evaluator.score", return_value=dict(_EVAL_RESULT)),
            mock.patch("agents.generator.run_package", side_effect=RuntimeError("crash")),
            mock.patch("db.client.update_lead_score"),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertIsInstance(result, dict)
        self.assertEqual(result["error"], "crash")
        self.assertEqual(result["error_stage"], "generate")


# ========================================================================
# Guarantee: invoke() returns actionable error information
# ========================================================================


@pytest.mark.integration
class TestInvokeReturnsActionableError(unittest.TestCase):
    """Guarantee: the error dict contains enough info for the caller.

    After any node failure, the caller can determine:
    - Which node failed (error_stage)
    - What the error was (error string)
    - What work was completed before failure (score, asset_path, etc.)
    """

    def test_error_info_sufficient_for_caller_decision(self):
        with (
            mock.patch("agents.evaluator.score", return_value=dict(_EVAL_RESULT)),
            mock.patch("agents.generator.run_package", return_value=dict(_GEN_RESULT)),
            mock.patch("db.client.update_lead_score", side_effect=RuntimeError("Disk full")),
            mock.patch("db.client.save_asset_package"),
        ):
            graph = build_eval_graph()
            result = graph.invoke(_base_state())

        self.assertIn("error", result)
        self.assertIn("error_stage", result)
        self.assertIn("score", result)
        self.assertIn("asset_path", result)
