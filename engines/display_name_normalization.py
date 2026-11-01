"""Bounded memoization of deterministic display-name text, never identity proof.

Callers still resolve current provider aliases, categories, observations and
permissions. Every input's truth/string conversion occurs before the cache;
only short, exact immutable strings enter it. Long and custom values keep the
uncached path and its errors. No rows, clocks, contexts or user roles are held.
"""
from functools import lru_cache
import re
import unicodedata

_NON_WORDS = re.compile(r"[^a-z0-9]+")
_CACHE_ENTRIES = 2048
_CACHE_TEXT_CHARS = 128

def _normalize_text(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    # Each maximal non-word run becomes one space, so no whitespace run remains.
    return _NON_WORDS.sub(" ", text).strip()

@lru_cache(maxsize=_CACHE_ENTRIES)
def _normalize_short_text(text):
    return _normalize_text(text)

def display_name_key(value):
    text = str(value or "").strip().lower()
    if type(text) is str and len(text) <= _CACHE_TEXT_CHARS:
        return _normalize_short_text(text)
    return _normalize_text(text)
