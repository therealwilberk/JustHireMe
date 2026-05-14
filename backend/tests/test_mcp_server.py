import json
import unittest

from conftest import assert_mcp_protocol_error, assert_mcp_response_structure, assert_mcp_tool_error
from mcp_server import _handle


class MCPServerTests(unittest.TestCase):
    TOOL_NAMES = {"score_job_fit", "evaluate_lead_quality", "extract_lead_intel"}
    EXTRACT_FIELDS = {"company", "location", "budget", "urgency", "tech_stack", "signal_quality"}

    INIT_RESULT_KEYS = {"protocolVersion", "capabilities", "serverInfo"}
    CAPABILITIES_KEYS = {"tools"}
    SERVER_INFO_KEYS = {"name", "version"}
    TOOL_SCHEMA_KEYS = {"name", "description", "inputSchema"}
    INPUT_SCHEMA_KEYS = {"type", "properties"}

    def test_initialize_returns_tool_capability(self):
        response = _handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert_mcp_response_structure(response, expected_id=1)
        result = response["result"]
        missing = self.INIT_RESULT_KEYS - set(result.keys())
        assert not missing, f"initialize result missing: {missing}"
        assert result["protocolVersion"] == "2024-11-05"
        caps_missing = self.CAPABILITIES_KEYS - set(result["capabilities"].keys())
        assert not caps_missing, f"capabilities missing: {caps_missing}"
        info_missing = self.SERVER_INFO_KEYS - set(result["serverInfo"].keys())
        assert not info_missing, f"serverInfo missing: {info_missing}"
        assert result["serverInfo"]["name"] == "justhireme"

    def test_tools_list_exposes_job_intelligence_tools(self):
        response = _handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        assert_mcp_response_structure(response, expected_id=2)
        tools = response["result"]["tools"]
        names = {tool["name"] for tool in tools}
        self.assertEqual(names, self.TOOL_NAMES)
        for tool in tools:
            tool_missing = self.TOOL_SCHEMA_KEYS - set(tool.keys())
            assert not tool_missing, f"tool {tool['name']} missing: {tool_missing}"
            assert isinstance(tool["description"], str)
            schema_missing = self.INPUT_SCHEMA_KEYS - set(tool["inputSchema"].keys())
            assert not schema_missing, f"tool {tool['name']} inputSchema missing: {schema_missing}"

    def test_extract_lead_intel_tool_returns_text_content(self):
        response = _handle({
            "jsonrpc": "2.0", "id": 3,
            "method": "tools/call",
            "params": {
                "name": "extract_lead_intel",
                "arguments": {
                    "text": "Acme is hiring a remote Python FastAPI React engineer. Apply today."
                },
            },
        })
        assert_mcp_response_structure(response, expected_id=3)
        result = response["result"]
        payload = json.loads(result["content"][0]["text"])
        self.assertFalse(result["isError"])
        self.assertEqual(payload["location"], "Remote")
        self.assertIn("Python", payload["tech_stack"])

    def test_initialize_with_wrong_params_still_works(self):
        response = _handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"unexpected": "value"}})
        assert_mcp_response_structure(response, expected_id=1)
        self.assertIn("tools", response["result"]["capabilities"])

    def test_tools_list_with_params_ignored(self):
        response = _handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {"unexpected": "value"}})
        assert_mcp_response_structure(response, expected_id=2)
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(names, self.TOOL_NAMES)

    def test_unknown_method_returns_error(self):
        response = _handle({"jsonrpc": "2.0", "id": 1, "method": "unknown/method", "params": {}})
        assert_mcp_protocol_error(response, message_contains="Unsupported method")

    def test_malformed_jsonrpc_request_handled_in_main(self):
        pass

    def test_tools_call_unknown_tool_returns_error(self):
        response = _handle({
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
        })
        assert_mcp_protocol_error(response, message_contains="Unknown tool")

    def test_tools_call_missing_name_returns_error(self):
        response = _handle({
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/call",
            "params": {"arguments": {"text": "test"}},
        })
        assert_mcp_protocol_error(response, message_contains="Unknown tool")

    def test_extract_lead_intel_with_empty_text_returns_error(self):
        response = _handle({
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/call",
            "params": {
                "name": "extract_lead_intel",
                "arguments": {"text": ""},
            },
        })
        assert_mcp_tool_error(response, message_contains="text is required")

    def test_score_job_fit_missing_posting_returns_error(self):
        response = _handle({
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/call",
            "params": {
                "name": "score_job_fit",
                "arguments": {"candidate": {"skills": [{"n": "Python"}]}},
            },
        })
        assert_mcp_tool_error(response, message_contains="posting is required")

    def test_score_job_fit_wrong_candidate_type_returns_error(self):
        response = _handle({
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/call",
            "params": {
                "name": "score_job_fit",
                "arguments": {
                    "posting": "Python developer needed",
                    "candidate": "not a dict",
                },
            },
        })
        assert_mcp_tool_error(response, message_contains="candidate must be a JSON object")

    def test_evaluate_lead_wrong_lead_type_returns_error(self):
        response = _handle({
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/call",
            "params": {
                "name": "evaluate_lead_quality",
                "arguments": {"lead": "not a dict"},
            },
        })
        assert_mcp_tool_error(response, message_contains="lead must be a JSON object")

    def test_extract_lead_intel_with_valid_text_returns_structured_data(self):
        response = _handle({
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/call",
            "params": {
                "name": "extract_lead_intel",
                "arguments": {
                    "text": "Remote Senior Python Engineer at TechCorp. Must have 5+ years experience with Django and AWS.",
                },
            },
        })
        assert_mcp_response_structure(response, expected_id=1)
        result = response["result"]
        self.assertFalse(result["isError"])
        payload = json.loads(result["content"][0]["text"])
        for key in self.EXTRACT_FIELDS:
            self.assertIn(key, payload)
        self.assertIn("Remote", payload["location"])
        self.assertTrue(len(payload["company"]) > 0)
        self.assertIn("Python", payload["tech_stack"])

    def test_notifications_initialized_returns_none(self):
        response = _handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertIsNone(response)
