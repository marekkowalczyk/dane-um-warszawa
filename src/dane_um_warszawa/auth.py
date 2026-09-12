"""Load a dane.um.warszawa.pl JWT without printing the full token."""

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_KEY_FILE = Path.home() / "Downloads" / "apiKey.txt"


class MissingApiKey(RuntimeError):
    """Raised when no JWT can be loaded from argument, env, or file."""


def redact_key(key: str) -> str:
    """Return a log-safe preview; never the full token."""
    if not key:
        return "<empty>"
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}…{key[-4:]}"


def load_api_key(*, api_key: str | None = None, key_file: str | Path | None = None) -> str:
    """Resolve the JWT from an argument, ``UM_WARSZAWA_API_KEY``, or a key file.

    File lookup order when ``key_file`` is omitted: ``DANE_UM_KEY_FILE``, then
    ``~/Downloads/apiKey.txt``.
    """
    if api_key is not None and str(api_key).strip():
        return str(api_key).strip()

    if key_file is not None:
        return _read_key_file(Path(key_file))

    env_key = os.environ.get("UM_WARSZAWA_API_KEY", "").strip()
    if env_key:
        return env_key

    env_path = os.environ.get("DANE_UM_KEY_FILE", "").strip()
    path = Path(env_path) if env_path else DEFAULT_KEY_FILE
    return _read_key_file(path)


def _read_key_file(path: Path) -> str:
    path = path.expanduser()
    if path.is_file():
        text = path.read_text(encoding="utf-8").strip()
        if text:
            return text
    raise MissingApiKey(
        "No dane.um.warszawa.pl JWT found. Set UM_WARSZAWA_API_KEY, "
        "or put the token in DANE_UM_KEY_FILE "
        f"(default {DEFAULT_KEY_FILE}). Get a key at "
        "https://dane.um.warszawa.pl/pl/key-api"
    )
