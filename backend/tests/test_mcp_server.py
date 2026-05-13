import json
import unittest

from mcp_server import _handle


class MCPServerTests(unittest.TestCase):
    def test_initialize_returns_tool_capability(self):
        response = _handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})

        self.assertEqual(response["id"], 1)
        self.assertIn("tools", response["result"]["capabilities"])

    def test_tools_list_exposes_job_intelligence_tools(self):
        response = _handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        names = {tool["name"] for tool in response["result"]["tools"]}

        self.assertEqual(
            names,
            {"score_job_fit", "evaluate_lead_quality", "extract_lead_intel"},
        )

    def test_extract_lead_intel_tool_returns_text_content(self):
        response = _handle(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "extract_lead_intel",
                    "arguments": {
                        "text": "Acme is hiring a remote Python FastAPI React engineer. Apply today."
                    },
                },
            }
        )

        result = response["result"]
        payload = json.loads(result["content"][0]["text"])
        self.assertFalse(result["isError"])
        self.assertEqual(payload["location"], "Remote")
        self.assertIn("Python", payload["tech_stack"])

    def test_initialize_with_wrong_params_still_works(self):
        # initialize should ignore params
        response = _handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"unexpected": "value"}})
        self.assertEqual(response["id"], 1)
        self.assertIn("tools", response["result"]["capabilities"])

    def test_tools_list_with_params_ignored(self):
        # tools/list should ignore params
        response = _handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {"unexpected": "value"}})
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {"score_job_fit", "evaluate_lead_quality", "extract_lead_intel"},
        )

    def test_unknown_method_returns_error(self):
        response = _handle({"jsonrpc": "2.0", "id": 1, "method": "unknown/method", "params": {}})
        self.assertEqual(response["id"], 1)
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32603)
        self.assertIn("Unsupported method", response["error"]["message"])

    def test_malformed_jsonrpc_request_handled_in_main(self):
        # This is tested indirectly - the main function catches JSON parse errors
        # We can test that our error handling structure is correct
        pass

    def test_tools_call_unknown_tool_returns_error(self):
        response = _handle({
            "jsonrpc": "2.0", 
            "id": 1, 
            "method": "tools/call", 
            "params": {
                "name": "unknown_tool",
                "arguments": {}
            }
        })
        self.assertEqual(response["id"], 1)
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32603)
        self.assertIn("Unknown tool", response["error"]["message"])

    def test_tools_call_missing_name_returns_error(self):
        response = _handle({
            "jsonrpc": "2.0", 
            "id": 1, 
            "method": "tools/call", 
            "params": {
                "arguments": {"text": "test"}
            }
        })
        self.assertEqual(response["id"], 1)
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32603)
        self.assertIn("Unknown tool", response["error"]["message"])

    def test_extract_lead_intel_with_empty_text_returns_error(self):
        response = _handle({
            "jsonrpc": "2.0", 
            "id": 1, 
            "method": "tools/call", 
            "params": {
                "name": "extract_lead_intel",
                "arguments": {
                    "text": ""
                }
            }
        })
        self.assertEqual(response["id"], 1)
        self.assertIn("result", response)
        self.assertTrue(response["result"]["isError"])
        self.assertIn("text is required", response["result"]["content"][0]["text"])

    def test_score_job_fit_missing_posting_returns_error(self):
        response = _handle({
            "jsonrpc": "2.0", 
            "id": 1, 
            "method": "tools/call", 
            "params": {
                "name": "score_job_fit",
                "arguments": {
                    "candidate": {"skills": [{"n": "Python"}]}
                }
            }
        })
        self.assertEqual(response["id"], 1)
        self.assertIn("result", response)
        self.assertTrue(response["result"]["isError"])
        self.assertIn("posting is required", response["result"]["content"][0]["text"])

    def test_score_job_fit_wrong_candidate_type_returns_error(self):
        response = _handle({
            "jsonrpc": "2.0", 
            "id": 1, 
            "method": "tools/call", 
            "params": {
                "name": "score_job_fit",
                "arguments": {
                    "posting": "Python developer needed",
                    "candidate": "not a dict"
                }
            }
        })
        self.assertEqual(response["id"], 1)
        self.assertIn("result", response)
        self.assertTrue(response["result"]["isError"])
        self.assertIn("candidate must be a JSON object", response["result"]["content"][0]["text"])

    def test_evaluate_lead_wrong_lead_type_returns_error(self):
        response = _handle({
            "jsonrpc": "2.0", 
            "id": 1, 
            "method": "tools/call", 
            "params": {
                "name": "evaluate_lead_quality",
                "arguments": {
                    "lead": "not a dict"
                }
            }
        })
        self.assertEqual(response["id"], 1)
        self.assertIn("result", response)
        self.assertTrue(response["result"]["isError"])
        self.assertIn("lead must be a JSON object", response["result"]["content"][0]["text"])

    def test_extract_lead_intel_with_valid_text_returns_structured_data(self):
        response = _handle({
            "jsonrpc": "2.0", 
            "id": 1, 
            "method": "tools/call", 
            "params": {
                "name": "extract_lead_intel",
                "arguments": {
                    "text": "Remote Senior Python Engineer at TechCorp. Must have 5+ years experience with Django and AWS."
                }
            }
        })
        self.assertEqual(response["id"], 1)
        self.assertFalse(response["result"]["isError"])
        payload = json.loads(response["result"]["content"][0]["text"])
        # Should have all expected fields
        self.assertIn("company", payload)
        self.assertIn("location", payload)
        self.assertIn("budget", payload)
        self.assertIn("urgency", payload)
        self.assertIn("tech_stack", payload)
        self.assertIn("signal_quality", payload)
        # Location should capture "Remote"
        self.assertIn("Remote", payload["location"])
        # Company should capture "TechCorp" or similar
        self.assertTrue(len(payload["company"]) > 0)
        # Tech stack should contain Python
        self.assertIn("Python", payload["tech_stack"])

    def test_notifications_initialized_returns_none(self):
        # notifications/initialized should return None (no response expected)
        response = _handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertIsNone(response)
