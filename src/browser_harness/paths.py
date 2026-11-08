"""browser-harness filesystem layout."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def env_flag(name: str) -> bool:
    return (os.environ.get(name) or "").strip() == "1"


def strict() -> bool:
    """Fleet fork: BH_STRICT_CDP=1. The harness drives only the loopback CDP endpoint it is given: no local browser
    discovery or launch, no 9222/9223 probe, no Browser Use cloud, no PyPI check, no fetch-use, no .env files."""
    return env_flag("BH_STRICT_CDP")


def dotenv_enabled() -> bool:
    """Fleet fork: BH_NO_DOTENV=1 (or strict mode) skips the repo and workspace .env files."""
    return not (env_flag("BH_NO_DOTENV") or strict())


_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def strict_refuse(what: str) -> None:
    """Raise when strict mode forbids `what` (a short name for the refused path)."""
    if strict():
        raise RuntimeError(f"strict-cdp: {what} is off (BH_STRICT_CDP=1)")


def strict_check_env(overrides=None) -> None:
    """In strict mode, require exactly one loopback CDP endpoint and no cloud settings in os.environ plus `overrides`."""
    if not strict():
        return
    from urllib.parse import urlparse
    env = {**os.environ, **(overrides or {})}
    if env.get("BU_BROWSER_ID") or env.get("BROWSER_USE_API_KEY"):
        raise RuntimeError("strict-cdp: BU_BROWSER_ID and BROWSER_USE_API_KEY must be unset (BH_STRICT_CDP=1)")
    urls = [v for v in (env.get("BU_CDP_URL"), env.get("BU_CDP_WS")) if v]
    if len(urls) != 1:
        raise RuntimeError("strict-cdp: set exactly one of BU_CDP_URL or BU_CDP_WS (BH_STRICT_CDP=1)")
    parsed = urlparse(urls[0])
    if parsed.scheme not in {"http", "ws"} or parsed.hostname not in _LOOPBACK or not parsed.port:
        raise RuntimeError("strict-cdp: the CDP endpoint must be http:// or ws:// on loopback with a port (BH_STRICT_CDP=1)")


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


def cdp_endpoint():
    """The configured CDP endpoint as host:port (lower case), or None. A daemon reports it in its ping."""
    from urllib.parse import urlparse
    url = os.environ.get("BU_CDP_URL") or os.environ.get("BU_CDP_WS")
    if not url:
        return None
    try:
        p = urlparse(url)
        return f"{(p.hostname or '').lower()}:{p.port}" if p.hostname and p.port else None
    except ValueError:
        return None


def strict_check_ws(ws_url):
    """In strict mode the WebSocket that /json/version names must be on the configured host and port (ws://)."""
    if not strict():
        return
    from urllib.parse import urlparse
    try:
        p = urlparse(ws_url)
        here = f"{(p.hostname or '').lower()}:{p.port}"
    except (TypeError, ValueError):
        here = None
    if not isinstance(ws_url, str) or p.scheme != "ws" or here != cdp_endpoint():
        raise RuntimeError("strict-cdp: /json/version named a WebSocket outside the configured endpoint (BH_STRICT_CDP=1)")


def no_redirect_opener():
    """A urllib opener that refuses every redirect: in strict mode discovery never leaves the configured endpoint."""
    import urllib.request

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise RuntimeError("strict-cdp: CDP discovery was redirected (BH_STRICT_CDP=1)")

    return urllib.request.build_opener(_NoRedirect)
