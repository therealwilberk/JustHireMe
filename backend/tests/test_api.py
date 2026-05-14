import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import pytest

# ── Must run before any backend module is imported ───────────────────────────
# Use a real temporary SQLite DB instead of faking sqlite3
_TEST_DB_DIR = tempfile.mkdtemp(prefix="jhm_test_")
os.environ["JHM_APP_DATA_DIR"] = _TEST_DB_DIR
os.makedirs(_TEST_DB_DIR, exist_ok=True)

from tests.fakes import _install_storage_fakes

_install_storage_fakes(use_real_sqlite=True)

# ── Import app and override the randomly-generated token ────────────────────
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

main._API_TOKEN = "test-token-abc123"
# Also propagate to the actual module ws.py imports from (copied at import time)
from routes import ws as _ws
_ws._API_TOKEN = "test-token-abc123"

from main import app  # noqa: E402  (same cached module, just for IDE clarity)

CLIENT = TestClient(app, raise_server_exceptions=False)
AUTH = {"Authorization": "Bearer test-token-abc123"}
NO_AUTH: dict = {}

# ── Seed helpers — insert test data into the real SQLite DB ─────────────────
from db.client import get_sql_connection  # noqa: E402

_SEEDED_LEADS: list[str] = []


def _seed_lead(overrides: dict | None = None) -> str:
    data = {
        "job_id": "test-seed-" + str(len(_SEEDED_LEADS) + 1),
        "title": "Software Engineer",
        "company": "Acme",
        "url": "https://example.com/job/001",
        "platform": "remoteok",
        "description": "Python and FastAPI role.",
        "kind": "job",
    }
    data.update(overrides or {})
    c = get_sql_connection()
    c.execute(
        """INSERT OR REPLACE INTO leads
           (job_id, title, company, url, platform, description, kind)
           VALUES (?,?,?,?,?,?,?)""",
        (data["job_id"], data["title"], data["company"],
         data["url"], data["platform"], data["description"], data["kind"]),
    )
    c.commit()
    c.close()
    _SEEDED_LEADS.append(data["job_id"])
    return data["job_id"]


def _seed_setting(key: str, val: str) -> None:
    c = get_sql_connection()
    c.execute("INSERT OR REPLACE INTO settings(key,val) VALUES(?,?)", (key, val))
    c.commit()
    c.close()


# ── Contract assertion helpers (re-exported from conftest) ──────────────────
from conftest import (
    assert_all_dict_items,
    assert_all_str_items,
    assert_csv_response,
    assert_detail_contains,
    assert_detail_error,
    assert_detail_exactly,
    assert_error_response,
    assert_list_response,
    assert_ok_response,
    assert_success_response,
    assert_timestamp_iso8601,
    assert_validation_error,
)

# ── Request helpers ───────────────────────────────────────────────────────────

def get(path, *, auth=True, **kwargs):
    headers = AUTH if auth else NO_AUTH
    return CLIENT.get(path, headers=headers, **kwargs)


def post(path, *, auth=True, json=None, **kwargs):
    headers = AUTH if auth else NO_AUTH
    return CLIENT.post(path, headers=headers, json=json, **kwargs)


def put(path, *, auth=True, json=None, **kwargs):
    headers = AUTH if auth else NO_AUTH
    return CLIENT.put(path, headers=headers, json=json, **kwargs)


def delete(path, *, auth=True, **kwargs):
    headers = AUTH if auth else NO_AUTH
    return CLIENT.delete(path, headers=headers, **kwargs)


# ── Test classes ─────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestAuthGate(unittest.TestCase):
    def test_health_no_token_is_200(self):
        resp = get("/health", auth=False)
        body = assert_success_response(resp)
        assert body.get("status") == "alive"
        assert isinstance(body.get("uptime_seconds"), (int, float))
        assert isinstance(body.get("log_level"), str)

    def test_protected_route_no_token_is_401(self):
        resp = get("/api/v1/leads", auth=False)
        assert_detail_error(resp, 401)

    def test_protected_route_wrong_token_is_401(self):
        resp = CLIENT.get(
            "/api/v1/leads",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert_detail_error(resp, 401)

    def test_protected_route_valid_token_returns_leads(self):
        resp = get("/api/v1/leads")
        assert_list_response(resp)

    def test_websocket_valid_token_connects(self):
        with CLIENT.websocket_connect("/ws?token=test-token-abc123") as ws:
            msg = ws.receive_json()
        self.assertEqual(msg["type"], "heartbeat")

    def test_websocket_missing_token_closes_without_server_error(self):
        with self.assertRaises(Exception):
            with CLIENT.websocket_connect("/ws"):
                pass


@pytest.mark.integration
class TestHealthEndpoint(unittest.TestCase):
    HEALTH_KEYS = {"status", "uptime_seconds", "timestamp", "log_level", "dependencies"}
    DEP_KEYS = {"database", "browser", "api_keys"}
    DEP_DB_KEYS = {"status", "latency_ms"}
    DEP_BROWSER_KEYS = {"status", "path"}
    DEP_API_KEYS = {"status", "configured_providers"}

    def test_health_structure(self):
        resp = get("/health")
        body = assert_success_response(resp, required_keys=self.HEALTH_KEYS)
        assert body["status"] == "alive"
        assert isinstance(body["uptime_seconds"], (int, float))
        assert_timestamp_iso8601(body["timestamp"])
        assert isinstance(body["log_level"], str)

    def test_health_dependencies_structure(self):
        resp = get("/health")
        deps = resp.json().get("dependencies", {})
        missing = self.DEP_KEYS - set(deps.keys())
        assert not missing, f"dependencies missing keys: {missing}"

        db = deps.get("database", {})
        db_missing = self.DEP_DB_KEYS - set(db.keys())
        assert not db_missing, f"database missing keys: {db_missing}"
        assert isinstance(db["latency_ms"], (int, float))

        browser = deps.get("browser", {})
        browser_missing = self.DEP_BROWSER_KEYS - set(browser.keys())
        assert not browser_missing, f"browser missing keys: {browser_missing}"

        api = deps.get("api_keys", {})
        api_missing = self.DEP_API_KEYS - set(api.keys())
        assert not api_missing, f"api_keys missing keys: {api_missing}"
        assert isinstance(api["configured_providers"], list)


@pytest.mark.integration
class TestLeadsEndpoints(unittest.TestCase):
    def test_get_leads_returns_list(self):
        resp = get("/api/v1/leads")
        body = assert_list_response(resp)
        assert_all_dict_items(body)

    def test_get_leads_seniority_filter_accepted(self):
        resp = get("/api/v1/leads", params={"seniority": "senior"})
        body = assert_list_response(resp)
        assert_all_dict_items(body)

    def test_get_lead_not_found(self):
        resp = get("/api/v1/leads/nonexistent-job-id")
        assert_detail_error(resp, 404, detail_contains="not found")

    def test_delete_lead_not_found(self):
        resp = delete("/api/v1/leads/nonexistent-job-id")
        assert_detail_error(resp, 404, detail_contains="not found")

    def test_update_status_invalid_body(self):
        resp = put(
            "/api/v1/leads/any-id/status",
            json={"status": "not_a_real_status"},
        )
        body = assert_validation_error(resp, field_loc="status", error_type="literal_error")
        # Verify the error loc has the expected path: body → status
        locs = [err["loc"] for err in body["detail"]]
        assert any(loc == ["body", "status"] for loc in locs), (
            f"Expected loc ['body', 'status'], got locs: {locs}"
        )

    def test_update_status_valid_body_not_found(self):
        resp = put(
            "/api/v1/leads/nonexistent/status",
            json={"status": "applied"},
        )
        assert_detail_error(resp, 404, detail_contains="not found")

    def test_delete_lead_round_trip(self):
        jid = _seed_lead()
        resp = delete(f"/api/v1/leads/{jid}")
        assert_ok_response(resp)
        resp2 = get(f"/api/v1/leads/{jid}")
        assert_detail_error(resp2, 404, detail_contains="not found")

    def test_manual_lead_missing_fields(self):
        resp = post("/api/v1/leads/manual", json={})
        assert_detail_exactly(resp, 400, "Paste lead text or a URL")

    def test_manual_lead_text_too_long(self):
        resp = post("/api/v1/leads/manual", json={"text": "x" * 25000})
        body = assert_validation_error(resp, field_loc="text", error_type="string_too_long")
        # Verify the error loc has the expected path: body → text
        locs = [err["loc"] for err in body["detail"]]
        assert any(loc == ["body", "text"] for loc in locs), (
            f"Expected loc ['body', 'text'], got locs: {locs}"
        )


@pytest.mark.integration
class TestExportEndpoint(unittest.TestCase):
    EXPECTED_CSV_HEADERS = {"job_id", "title", "company", "url"}

    def test_export_csv_contract(self):
        resp = get("/api/v1/leads/export.csv")
        assert_csv_response(resp, expected_header_fields=self.EXPECTED_CSV_HEADERS)

    def test_export_csv_content_type(self):
        resp = get("/api/v1/leads/export.csv")
        self.assertIn("text/csv", resp.headers.get("content-type", ""))

    def test_export_csv_has_header_row(self):
        resp = get("/api/v1/leads/export.csv")
        first_line = resp.text.splitlines()[0] if resp.text else ""
        self.assertIn("job_id", first_line)


@pytest.mark.integration
class TestSettingsEndpoints(unittest.TestCase):
    def test_get_template_returns_dict(self):
        resp = get("/api/v1/template")
        body = assert_success_response(resp, required_keys={"template"})
        assert isinstance(body["template"], str)

    def test_save_and_retrieve_template(self):
        template_text = "Custom template for round-trip test"
        resp = post("/api/v1/template", json={"template": template_text})
        assert_ok_response(resp)
        resp2 = get("/api/v1/template")
        body = assert_success_response(resp2, required_keys={"template"})
        assert body["template"] == template_text

    def test_settings_save_and_retrieve(self):
        key, val = "test_roundtrip_key", "test_roundtrip_value"
        resp = post("/api/v1/settings", json={key: val})
        assert_ok_response(resp)
        from db.client import get_setting
        retrieved = get_setting(key)
        assert retrieved == val

    def test_save_template_too_long(self):
        resp = post("/api/v1/template", json={"template": "x" * 25000})
        body = assert_validation_error(resp, field_loc="template", error_type="string_too_long")
        locs = [err["loc"] for err in body["detail"]]
        assert any(loc == ["body", "template"] for loc in locs), (
            f"Expected loc ['body', 'template'], got locs: {locs}"
        )

    def test_validate_returns_provider_dict(self):
        resp = get("/api/v1/settings/validate")
        body = assert_success_response(resp)
        assert isinstance(body, dict)
        assert len(body) > 0
        for provider, result in body.items():
            assert isinstance(provider, str)
            assert isinstance(result, dict)
            assert "status" in result
            assert isinstance(result["status"], str)
            assert "latency_ms" in result
            assert isinstance(result["latency_ms"], (int, float))

    def test_settings_save_sensitive_key_logs_deprecation(self):
        with mock.patch("services.provider_probe._log") as mock_log:
            resp = post("/api/v1/settings", json={"hunter_api_key": "test-key-123"})
            assert_ok_response(resp)
            found = any(
                "written to SQLite" in str(call)
                for call in mock_log.warning.call_args_list
            )
            self.assertTrue(found, "Expected deprecation warning about SQLite write")

    def test_settings_save_non_sensitive_key_no_deprecation(self):
        with mock.patch("services.provider_probe._log") as mock_log:
            resp = post("/api/v1/settings", json={"ghost_mode": "true"})
            assert_ok_response(resp)
            for call in mock_log.warning.call_args_list:
                self.assertNotIn("written to SQLite", str(call))


@pytest.mark.integration
class TestFollowupsEndpoint(unittest.TestCase):
    def test_due_followups_returns_list(self):
        resp = get("/api/v1/followups/due")
        body = assert_list_response(resp)
        assert_all_dict_items(body)


@pytest.mark.integration
class TestFormReaderEndpoints(unittest.TestCase):
    IDENTITY_KEYS = {
        "full_name", "email", "phone", "linkedin_url",
        "github_url", "website_url", "city", "current_company",
    }

    def test_form_read_not_found(self):
        resp = post(
            "/api/v1/leads/nonexistent/form/read",
            json={"url": "https://example.com/apply"},
        )
        assert_detail_error(resp, 404, detail_contains="not found")

    def test_form_read_no_url(self):
        _seed_lead({"job_id": "test-form-001", "url": ""})
        resp = post(
            "/api/v1/leads/test-form-001/form/read",
            json={"url": ""},
        )
        assert_detail_contains(resp, 400, "no url")

    def test_identity_endpoint(self):
        resp = get("/api/v1/identity")
        body = assert_success_response(resp, required_keys=self.IDENTITY_KEYS)
        for key in self.IDENTITY_KEYS:
            assert isinstance(body[key], str), f"identity.{key} should be str"

    def test_selectors_refresh(self):
        resp = post("/api/v1/selectors/refresh")
        body = assert_success_response(resp, required_keys={"version", "platforms"})
        assert isinstance(body["platforms"], list)


@pytest.mark.integration
class TestPipelineRunEndpoint(unittest.TestCase):
    def test_pipeline_run_not_found(self):
        resp = post("/api/v1/leads/nonexistent/pipeline/run")
        assert_detail_error(resp, 404, detail_contains="not found")

    def test_pipeline_run_valid_id_accepted(self):
        _seed_lead({"job_id": "test-pipeline-001"})
        _seed_setting("llm_provider", "ollama")
        resp = post("/api/v1/leads/test-pipeline-001/pipeline/run")
        body = assert_success_response(resp, required_keys={"status", "job_id"})
        assert body["status"] == "started"
        assert body["job_id"] == "test-pipeline-001"


@pytest.mark.integration
class TestGenerateEndpoint(unittest.TestCase):
    def test_generate_waits_for_ready_package(self):
        ready_lead = {
            "job_id": "test-generate-001",
            "resume_asset": "/tmp/resume.pdf",
            "cover_letter_asset": "/tmp/cover.pdf",
        }
        with mock.patch("services.generator._generate_one", new=mock.AsyncMock(return_value=ready_lead)):
            resp = post("/api/v1/leads/test-generate-001/generate")

        body = assert_success_response(resp, required_keys={"status", "job_id", "lead"})
        assert body["status"] == "ready"
        assert isinstance(body["lead"], dict)
        assert body["lead"]["job_id"] == "test-generate-001"


@pytest.mark.integration
class TestIngestionEndpoints(unittest.TestCase):
    PROFILE_STATS_KEYS = {
        "skills", "experience", "projects", "education",
        "certifications", "achievements",
    }

    def test_linkedin_ingest_rejects_non_zip(self):
        resp = CLIENT.post(
            "/api/v1/ingest/linkedin",
            headers=AUTH,
            files={"file": ("resume.txt", b"not a zip", "text/plain")},
        )
        assert_detail_exactly(resp, 400, "expected a .zip file from LinkedIn data export")

    def test_linkedin_ingest_rejects_invalid_zip(self):
        resp = CLIENT.post(
            "/api/v1/ingest/linkedin",
            headers=AUTH,
            files={"file": ("export.zip", b"this is not a valid zip file", "application/zip")},
        )
        assert_detail_contains(resp, 422, "could not parse linkedin export")

    def test_linkedin_ingest_accepts_valid_zip(self):
        import io
        import zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("Profile.csv", "First Name,Last Name,Headline,Summary,Geo Location\nTest,User,Engineer,Summary,London")
            zf.writestr("Skills.csv", "Name\nPython\nTypeScript")
            zf.writestr("Positions.csv", "Company Name,Title,Description,Location,Started On,Finished On\nAcme,Engineer,Did things,London,Jan 2023,Present")
        zip_bytes = buf.getvalue()

        resp = CLIENT.post(
            "/api/v1/ingest/linkedin",
            headers=AUTH,
            files={"file": ("export.zip", zip_bytes, "application/zip")},
        )
        body = assert_success_response(resp, required_keys={"status", "stats", "location", "errors"})
        assert body["status"] in {"ok", "partial"}
        assert isinstance(body["stats"], dict)
        assert isinstance(body["errors"], list)
        assert body["stats"]["skills"] >= 2

    def test_github_ingest_unknown_user(self):
        import agents.github_ingestor as _gh_mod

        async def _fake_fetch(*args, **kwargs):
            return None

        with mock.patch.object(_gh_mod, "_fetch", side_effect=_fake_fetch):
            resp = post(
                "/api/v1/ingest/github",
                json={"username": "this-user-does-not-exist-jhm-test"},
            )
        assert_detail_contains(resp, 404, "not found")

    def test_github_ingest_missing_username(self):
        resp = post("/api/v1/ingest/github", json={"username": ""})
        body = assert_validation_error(resp, field_loc="username", error_type="string_too_short")
        locs = [err["loc"] for err in body["detail"]]
        assert any(loc == ["body", "username"] for loc in locs), (
            f"Expected loc ['body', 'username'], got locs: {locs}"
        )

    def test_profile_import_empty_body(self):
        resp = post("/api/v1/ingest/profile", json={})
        body = assert_success_response(resp, required_keys={"status", "stats", "errors"})
        assert body["status"] == "ok"
        assert isinstance(body["stats"], dict)
        for key in self.PROFILE_STATS_KEYS:
            assert key in body["stats"], f"Missing profile stat key: {key}"
        assert isinstance(body["errors"], list)

    def test_profile_import_valid_skills(self):
        resp = post(
            "/api/v1/ingest/profile",
            json={
                "skills": [
                    {"name": "Python", "category": "language"},
                    {"name": "React", "category": "frontend"},
                ],
            },
        )
        body = assert_success_response(resp, required_keys={"status", "stats", "errors"})
        assert isinstance(body["stats"]["skills"], int)

    def test_profile_import_skill_name_too_long(self):
        resp = post(
            "/api/v1/ingest/profile",
            json={"skills": [{"name": "x" * 200, "category": "language"}]},
        )
        body = assert_validation_error(resp, field_loc="name", error_type="string_too_long")
        locs = [err["loc"] for err in body["detail"]]
        assert any(loc == ["body", "skills", 0, "name"] for loc in locs), (
            f"Expected loc ['body', 'skills', 0, 'name'], got locs: {locs}"
        )

    def test_profile_template_endpoint(self):
        resp = get("/api/v1/ingest/profile/template")
        body = assert_success_response(resp, required_keys={"skills"})
        assert isinstance(body["skills"], list)
        assert_all_dict_items(body["skills"])

    def test_portfolio_ingest_invalid_url(self):
        resp = post("/api/v1/ingest/portfolio", json={"url": "not-a-url"})
        assert_detail_exactly(resp, 400, "url must start with http:// or https://")

    PORTFOLIO_KEYS = {
        "source", "url", "screenshot_b64", "candidate",
        "skills", "projects", "achievements", "experience",
        "education", "certifications", "stats", "error",
    }

    def test_portfolio_ingest_valid_url_structure(self):
        async def _fake_ingest_portfolio_url(_url):
            return {
                "source": "portfolio_url",
                "url": "https://example.com",
                "screenshot_b64": "",
                "candidate": {"name": "", "summary": ""},
                "skills": [],
                "projects": [],
                "achievements": [],
                "experience": [],
                "education": [],
                "certifications": [],
                "stats": {"skills": 0, "projects": 0},
                "error": None,
            }

        with mock.patch(
            "agents.portfolio_ingestor.ingest_portfolio_url",
            side_effect=_fake_ingest_portfolio_url,
        ):
            resp = post(
                "/api/v1/ingest/portfolio",
                json={"url": "https://example.com"},
            )
        body = assert_success_response(resp, required_keys=self.PORTFOLIO_KEYS)
        assert isinstance(body["source"], str)
        assert isinstance(body["skills"], list)
        assert isinstance(body["stats"], dict)
        assert body["stats"]["skills"] == 0
        assert body["error"] is None


if __name__ == "__main__":
    unittest.main()
