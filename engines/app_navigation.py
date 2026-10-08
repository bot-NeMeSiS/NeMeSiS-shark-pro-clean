"""Pure navigation matching; no provider calls, session writes or storage reads."""
from __future__ import annotations

import unicodedata


def navigation_matches(label: str, query: str) -> bool:
    def normalized(value):
        return "".join(c for c in unicodedata.normalize("NFD", str(value or ""))
                       if unicodedata.category(c) != "Mn").casefold()

    return all(word in normalized(label) for word in normalized(query[:90]).split())
