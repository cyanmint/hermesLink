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
    # The bundled Agent lives inside hermesrt.zip.  Extract it to the writable
    # HERMES_HOME so filesystem-based config/discovery code can use it on iOS.
    _origin = str(Path(__file__).resolve()).replace(os.sep, "/")
    if ".zip/" in _origin:
        _archive = Path(_origin.split(".zip/", 1)[0] + ".zip")
        _target = Path(os.getenv("HERMES_HOME", str(Path.home()))) / "HermesAgent"
        try:
            with zipfile.ZipFile(_archive) as _bundle:
                _prefix = "hermes/"
                for _name in _bundle.namelist():
                    if not _name.startswith(_prefix) or _name.endswith("/"):
                        continue
                    _destination = _target / _name[len(_prefix):]
                    _destination.parent.mkdir(parents=True, exist_ok=True)
                    _data = _bundle.read(_name)
                    if not _destination.exists() or _destination.read_bytes() != _data:
                        _destination.write_bytes(_data)
            return _target
        except (OSError, KeyError, zipfile.BadZipFile):
            pass
'''
if 'The bundled Agent lives at hermesrt.zip/hermes.' not in text:
    if anchor not in text:
        raise SystemExit("agent discovery anchor not found")
    text = text.replace(anchor, injection, 1)

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
