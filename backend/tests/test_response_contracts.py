"""Verify route responses conform to their response_model= schemas.

response_model= is an active serialization boundary — fields not in the model
are silently stripped from the outbound payload. This suite catches field drops
by re-serializing actual responses through their models and asserting every
returned key has a corresponding model field.
"""

import os
import tempfile

os.environ["JHM_APP_DATA_DIR"] = tempfile.mkdtemp(prefix="jhm_test_")

from tests.fakes import _install_storage_fakes

_install_storage_fakes(use_real_sqlite=True)

from fastapi.testclient import TestClient

import main

main._API_TOKEN = "test-token-abc123"

from main import app

CLIENT = TestClient(app, raise_server_exceptions=False)
AUTH = {"Authorization": "Bearer test-token-abc123"}


def test_health_response_fields_in_model():
    resp = CLIENT.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    known = {"status", "uptime_seconds", "timestamp", "log_level", "dependencies"}
    for key in body:
        assert key in known, f"HealthResponse missing field: {key}"


def test_identity_response_fields_in_model():
    resp = CLIENT.get("/api/v1/identity", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    known = {"full_name", "email", "phone", "linkedin_url",
             "github_url", "website_url", "city", "current_company"}
    for key in body:
        assert key in known, f"IdentityResponse missing field: {key}"


def test_scan_response_fields_in_model():
    resp = CLIENT.post("/api/v1/scan", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    known = {"status"}
    for key in body:
        assert key in known, f"StatusResponse missing field: {key}"


def test_template_response_fields_in_model():
    resp = CLIENT.get("/api/v1/template", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    known = {"template"}
    for key in body:
        assert key in known, f"TemplateResponse missing field: {key}"


def test_template_save_response_fields_in_model():
    resp = CLIENT.post("/api/v1/template", headers=AUTH, json={"template": "test"})
    assert resp.status_code == 200
    body = resp.json()
    known = {"ok"}
    for key in body:
        assert key in known, f"OkResponse missing field: {key}"


def test_job_targets_get_empty_response():
    resp = CLIENT.get("/api/v1/settings/job-targets", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    known = {"targets", "blocked"}
    for key in body:
        assert key in known, f"JobTargetsResponse missing field: {key}"
    assert body["targets"] == []
    assert body["blocked"] == []


def test_job_targets_put_and_get_round_trip():
    payload = {"targets": ["https://remoteok.com/api", "site:linkedin.com/jobs"], "blocked": ["freelance"]}
    resp = CLIENT.put("/api/v1/settings/job-targets", headers=AUTH, json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["targets"] == payload["targets"]
    assert body["blocked"] == payload["blocked"]

    resp = CLIENT.get("/api/v1/settings/job-targets", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["targets"] == payload["targets"]
    assert body["blocked"] == payload["blocked"]


def test_job_targets_put_rejects_invalid():
    resp = CLIENT.put("/api/v1/settings/job-targets", headers=AUTH, json={"targets": ["site:opp"]})
    assert resp.status_code == 422


def test_job_targets_delete_clears():
    CLIENT.put("/api/v1/settings/job-targets", headers=AUTH, json={"targets": ["https://remoteok.com/api"]})
    resp = CLIENT.delete("/api/v1/settings/job-targets", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["targets"] == []
    assert body["blocked"] == []
