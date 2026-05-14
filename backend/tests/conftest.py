import sys
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


collect_ignore_glob = ["tmp*"]


# ── API Contract Assertion Helpers ──────────────────────────────────────


def assert_error_response(resp, status: int) -> dict:
    """Assert a FastAPI error response with {"detail": str | list}.

    Returns the response body for further optional assertions.
    """
    assert resp.status_code == status, (
        f"Expected status {status}, got {resp.status_code}: {resp.text[:200]}"
    )
    body = resp.json()
    assert "detail" in body, f"Error response missing 'detail' key: {body}"
    assert isinstance(body["detail"], (str, list)), (
        f"'detail' must be str or list, got {type(body['detail']).__name__}"
    )
    return body


def assert_detail_error(resp, status: int, detail_contains: str | None = None) -> dict:
    """Assert error with {"detail": str} and optionally verify detail content."""
    body = assert_error_response(resp, status)
    assert isinstance(body["detail"], str), (
        f"Expected str detail, got {type(body['detail']).__name__}"
    )
    if detail_contains is not None:
        assert detail_contains.lower() in body["detail"].lower(), (
            f"Expected detail to contain {detail_contains!r}, got {body['detail']!r}"
        )
    return body


def assert_validation_error(
    resp,
    field_loc: str | None = None,
    error_type: str | None = None,
) -> dict:
    """Assert a 422 Pydantic validation error with loc/msg/type structure.

    Args:
        resp: The TestClient response.
        field_loc: If set, assert at least one error's loc contains this value.
        error_type: If set, assert at least one error's type matches.
    """
    body = assert_error_response(resp, 422)
    assert isinstance(body["detail"], list), (
        f"422 detail must be a list, got {type(body['detail']).__name__}"
    )
    assert len(body["detail"]) > 0, "422 detail list is empty"
    for err in body["detail"]:
        assert isinstance(err, dict), f"Each 422 error item must be dict, got {type(err).__name__}"
        assert "loc" in err, f"422 error missing 'loc': {err}"
        assert "msg" in err, f"422 error missing 'msg': {err}"
        assert "type" in err, f"422 error missing 'type': {err}"
        assert isinstance(err["loc"], list), f"422 loc must be list, got {type(err['loc']).__name__}"
        assert isinstance(err["msg"], str), f"422 msg must be str, got {type(err['msg']).__name__}"
        assert isinstance(err["type"], str), f"422 type must be str, got {type(err['type']).__name__}"

    if field_loc is not None:
        locs = [err["loc"] for err in body["detail"]]
        all_loc_values = [str(v) for loc in locs for v in loc]
        assert field_loc in all_loc_values, (
            f"Expected field_loc {field_loc!r} in error locs: {all_loc_values}"
        )
    if error_type is not None:
        types = [err["type"] for err in body["detail"]]
        assert error_type in types, (
            f"Expected error_type {error_type!r} in {types}"
        )
    return body


def assert_success_response(
    resp,
    status: int = 200,
    required_keys: set[str] | None = None,
) -> dict:
    """Assert a successful JSON response with optional field presence check.

    Returns the response body for further assertions.
    """
    assert resp.status_code == status, (
        f"Expected status {status}, got {resp.status_code}: {resp.text[:200]}"
    )
    body = resp.json()
    _assert_body_type(body, dict)
    if required_keys:
        missing = required_keys - set(body.keys())
        assert not missing, (
            f"Response missing required keys: {missing}. Present: {list(body.keys())}"
        )
    return body


def assert_list_response(resp, status: int = 200) -> list:
    """Assert a successful JSON list response."""
    assert resp.status_code == status, (
        f"Expected status {status}, got {resp.status_code}: {resp.text[:200]}"
    )
    body = resp.json()
    assert isinstance(body, list), f"Expected list, got {type(body).__name__}"
    return body


def assert_csv_response(resp, expected_header_fields: set[str] | None = None) -> str:
    """Assert a CSV response (200, text/csv, optional header check)."""
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert "text/csv" in resp.headers.get("content-type", ""), (
        f"Expected text/csv content-type, got {resp.headers.get('content-type')}"
    )
    if expected_header_fields and resp.text:
        first_line = resp.text.splitlines()[0]
        for field in expected_header_fields:
            assert field in first_line, (
                f"Expected CSV header field {field!r} not in {first_line}"
            )
    return resp.text


def assert_ok_response(resp, status: int = 200) -> dict:
    """Assert a response with {"ok": true}."""
    body = assert_success_response(resp, status=status, required_keys={"ok"})
    assert body["ok"] is True, f"Expected ok=true, got ok={body['ok']!r}"
    return body


def assert_detail_exactly(resp, status: int, expected: str) -> dict:
    """Assert an error response whose detail matches exactly."""
    body = assert_detail_error(resp, status)
    assert body["detail"] == expected, (
        f"Expected detail {expected!r}, got {body['detail']!r}"
    )
    return body


def assert_detail_contains(resp, status: int, substring: str) -> dict:
    """Assert an error response whose detail contains the given substring."""
    body = assert_error_response(resp, status)
    assert isinstance(body["detail"], str), f"detail must be str for substring match"
    assert substring.lower() in body["detail"].lower(), (
        f"Expected {substring!r} in detail {body['detail']!r}"
    )
    return body


# ── MCP (JSON-RPC) Contract Assertion Helpers ──────────────────────────


def assert_mcp_response_structure(response: dict, expected_id: int | None = 1) -> None:
    """Assert basic JSON-RPC response shape.

    Verifies: jsonrpc field, id matches, error/result mutual exclusivity.
    """
    assert response.get("jsonrpc") == "2.0", (
        f"Expected jsonrpc '2.0', got {response.get('jsonrpc')!r}"
    )
    assert response.get("id") == expected_id, (
        f"Expected id {expected_id}, got {response.get('id')!r}"
    )
    has_error = "error" in response
    has_result = "result" in response
    assert has_error != has_result, (
        f"error and result are mutually exclusive: error={has_error} result={has_result}"
    )


def assert_mcp_protocol_error(
    response: dict,
    expected_code: int = -32603,
    message_contains: str | None = None,
    expected_id: int | None = 1,
) -> dict:
    """Assert a JSON-RPC protocol-level error response.

    Verifies: jsonrpc, id, error.code, error.message structure.
    Returns the error dict for further assertions.
    """
    assert_mcp_response_structure(response, expected_id=expected_id)
    error = response["error"]
    assert isinstance(error, dict), f"error must be dict, got {type(error).__name__}"
    assert "code" in error, f"error missing 'code': {error}"
    assert "message" in error, f"error missing 'message': {error}"
    assert isinstance(error["code"], int), f"error.code must be int, got {type(error['code']).__name__}"
    assert isinstance(error["message"], str), (
        f"error.message must be str, got {type(error['message']).__name__}"
    )
    assert error["code"] == expected_code, (
        f"Expected error code {expected_code}, got {error['code']}"
    )
    if message_contains is not None:
        assert message_contains.lower() in error["message"].lower(), (
            f"Expected {message_contains!r} in error message {error['message']!r}"
        )
    return error


def assert_mcp_tool_error(
    response: dict,
    message_contains: str | None = None,
    expected_id: int | None = 1,
) -> dict:
    """Assert an MCP tool-level error response (result with isError=true).

    Verifies: jsonrpc, id, result.isError, content structure.
    Returns the result dict for further assertions.
    """
    assert_mcp_response_structure(response, expected_id=expected_id)
    result = response["result"]
    assert isinstance(result, dict), f"result must be dict, got {type(result).__name__}"
    assert result.get("isError") is True, f"Expected isError=true, got {result.get('isError')!r}"
    assert "content" in result, f"result missing 'content': {result}"
    assert isinstance(result["content"], list), (
        f"content must be list, got {type(result['content']).__name__}"
    )
    assert len(result["content"]) > 0, "content list is empty"
    content_item = result["content"][0]
    assert isinstance(content_item, dict), (
        f"content[0] must be dict, got {type(content_item).__name__}"
    )
    assert content_item.get("type") == "text", (
        f"Expected content[0].type='text', got {content_item.get('type')!r}"
    )
    assert isinstance(content_item.get("text"), str), (
        f"content[0].text must be str, got {type(content_item.get('text')).__name__}"
    )
    if message_contains is not None:
        assert message_contains.lower() in content_item["text"].lower(), (
            f"Expected {message_contains!r} in error text {content_item['text']!r}"
        )
    return result


# ── Generic Shape Helpers ───────────────────────────────────────────────


def assert_timestamp_iso8601(value: str) -> None:
    """Assert a string is ISO 8601 formatted (e.g. '2026-05-14T12:00:00+00:00')."""
    assert isinstance(value, str), f"Expected str, got {type(value).__name__}"
    assert "T" in value and ("+" in value or value.endswith("Z")), (
        f"Expected ISO 8601 timestamp, got {value!r}"
    )


def assert_all_str_items(items: list) -> None:
    for i, item in enumerate(items):
        assert isinstance(item, str), f"Item {i} should be str, got {type(item).__name__}"


def assert_all_dict_items(items: list, required_keys: set[str] | None = None) -> None:
    for i, item in enumerate(items):
        assert isinstance(item, dict), f"Item {i} should be dict, got {type(item).__name__}"
        if required_keys:
            missing = required_keys - set(item.keys())
            assert not missing, f"Item {i} missing keys: {missing}"


def _assert_body_type(body: Any, expected: type) -> None:
    assert isinstance(body, expected), (
        f"Expected {expected.__name__}, got {type(body).__name__}: {str(body)[:200]}"
    )
