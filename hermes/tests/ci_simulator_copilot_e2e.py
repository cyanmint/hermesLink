#!/usr/bin/env python3
"""Launch HermesLink in iOS Simulator and verify a real Copilot terminal call."""
from __future__ import annotations

import json
import os
import plistlib
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Iterable, Iterator


MODEL = "gpt-6-luna"
PROVIDER = "copilot"
BASE_URL = "http://127.0.0.1:8787"
PROOF_PREFIX = "HermesLink-E2E-LS-PROOF-"


class E2EError(RuntimeError):
    """A safe-to-print failure without response bodies or credentials."""


def parse_sse_events(lines: Iterable[str | bytes]) -> Iterator[tuple[str, object]]:
    event_name = "message"
    data_lines: list[str] = []

    def emit() -> tuple[str, object] | None:
        if not data_lines:
            return None
        raw_data = "\n".join(data_lines)
        try:
            payload: object = json.loads(raw_data)
        except json.JSONDecodeError:
            payload = raw_data
        return event_name, payload

    for raw_line in lines:
        line = raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, bytes) else raw_line
        line = line.rstrip("\r\n")
        if not line:
            item = emit()
            if item is not None:
                yield item
            event_name = "message"
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        field, separator, value = line.partition(":")
        if separator and value.startswith(" "):
            value = value[1:]
        if field == "event":
            event_name = value
        elif field == "data":
            data_lines.append(value)

    item = emit()
    if item is not None:
        yield item


def _tool_call_id(payload: dict) -> str | None:
    for key in ("tid", "tool_call_id", "id"):
        value = payload.get(key)
        if value:
            return str(value)
    return None


def _is_ls_command(payload: dict) -> bool:
    args = payload.get("args")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return False
    if not isinstance(args, dict):
        return False
    command = args.get("command")
    if not isinstance(command, str):
        return False
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        return False
    return words == ["ls", "-la"]


def has_successful_ls_tool_run(
    events: Iterable[tuple[str, object]], sentinel: str
) -> bool:
    calls: list[tuple[str | None, dict]] = []
    completions: list[tuple[str | None, dict]] = []
    for event_name, raw_payload in events:
        if not isinstance(raw_payload, dict) or raw_payload.get("name") != "terminal":
            continue
        if event_name == "tool" and _is_ls_command(raw_payload):
            calls.append((_tool_call_id(raw_payload), raw_payload))
        elif event_name == "tool_complete":
            completions.append((_tool_call_id(raw_payload), raw_payload))

    for call_id, _call in calls:
        for completion_id, completion in completions:
            if call_id and completion_id != call_id:
                continue
            if completion.get("is_error") is not False:
                continue
            preview = completion.get("preview")
            if isinstance(preview, str) and sentinel in preview:
                return True
    return False


def _simctl_env(token: str | None = None) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "COPILOT_GITHUB_TOKEN",
            "SIMCTL_CHILD_GITHUB_TOKEN",
            "SIMCTL_CHILD_COPILOT_GITHUB_TOKEN",
        }
    }
    if token is not None:
        env["SIMCTL_CHILD_COPILOT_GITHUB_TOKEN"] = token
    return env


def _simctl(
    args: list[str],
    *,
    token: str | None = None,
    allow_failure: bool = False,
    timeout: int = 120,
) -> str:
    env = _simctl_env(token)
    try:
        result = subprocess.run(
            ["xcrun", "simctl", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise E2EError(f"simctl {args[0]} could not complete") from exc
    if result.returncode and not allow_failure:
        raise E2EError(f"simctl {args[0]} failed with exit status {result.returncode}")
    return result.stdout.strip()


def _select_iphone_simulator() -> tuple[str, bool]:
    try:
        devices = json.loads(_simctl(["list", "devices", "available", "-j"]))
    except (json.JSONDecodeError, E2EError) as exc:
        raise E2EError("could not enumerate available iOS simulators") from exc
    candidates = [
        device
        for runtime_devices in devices.get("devices", {}).values()
        for device in runtime_devices
        if device.get("isAvailable", True) and str(device.get("name", "")).startswith("iPhone")
    ]
    if not candidates:
        raise E2EError("no available iPhone simulator")
    selected = next((device for device in candidates if device.get("state") == "Booted"), candidates[0])
    return str(selected["udid"]), selected.get("state") == "Booted"


def _request_json(path: str, payload: dict | None = None, *, timeout: int = 30) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE_URL + path, data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            decoded = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = _safe_http_error_detail(exc)
        suffix = f": {detail}" if detail else ""
        raise E2EError(f"{path} returned HTTP {exc.code}{suffix}") from None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise E2EError(f"{path} request failed") from None
    if not isinstance(decoded, dict):
        raise E2EError(f"{path} returned an invalid response")
    return decoded


def _safe_http_error_detail(error: urllib.error.HTTPError) -> str:
    """Extract a bounded JSON error message without printing response bodies or secrets."""
    try:
        payload = json.loads(error.read(4096).decode("utf-8", errors="replace"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    detail = payload.get("error", payload.get("message"))
    if not isinstance(detail, str):
        return ""
    detail = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[redacted]", detail)
    detail = re.sub(
        r"(?i)\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,})\b",
        "[redacted]",
        detail,
    )
    return " ".join(detail.split())[:400]


def _wait_for_webui(timeout_seconds: int = 180) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(BASE_URL + "/health", timeout=3) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(2)
    raise E2EError("WebUI did not become healthy on simulator port 8787")


def _read_chat_stream(stream_id: str) -> list[tuple[str, object]]:
    query = urllib.parse.urlencode({"stream_id": stream_id})
    request = urllib.request.Request(
        f"{BASE_URL}/api/chat/stream?{query}",
        headers={"Accept": "text/event-stream"},
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return list(parse_sse_events(response))
    except urllib.error.HTTPError as exc:
        raise E2EError(f"chat stream returned HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise E2EError("chat stream could not be read") from None


def _write_simulator_config(home: Path, workspace: Path) -> None:
    home.mkdir(parents=True, exist_ok=True)
    config = (
        "model:\n"
        f"  provider: {PROVIDER}\n"
        f"  default: {MODEL}\n"
        "terminal:\n"
        f"  cwd: {json.dumps(str(workspace))}\n"
    )
    (home / "config.yaml").write_text(config, encoding="utf-8", newline="\n")


def _prepare_and_launch(app_path: Path, token: str) -> tuple[str, str, Path, str]:
    info_path = app_path / "Info.plist"
    try:
        with info_path.open("rb") as info_file:
            bundle_id = plistlib.load(info_file)["CFBundleIdentifier"]
    except (OSError, KeyError, plistlib.InvalidFileException):
        raise E2EError("simulator app bundle is missing a valid bundle identifier") from None

    simulator_id, already_booted = _select_iphone_simulator()
    if not already_booted:
        _simctl(["boot", simulator_id])
    _simctl(["bootstatus", simulator_id, "-b"], timeout=300)
    _simctl(["uninstall", simulator_id, str(bundle_id)], allow_failure=True)
    _simctl(["install", simulator_id, str(app_path)], timeout=180)
    data_container = Path(_simctl(["get_app_container", simulator_id, str(bundle_id), "data"]))
    documents = data_container / "Documents"
    home = documents / "HermesHome"
    workspace = documents / "workspace"
    documents.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    sentinel = f"{PROOF_PREFIX}{uuid.uuid4().hex}.txt"
    (workspace / sentinel).write_text("simulator ls proof\n", encoding="utf-8", newline="\n")
    _write_simulator_config(home, workspace)
    _simctl(
        ["launch", "--terminate-running-process", simulator_id, str(bundle_id)],
        token=token,
        timeout=60,
    )
    return simulator_id, str(bundle_id), workspace, sentinel


def run_e2e(app_path: Path, token: str) -> None:
    simulator_id, _bundle_id, workspace, sentinel = _prepare_and_launch(app_path, token)
    try:
        print("HermesLink launched in iOS Simulator; waiting for WebUI :8787")
        _wait_for_webui()
        print(f"WebUI healthy; configuring {PROVIDER}/{MODEL}")
        created = _request_json(
            "/api/session/new",
            {
                "profile": "default",
                "workspace": str(workspace),
                "worktree": False,
                "model": MODEL,
                "model_provider": PROVIDER,
            },
        )
        session = created.get("session")
        if not isinstance(session, dict) or not session.get("session_id"):
            raise E2EError("session creation did not return a session id")
        if session.get("model") != MODEL or session.get("model_provider") != PROVIDER:
            raise E2EError("session did not retain the requested Copilot model")
        session_id = str(session["session_id"])

        yolo = _request_json("/api/session/yolo", {"session_id": session_id, "enabled": True})
        if yolo.get("yolo_enabled") is not True:
            raise E2EError("could not enable non-interactive tool approvals for the test session")

        started = _request_json(
            "/api/chat/start",
            {
                "session_id": session_id,
                "message": (
                    "Use the terminal tool to run exactly `ls -la` in the current workspace. "
                    f"Do not claim success unless its output contains `{sentinel}`."
                ),
                "model": MODEL,
                "model_provider": PROVIDER,
                "explicit_model_pick": True,
                "workspace": str(workspace),
            },
        )
        stream_id = started.get("stream_id")
        if not isinstance(stream_id, str) or not stream_id:
            raise E2EError("chat start did not return a stream id")
        events = _read_chat_stream(stream_id)
        if not has_successful_ls_tool_run(events, sentinel):
            raise E2EError("agent did not complete terminal ls with the simulator workspace proof file")
        print("PASS: Copilot conversation completed a real terminal ls and returned its workspace proof file")
    finally:
        _simctl(["shutdown", simulator_id], allow_failure=True, timeout=60)


def main() -> int:
    token = os.environ.get("COPILOT_GITHUB_TOKEN", "").strip()
    app_path = os.environ.get("SIMULATOR_APP_PATH", "").strip()
    if not token:
        print("Copilot simulator E2E requires COPILOT_GITHUB_TOKEN", file=sys.stderr)
        return 2
    if not app_path:
        print("Copilot simulator E2E requires SIMULATOR_APP_PATH", file=sys.stderr)
        return 2
    try:
        run_e2e(Path(app_path), token)
    except E2EError as error:
        print(f"Copilot simulator E2E failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
