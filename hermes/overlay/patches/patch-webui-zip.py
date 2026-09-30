# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
if "import zipfile\n" not in text:
    text = text.replace("import sys\n", "import sys\nimport zipfile\n", 1)
host_anchor = 'HOST = os.getenv("HERMES_WEBUI_HOST", "127.0.0.1")\nPORT = int(os.getenv("HERMES_WEBUI_PORT", "8787"))\n'
host_replacement = '''def _cli_override(name: str, default: str) -> str:
    try:
        index = sys.argv.index(name)
        return sys.argv[index + 1]
    except (ValueError, IndexError):
        return default


HOST = _cli_override("--host", os.getenv("HERMES_WEBUI_HOST", "127.0.0.1"))
PORT = int(_cli_override("--port", os.getenv("HERMES_WEBUI_PORT", "8787")))
'''
if host_anchor in text:
    text = text.replace(host_anchor, host_replacement, 1)
if "_BUNDLED_STATIC_ROOT" not in text:
    old = '''def get_static_root() -> Path:
    return REPO_ROOT / "static"
'''
    new = '''_BUNDLED_STATIC_ROOT: Path | None = None


def get_static_root() -> Path:
    """Return a filesystem root for static assets, including ZIP bundles."""
    global _BUNDLED_STATIC_ROOT
    direct = REPO_ROOT / "static"
    if direct.is_dir():
        return direct
    if _BUNDLED_STATIC_ROOT is not None:
        return _BUNDLED_STATIC_ROOT
    origin = str(Path(__file__).resolve()).replace(os.sep, "/")
    marker = ".zip/"
    if marker not in origin:
        return direct
    archive_name, inside = origin.split(marker, 1)
    archive = Path(archive_name + ".zip")
    if not archive.is_file():
        return direct
    prefix = inside.split("api/", 1)[0] + "static/"
    target = Path(os.getenv("HERMES_HOME", str(archive.parent))) / "WebUIStatic"
    import zipfile
    try:
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if not name.startswith(prefix) or name.endswith("/"):
                    continue
                destination = target / name[len(prefix):]
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists() or destination.stat().st_size != bundle.getinfo(name).file_size:
                    destination.write_bytes(bundle.read(name))
    except (OSError, KeyError, zipfile.BadZipFile):
        return direct
    if (target / "index.html").is_file():
        _BUNDLED_STATIC_ROOT = target
        return target
    return direct
'''
    if old not in text:
        raise SystemExit("get_static_root patch anchor not found")
    text = text.replace(old, new, 1)

agent_marker = "# iOS ZIP runtime: the agent is importable from the outer archive.\n"
agent_block = '''# iOS ZIP runtime: the agent is importable from the outer archive.
if "_discover_agent_dir" in text:
    pass
'''
# Inject at the start of the discovery function, before filesystem candidates.
anchor = 'def _discover_agent_dir() -> Path:\n'
injection = '''def _discover_agent_dir() -> Path:
    # The bundled Agent is already importable through zipimport.
    _origin = str(Path(__file__).resolve()).replace(os.sep, "/")
    if ".zip/" in _origin:
        _archive = Path(_origin.split(".zip/", 1)[0] + ".zip")
        _bundled_agent = Path(str(_archive) + "/hermes")
        if _archive.is_file():
            _explicit_agent = os.environ.get("HERMES_WEBUI_AGENT_DIR")
            if _explicit_agent:
                _explicit_path = Path(_explicit_agent).expanduser().resolve()
                if _explicit_path.exists() and _looks_like_agent_source_root(_explicit_path):
                    return _explicit_path
            return _bundled_agent
'''
if "The bundled Agent is already importable through zipimport." not in text:
    if anchor not in text:
        raise SystemExit("agent discovery anchor not found")
    text = text.replace(anchor, injection, 1)

workspace_candidates_anchor = '''def _workspace_candidates(raw: str | Path | None = None) -> list[Path]:
    """Return ordered candidate workspace paths, de-duplicated."""
    candidates: list[Path] = []
'''
workspace_candidates_injection = '''def _workspace_candidates(raw: str | Path | None = None) -> list[Path]:
    """Return ordered candidate workspace paths, de-duplicated."""
    ios_documents_root = os.environ.get("HERMES_IOS_DOCUMENTS_ROOT")
    if ios_documents_root:
        workspace = (Path(ios_documents_root) / "workspace").expanduser().resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        return [workspace]
    candidates: list[Path] = []
'''
if 'ios_documents_root = os.environ.get("HERMES_IOS_DOCUMENTS_ROOT")' not in text:
    if workspace_candidates_anchor not in text:
        raise SystemExit("config workspace discovery patch anchor not found")
    text = text.replace(
        workspace_candidates_anchor, workspace_candidates_injection, 1
    )

path.write_text(text, encoding="utf-8", newline="\n")

if len(sys.argv) > 2:
    workspace_path = Path(sys.argv[2])
    workspace_text = workspace_path.read_text(encoding="utf-8")

    ios_workspace_helper = '''def _ios_documents_workspace() -> str | None:
    documents_root = os.environ.get("HERMES_IOS_DOCUMENTS_ROOT")
    if not documents_root:
        return None
    workspace = Path(documents_root) / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return str(_resolve_path(workspace))


'''
    if "def _ios_documents_workspace() -> str | None:" not in workspace_text:
        workspace_text = workspace_text.replace(
            "def _profile_default_workspace() -> str:\n",
            ios_workspace_helper + "def _profile_default_workspace() -> str:\n",
            1,
        )

    workspace_default_anchor = "def _profile_default_workspace() -> str:\n"
    workspace_default_injection = '''def _profile_default_workspace() -> str:
    ios_workspace = _ios_documents_workspace()
    if ios_workspace:
        return ios_workspace
    ios_default_workspace = os.environ.get("HERMES_WEBUI_DEFAULT_WORKSPACE")
    if ios_default_workspace:
        return str(_resolve_path(ios_default_workspace))
'''
    if "ios_workspace = _ios_documents_workspace()" not in workspace_text:
        if workspace_default_anchor not in workspace_text:
            raise SystemExit("workspace default selection patch anchor not found")
        workspace_text = workspace_text.replace(
            workspace_default_anchor, workspace_default_injection, 1
        )

    for function_name, signature, variable in (
        (
            "get_profile_default_workspace",
            "def get_profile_default_workspace() -> str:\n",
            "ios_profile_workspace",
        ),
        ("get_last_workspace", "def get_last_workspace() -> str:\n", "ios_last_workspace"),
    ):
        ios_override = (
            f"    {variable} = _ios_documents_workspace()\n"
            f"    if {variable}:\n"
            f"        return {variable}\n"
        )
        if variable not in workspace_text:
            if signature not in workspace_text:
                raise SystemExit(f"{function_name} patch anchor not found")
            workspace_text = workspace_text.replace(signature, signature + ios_override, 1)

    resolver_anchor = '''    candidate = _resolve_path(path)

    access_error = _workspace_access_error(candidate)
'''
    resolver_replacement = '''    ios_workspace = _ios_documents_workspace()
    candidate = Path(ios_workspace) if ios_workspace else _resolve_path(path)

    access_error = _workspace_access_error(candidate)
'''
    if "candidate = Path(ios_workspace) if ios_workspace else _resolve_path(path)" not in workspace_text:
        if resolver_anchor not in workspace_text:
            raise SystemExit("trusted workspace candidate patch anchor not found")
        workspace_text = workspace_text.replace(resolver_anchor, resolver_replacement, 1)

    workspace_api_overrides = (
        (
            "load_workspaces",
            "def load_workspaces() -> list:\n",
            '''    ios_loaded_workspaces = _ios_documents_workspace()
    if ios_loaded_workspaces:
        return [{"path": ios_loaded_workspaces, "name": "Home"}]
''',
        ),
        (
            "save_workspaces",
            "def save_workspaces(workspaces: list) -> None:\n",
            '''    ios_save_workspace = _ios_documents_workspace()
    if ios_save_workspace:
        workspaces = [{"path": ios_save_workspace, "name": "Home"}]
''',
        ),
        (
            "set_last_workspace",
            "def set_last_workspace(path: str) -> None:\n",
            '''    ios_last_workspace_to_save = _ios_documents_workspace()
    if ios_last_workspace_to_save:
        path = ios_last_workspace_to_save
''',
        ),
        (
            "list_workspace_suggestions",
            "def list_workspace_suggestions(prefix: str = \"\", limit: int = 12) -> list[str]:\n",
            '''    ios_suggested_workspace = _ios_documents_workspace()
    if ios_suggested_workspace:
        return [ios_suggested_workspace]
''',
        ),
        (
            "validate_workspace_to_add",
            "def validate_workspace_to_add(path: str) -> Path:\n",
            '''    ios_added_workspace = _ios_documents_workspace()
    if ios_added_workspace:
        return Path(ios_added_workspace)
''',
        ),
    )
    for function_name, signature, injection in workspace_api_overrides:
        marker = injection.splitlines()[0]
        if marker not in workspace_text:
            if signature not in workspace_text:
                raise SystemExit(f"{function_name} patch anchor not found")
            workspace_text = workspace_text.replace(signature, signature + injection, 1)

    saved_workspace_anchor = '''        if Path(raw).is_dir():
            return raw
'''
    saved_workspace_injection = '''        candidate = _resolve_path(raw)
        if _is_blocked_workspace_path(candidate, raw):
            return None
        if candidate.is_dir():
            return raw
'''
    if saved_workspace_anchor in workspace_text:
        workspace_text = workspace_text.replace(
            saved_workspace_anchor, saved_workspace_injection
        )
    elif "if _is_blocked_workspace_path(candidate, raw):" not in workspace_text:
        raise SystemExit("saved workspace validation patch anchor not found")

    workspace_list_anchor = "        # Skip paths inside a DIFFERENT profile's directory"
    workspace_list_injection = '''        if _is_blocked_workspace_path(p, path):
            continue
        # Skip paths inside a DIFFERENT profile's directory'''
    if workspace_list_anchor in workspace_text:
        workspace_text = workspace_text.replace(
            workspace_list_anchor, workspace_list_injection, 1
        )
    elif "if _is_blocked_workspace_path(p, path):" not in workspace_text:
        raise SystemExit("saved workspace list validation patch anchor not found")

    workspace_anchor = '''    raw = None
    if raw_path not in (None, ""):
'''
    workspace_injection = '''    ios_documents_root = os.environ.get("HERMES_IOS_DOCUMENTS_ROOT")
    try:
        resolved_candidate = candidate.resolve()
    except (OSError, RuntimeError):
        resolved_candidate = candidate

    if ios_documents_root:
        try:
            documents_root = Path(ios_documents_root).resolve()
        except (OSError, RuntimeError):
            pass
        else:
            if resolved_candidate == documents_root or documents_root in resolved_candidate.parents:
                return False

    ios_home_root = os.environ.get("HERMES_IOS_HOME_ROOT") or os.environ.get("HOME")
    if ios_home_root:
        try:
            home_root = Path(ios_home_root).resolve()
        except (OSError, RuntimeError):
            pass
        else:
            if resolved_candidate == home_root or home_root in resolved_candidate.parents:
                return True

    raw = None
    if raw_path not in (None, ""):
'''
    if workspace_anchor in workspace_text:
        workspace_text = workspace_text.replace(workspace_anchor, workspace_injection, 1)
    elif "HERMES_IOS_DOCUMENTS_ROOT" not in workspace_text:
        raise SystemExit("workspace path validation patch anchor not found")
    workspace_path.write_text(workspace_text, encoding="utf-8", newline="\n")

if len(sys.argv) > 3:
    onboarding_path = Path(sys.argv[3])
    onboarding_text = onboarding_path.read_text(encoding="utf-8")
    model_anchor = '''  const provider=(ONBOARDING.form.provider||'').trim();
  const model=(ONBOARDING.form.model||'').trim();
'''
    model_replacement = '''  const provider=(ONBOARDING.form.provider||'').trim();
  const setupProvider=_getOnboardingSetupProvider(provider);
  const model=(ONBOARDING.form.model||(_getOnboardingCurrentSetup()||{}).model||(setupProvider&&setupProvider.default_model)||'').trim();
'''
    if "setupProvider&&setupProvider.default_model" not in onboarding_text:
        if model_anchor not in onboarding_text:
            raise SystemExit("onboarding model fallback patch anchor not found")
        onboarding_text = onboarding_text.replace(model_anchor, model_replacement, 1)

    setup_body_anchor = '''  const body={provider,model};
'''
    setup_body_replacement = '''  if(!model) throw new Error(t('onboarding_error_model_required')||'A model is required.');
  const body={provider,model};
'''
    if "if(!model) throw new Error(t('onboarding_error_model_required')" not in onboarding_text:
        if setup_body_anchor not in onboarding_text:
            raise SystemExit("onboarding setup payload patch anchor not found")
        onboarding_text = onboarding_text.replace(setup_body_anchor, setup_body_replacement, 1)
    onboarding_path.write_text(onboarding_text, encoding="utf-8", newline="\n")

if len(sys.argv) > 4:
    server_path = Path(sys.argv[4])
    server_text = server_path.read_text(encoding="utf-8")
    verbose_marker = "_WEBUI_VERBOSE = any(arg in (\"--verbose\", \"-v\")"
    verbose_helpers = '''_WEBUI_VERBOSE = any(arg in ("--verbose", "-v") for arg in sys.argv[1:])


def _verbose_request_stalled(method: str, path: str, request_thread, started: float) -> None:
    thread_id = request_thread.ident
    frame = sys._current_frames().get(thread_id) if thread_id is not None else None
    if frame is None or not request_thread.is_alive():
        return
    elapsed = time.monotonic() - started
    print(
        f"[webui][verbose] request still running method={method} path={path} "
        f"thread={thread_id} elapsed={elapsed:.1f}s",
        flush=True,
    )
    traceback.print_stack(frame, file=sys.stderr)


'''
    if verbose_marker not in server_text:
        logger_anchor = 'logger = logging.getLogger(__name__)\n'
        if logger_anchor not in server_text:
            raise SystemExit("WebUI logger patch anchor not found")
        server_text = server_text.replace(
            logger_anchor, logger_anchor + "\n" + verbose_helpers, 1
        )

    request_anchor = '''            result = route_func(self, parsed)
            if result is False:
'''
    request_replacement = '''            verbose_started = time.monotonic()
            verbose_timer = None
            if _WEBUI_VERBOSE:
                content_length = self.headers.get("Content-Length", "unknown")
                print(
                    f"[webui][verbose] request started method={self.command} "
                    f"path={parsed.path} thread={threading.get_ident()} "
                    f"content_length={content_length[:32]}",
                    flush=True,
                )
                if parsed.path == "/api/session/draft":
                    verbose_timer = threading.Timer(
                        5.0,
                        _verbose_request_stalled,
                        args=(self.command, parsed.path, threading.current_thread(), verbose_started),
                    )
                    verbose_timer.daemon = True
                    verbose_timer.start()
            try:
                result = route_func(self, parsed)
            finally:
                if verbose_timer is not None:
                    verbose_timer.cancel()
                if _WEBUI_VERBOSE:
                    elapsed = time.monotonic() - verbose_started
                    print(
                        f"[webui][verbose] request finished method={self.command} "
                        f"path={parsed.path} elapsed={elapsed:.3f}s",
                        flush=True,
                    )
            if result is False:
'''
    if "[webui][verbose] request started" not in server_text:
        if request_anchor not in server_text:
            raise SystemExit("WebUI write request logging patch anchor not found")
        server_text = server_text.replace(request_anchor, request_replacement, 1)
    server_path.write_text(server_text, encoding="utf-8", newline="\n")
