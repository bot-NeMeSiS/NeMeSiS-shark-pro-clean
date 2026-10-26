"""Shared SHARK request and persistence contracts; no Flask, SQL or provider IO."""
from __future__ import annotations

import json
import math
from collections.abc import Mapping


class SharkInputError(ValueError):
    def __init__(self, code="invalid_question"):
        self.code = code
        super().__init__(code)


def normalize_request(payload, query=None, *, require_question=True):
    """Normalize both surfaces without trusting identity/plan fields or truncating.

    Conflicting aliases, including across query/form, fail before admission. GET
    callers may accept an empty question; arbitrary GET questions are still
    governed by the route's existing read-only quick-question allowlist.
    """
    if not isinstance(payload, Mapping) or (query is not None and not isinstance(query, Mapping)):
        raise SharkInputError("invalid_body")
    sources = [payload] + ([query] if query is not None else [])

    def field(names, maximum, *, question=False):
        values = []
        for source in sources:
            for name in names:
                raw_values = source.getlist(name) if hasattr(source, "getlist") else ([source[name]] if name in source else [])
                for value in raw_values:
                    if value is None and not question:
                        continue
                    if not isinstance(value, str):
                        raise SharkInputError("invalid_question" if question else "invalid_selection")
                    if len(value) > maximum:
                        raise SharkInputError("invalid_question" if question else "invalid_selection")
                    value = value.strip()
                    if len(value) > maximum or any(ord(c) < 32 and c not in ("\n", "\r", "\t") for c in value):
                        raise SharkInputError("invalid_question" if question else "invalid_selection")
                    if not question and any(c.isspace() for c in value):
                        raise SharkInputError("invalid_selection")
                    if value:
                        values.append(value)
        if len(set(values)) > 1:
            raise SharkInputError("conflicting_question" if question else "selection_conflict")
        return values[0] if values else ""

    result = {"question": field(("question", "q"), 1000, question=True),
              "match_id": field(("match_id", "match"), 180),
              "pick_id": field(("pick_id", "pick"), 180)}
    if require_question and not result["question"]:
        raise SharkInputError("invalid_question")
    return result


def finite_json(value):
    """Unknown numeric values stay JSON null in HTTP and persisted context."""
    if type(value) is float and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: finite_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite_json(item) for item in value]
    return value


def encode_snapshot(payload, *, maximum=8000):
    """Persist valid bounded JSON, including an explicit reduction receipt.

    No textual JSON slicing: a large context is reduced to its identity/state
    envelope rather than writing an unreadable half-object or an unbounded row.
    """
    encoded = json.dumps(finite_json(payload), ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if len(encoded) <= maximum:
        return encoded
    context = payload if isinstance(payload, dict) else {}
    user = context.get("user") if isinstance(context.get("user"), dict) else {}
    reduced = {"contract": "SHARK-CONTEXT-SNAPSHOT-V2", "truncated": True,
               "original_characters": len(encoded), "execution_source": "LOCAL",
               "user": {k: str(user[k])[:180] for k in ("id", "membership") if k in user},
               "selection": {k: str((context.get(k) or {}).get("id") or "")[:180]
                             for k in ("match", "pick") if isinstance(context.get(k), dict)}}
    for key in ("match", "pick"):
        if isinstance(context.get(key), dict):
            reduced[key] = {"id": str(context[key].get("id") or "")[:180]}
    return json.dumps(reduced, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
