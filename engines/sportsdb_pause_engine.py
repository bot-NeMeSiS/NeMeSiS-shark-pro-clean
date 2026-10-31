"""Reversible TheSportsDB network pause; preserves secrets and local cached data."""
from __future__ import annotations

import os
from typing import Mapping

_TRUE = {"1", "true", "yes", "on", "si", "sí"}


def sportsdb_paused(env: Mapping[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return str(source.get("THESPORTSDB_PAUSED", "false")).strip().lower() in _TRUE


def sportsdb_effective_key(env: Mapping[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    if sportsdb_paused(source):
        return ""
    return str(source.get("THESPORTSDB_KEY") or source.get("THESPORTSDB_API_KEY") or "").strip()
