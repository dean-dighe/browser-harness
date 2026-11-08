"""browser-harness filesystem layout."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def env_flag(name: str) -> bool:
    return (os.environ.get(name) or "").strip() == "1"


def dotenv_enabled() -> bool:
    """Fleet fork: BH_NO_DOTENV=1 skips the repo and workspace .env files, so only the caller's env configures a daemon."""
    return not env_flag("BH_NO_DOTENV")


def home_dir() -> Path:
    raw = os.environ.get("BH_HOME") or os.environ.get("BROWSER_HARNESS_HOME")
    if raw:
        return Path(raw).expanduser().resolve()
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return (Path(base).expanduser() / "browser-harness").resolve()
    return (Path.home() / ".config" / "browser-harness").resolve()


def ensure_private_dir(path: Path) -> Path:
    existed = path.exists()
    path.mkdir(parents=True, exist_ok=True)
    if not existed and sys.platform != "win32":
        os.chmod(path, 0o700)
    return path


def config_dir() -> Path:
    raw = os.environ.get("BH_CONFIG_DIR")
    return ensure_private_dir(Path(raw).expanduser().resolve() if raw else home_dir())


def inspect_marker() -> Path:
    """Marker recording that the harness opened a chrome://inspect tab"""
    return config_dir() / "inspect-opened"


def runtime_dir() -> Path:
    raw = os.environ.get("BH_RUNTIME_DIR")
    return ensure_private_dir(Path(raw).expanduser().resolve() if raw else home_dir() / "runtime")


def tmp_dir() -> Path:
    raw = os.environ.get("BH_TMP_DIR")
    return ensure_private_dir(Path(raw).expanduser().resolve() if raw else home_dir() / "tmp")


def workspace_dir() -> Path:
    raw = os.environ.get("BH_AGENT_WORKSPACE")
    return ensure_private_dir(Path(raw).expanduser().resolve() if raw else home_dir() / "agent-workspace")
