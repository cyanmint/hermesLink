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

# Inject at the start of the discovery function, before filesystem candidates.
anchor = 'def _discover_agent_dir() -> Path:\n'
injection = '''def _discover_agent_dir() -> Path:
    # Point zipimport at the bundled Agent directly; never duplicate its source
    # tree into the writable HERMES_HOME.
    _origin = str(Path(__file__).resolve()).replace(os.sep, "/")
    if ".zip/" in _origin:
        _archive = Path(_origin.split(".zip/", 1)[0] + ".zip")
        try:
            with zipfile.ZipFile(_archive) as _bundle:
                _bundle.getinfo("hermes/hermes_cli/main.py")
            return Path(str(_archive) + "/hermes")
        except (OSError, KeyError, zipfile.BadZipFile):
            pass
'''
if "Point zipimport at the bundled Agent directly" not in text:
    if anchor not in text:
        raise SystemExit("agent discovery anchor not found")
    text = text.replace(anchor, injection, 1)

# Replace the older iOS injection when upgrading an already-patched runtime.
legacy_agent_comment = "    # The bundled Agent lives inside hermesrt.zip.  Extract it to the writable\n"
legacy_agent_end = '    """\n    Locate the hermes-agent checkout'
if legacy_agent_comment in text:
    legacy_start = text.index(legacy_agent_comment)
    legacy_end = text.find(legacy_agent_end, legacy_start)
    if legacy_end < 0:
        raise SystemExit("legacy agent extraction block terminator not found")
    text = text[:legacy_start] + text[legacy_end:]

workspace_anchor = 'LAST_WORKSPACE_FILE = STATE_DIR / "last_workspace.txt"\n'
workspace_migration = '''LAST_WORKSPACE_FILE = STATE_DIR / "last_workspace.txt"


def _migrate_legacy_workspace_state() -> None:
    """Move persisted default-workspace pointers from ~/workspace to Documents/workspace."""
    configured = os.getenv("HERMES_WEBUI_DEFAULT_WORKSPACE", "").strip()
    if not configured:
        return
    try:
        _preferred = str(Path(configured).expanduser().resolve())
        _legacy = str((Path(HOME).expanduser() / "workspace").resolve())
        if _preferred == _legacy:
            return

        def _is_legacy(value: object) -> bool:
            if not isinstance(value, str) or not value.strip():
                return False
            try:
                return str(Path(value).expanduser().resolve()) == _legacy
            except (OSError, RuntimeError, ValueError):
                return False

        def _write_json(path: Path, value: object) -> None:
            _temporary = path.with_name(path.name + ".tmp")
            _temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
            os.replace(_temporary, path)

        try:
            _settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(_settings, dict) and _is_legacy(_settings.get("default_workspace")):
                _settings["default_workspace"] = _preferred
                _write_json(SETTINGS_FILE, _settings)
        except (OSError, ValueError, TypeError):
            pass

        try:
            _workspaces = json.loads(WORKSPACES_FILE.read_text(encoding="utf-8"))
            if isinstance(_workspaces, list):
                _changed = False
                for _workspace in _workspaces:
                    if isinstance(_workspace, dict) and _is_legacy(_workspace.get("path")):
                        _workspace["path"] = _preferred
                        _changed = True
                if _changed:
                    _write_json(WORKSPACES_FILE, _workspaces)
        except (OSError, ValueError, TypeError):
            pass

        try:
            if _is_legacy(LAST_WORKSPACE_FILE.read_text(encoding="utf-8").strip()):
                _temporary = LAST_WORKSPACE_FILE.with_name(LAST_WORKSPACE_FILE.name + ".tmp")
                _temporary.write_text(_preferred + "\\n", encoding="utf-8")
                os.replace(_temporary, LAST_WORKSPACE_FILE)
        except OSError:
            pass
    except (OSError, RuntimeError, ValueError):
        pass


_migrate_legacy_workspace_state()
'''
if "def _migrate_legacy_workspace_state()" not in text:
    if workspace_anchor not in text:
        raise SystemExit("workspace state migration anchor not found")
    text = text.replace(workspace_anchor, workspace_migration, 1)

path.write_text(text, encoding="utf-8", newline="\n")
