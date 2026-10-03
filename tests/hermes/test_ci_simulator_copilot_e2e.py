import io
import os
import urllib.error
import unittest
from unittest.mock import patch

import ci_simulator_copilot_e2e as e2e
from ci_simulator_copilot_e2e import (
    has_successful_ls_tool_run,
    has_successful_tool_run,
    parse_sse_events,
)


class CopilotSimulatorE2ETests(unittest.TestCase):
    def test_http_error_keeps_safe_server_detail_and_redacts_credentials(self):
        error = urllib.error.HTTPError(
            "http://127.0.0.1/api/session/new",
            400,
            "Bad Request",
            {},
            io.BytesIO(
                b'{"error":"Path rejected; Authorization: Bearer ghp_123456789012345678901234567890"}'
            ),
        )
        with patch("ci_simulator_copilot_e2e.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(e2e.E2EError) as raised:
                e2e._request_json("/api/session/new", {})

        self.assertIn("HTTP 400: Path rejected", str(raised.exception))
        self.assertIn("[redacted]", str(raised.exception))
        self.assertNotIn("ghp_", str(raised.exception))

    def test_parses_named_multiline_sse_json_events(self):
        events = list(
            parse_sse_events(
                [
                    ": heartbeat\n",
                    "event: tool\n",
                    'data: {"name":"terminal",\n',
                    'data: "args":{"command":"ls -la"}}\n',
                    "\n",
                ]
            )
        )

        self.assertEqual(events, [("tool", {"name": "terminal", "args": {"command": "ls -la"}})])

    def test_requires_terminal_ls_completion_with_expected_workspace_output(self):
        events = [
            ("tool", {"name": "terminal", "args": {"command": "ls -la"}, "tid": "call-1"}),
            (
                "tool_complete",
                {
                    "name": "terminal",
                    "args": {"command": "ls -la"},
                    "tid": "call-1",
                    "is_error": False,
                    "preview": "HermesLink-E2E-LS-PROOF.txt",
                },
            ),
        ]

        self.assertTrue(has_successful_ls_tool_run(events, "HermesLink-E2E-LS-PROOF.txt"))

    def test_requires_terminal_to_run_the_native_ish_command(self):
        command = "ish printf HermesLink-E2E-ISH-COMMAND-proof"
        proof = "HermesLink-E2E-ISH-COMMAND-proof"
        events = [
            ("tool", {"name": "terminal", "args": {"command": command}, "tid": "call-1"}),
            (
                "tool_complete",
                {
                    "name": "terminal",
                    "args": {"command": command},
                    "tid": "call-1",
                    "is_error": False,
                    "preview": proof,
                },
            ),
        ]

        self.assertTrue(has_successful_tool_run(events, "terminal", command, proof))
        self.assertFalse(has_successful_tool_run(events, "ish", "printf " + proof, proof))

    def test_requires_ish_agent_tool_with_matching_successful_completion(self):
        command = "printf HermesLink-E2E-ISH-TOOL-proof"
        proof = "HermesLink-E2E-ISH-TOOL-proof"
        events = [
            ("tool", {"name": "ish", "args": {"command": command}, "tid": "call-1"}),
            (
                "tool_complete",
                {
                    "name": "ish",
                    "args": {"command": command},
                    "tid": "call-1",
                    "is_error": False,
                    "preview": proof,
                },
            ),
        ]

        self.assertTrue(has_successful_tool_run(events, "ish", command, proof))

    def test_ish_agent_tool_rejects_wrong_command_or_missing_alpine_proof(self):
        command = "printf HermesLink-E2E-ISH-TOOL-proof"
        proof = "HermesLink-E2E-ISH-TOOL-proof"
        events = [
            ("tool", {"name": "ish", "args": {"command": "echo wrong"}, "tid": "call-1"}),
            (
                "tool_complete",
                {
                    "name": "ish",
                    "args": {"command": "echo wrong"},
                    "tid": "call-1",
                    "is_error": False,
                    "preview": proof,
                },
            ),
        ]

        self.assertFalse(has_successful_tool_run(events, "ish", command, proof))

    def test_ish_agent_tool_rejects_completion_without_its_unique_proof(self):
        command = "printf HermesLink-E2E-ISH-TOOL-proof"
        proof = "HermesLink-E2E-ISH-TOOL-proof"
        events = [
            ("tool", {"name": "ish", "args": {"command": command}, "tid": "call-1"}),
            (
                "tool_complete",
                {
                    "name": "ish",
                    "args": {"command": command},
                    "tid": "call-1",
                    "is_error": False,
                    "preview": "not the Alpine output",
                },
            ),
        ]

        self.assertFalse(has_successful_tool_run(events, "ish", command, proof))

    def test_rejects_assistant_text_without_a_tool_call(self):
        events = [("token", {"text": "I ran ls and found HermesLink-E2E-LS-PROOF.txt"})]

        self.assertFalse(has_successful_ls_tool_run(events, "HermesLink-E2E-LS-PROOF.txt"))

    def test_rejects_tool_error_even_when_preview_mentions_sentinel(self):
        events = [
            ("tool", {"name": "terminal", "args": {"command": "ls"}, "tid": "call-1"}),
            (
                "tool_complete",
                {
                    "name": "terminal",
                    "args": {"command": "ls"},
                    "tid": "call-1",
                    "is_error": True,
                    "preview": "HermesLink-E2E-LS-PROOF.txt",
                },
            ),
        ]

        self.assertFalse(has_successful_ls_tool_run(events, "HermesLink-E2E-LS-PROOF.txt"))

    def test_requires_matching_tool_call_and_completion_ids(self):
        events = [
            ("tool", {"name": "terminal", "args": {"command": "ls"}, "tid": "call-1"}),
            (
                "tool_complete",
                {
                    "name": "terminal",
                    "args": {"command": "ls"},
                    "tid": "call-2",
                    "is_error": False,
                    "preview": "HermesLink-E2E-LS-PROOF.txt",
                },
            ),
        ]

        self.assertFalse(has_successful_ls_tool_run(events, "HermesLink-E2E-LS-PROOF.txt"))

    def test_rejects_commands_that_only_mention_ls(self):
        events = [
            ("tool", {"name": "terminal", "args": {"command": "echo ls"}, "tid": "call-1"}),
            (
                "tool_complete",
                {
                    "name": "terminal",
                    "args": {"command": "echo ls"},
                    "tid": "call-1",
                    "is_error": False,
                    "preview": "HermesLink-E2E-LS-PROOF.txt",
                },
            ),
        ]

        self.assertFalse(has_successful_ls_tool_run(events, "HermesLink-E2E-LS-PROOF.txt"))

    def test_rejects_shell_suffix_that_could_fake_the_workspace_proof(self):
        command = "ls -la; echo HermesLink-E2E-LS-PROOF.txt"
        events = [
            ("tool", {"name": "terminal", "args": {"command": command}, "tid": "call-1"}),
            (
                "tool_complete",
                {
                    "name": "terminal",
                    "args": {"command": command},
                    "tid": "call-1",
                    "is_error": False,
                    "preview": "HermesLink-E2E-LS-PROOF.txt",
                },
            ),
        ]

        self.assertFalse(has_successful_ls_tool_run(events, "HermesLink-E2E-LS-PROOF.txt"))

    def test_copilot_token_is_forwarded_only_to_the_simulator_app(self):
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "test-workflow-token",
                "GH_TOKEN": "test-other-token",
                "COPILOT_GITHUB_TOKEN": "test-copilot-token",
                "SIMCTL_CHILD_GITHUB_TOKEN": "test-stale-token",
                "SIMCTL_CHILD_COPILOT_GITHUB_TOKEN": "test-stale-copilot-token",
            },
            clear=True,
        ):
            host_env = e2e._simctl_env()
            app_env = e2e._simctl_env("test-copilot-token")

        for env in (host_env, app_env):
            self.assertNotIn("GITHUB_TOKEN", env)
            self.assertNotIn("GH_TOKEN", env)
            self.assertNotIn("COPILOT_GITHUB_TOKEN", env)
        self.assertNotIn("SIMCTL_CHILD_GITHUB_TOKEN", host_env)
        self.assertNotIn("SIMCTL_CHILD_COPILOT_GITHUB_TOKEN", host_env)
        self.assertNotIn("SIMCTL_CHILD_GITHUB_TOKEN", app_env)
        self.assertEqual(app_env["SIMCTL_CHILD_COPILOT_GITHUB_TOKEN"], "test-copilot-token")


if __name__ == "__main__":
    unittest.main()
