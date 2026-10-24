"""Read-only, user-scoped account activity from existing local records.

No navigation tracking is enabled here. `query_rows` must be the application's
local SELECT callback; `resolve_target` must resolve canonical local identities.
Neither callback may fetch providers or write. Payload URLs/names are never used.

The cursor checksum detects malformed/accidentally changed tokens; it is not an
authentication signature. Authorization remains the explicit user filter, and
the cursor anchor is revalidated in that user's visible records in the SELECT.
"""
from __future__ import annotations

import base64
from collections.abc import Mapping
import hashlib
import itertools
import json
import math
import re
from typing import Any, Callable
from urllib.parse import quote

PREVIEW_LIMIT = 7
MAX_PAGE_LIMIT = 100
MAX_CURSOR_BYTES = 768
MAX_CURSOR_JSON_BYTES = 512
_CURSOR_DOMAIN = b"NeMeSiS.client-activity.cursor.v1\x00"
_ACTIVITY_ID = re.compile(r"^[A-Za-z0-9_:-]{1,128}$")
_JULIAN = re.compile(r"^[0-9]{1,7}(?:\.[0-9]{1,17})?$")
_ENTITY_ROUTES = {"match": "/match/", "team": "/team/", "competition": "/competition/"}
_ENTITY_NAMES = {"match": "Partido", "team": "Equipo", "competition": "Competición"}
_SECTION_ROUTES = {
    "picks": ("Has revisado tus pronósticos.", "/picks"),
    "combis": ("Has abierto el constructor de combinadas.", "/combis"),
    "alerts": ("Has revisado tus alertas.", "/alertas"),
    "favorite": ("Favorito actualizado.", "/favoritos"),
}

_ACTIVITY_QUERY = """
WITH visible AS (
    SELECT id, activity_type, target_type, target_id, created_at,
           julianday(created_at) AS sort_jd,
           strftime('%Y-%m-%dT%H:%M:%fZ', created_at) AS created_at_utc
    FROM user_activity
    WHERE user_id=?
      AND LOWER(COALESCE(target_type,'')) != 'growth_funnel'
      AND substr(LOWER(COALESCE(activity_type,'')),1,7) != 'growth_'
), anchor AS (
    SELECT id, sort_jd FROM visible
    WHERE id=? AND ((?=1 AND sort_jd IS NULL) OR (?=0 AND sort_jd=?))
), metadata AS (
    SELECT COUNT(*) AS activity_total,
           CASE WHEN ?=0 OR EXISTS(SELECT 1 FROM anchor) THEN 1 ELSE 0 END AS cursor_valid
    FROM visible
), page AS (
    SELECT * FROM visible
    WHERE ?=0 OR (
      ((SELECT sort_jd FROM anchor) IS NOT NULL AND (
          sort_jd IS NULL OR sort_jd < (SELECT sort_jd FROM anchor)
          OR (sort_jd=(SELECT sort_jd FROM anchor) AND id < ? COLLATE BINARY)))
      OR ((SELECT sort_jd FROM anchor) IS NULL AND sort_jd IS NULL AND id < ? COLLATE BINARY)
    )
    ORDER BY (sort_jd IS NULL) ASC, sort_jd DESC, id COLLATE BINARY DESC
    LIMIT ?
)
SELECT metadata.activity_total, metadata.cursor_valid, page.*
FROM metadata LEFT JOIN page ON metadata.cursor_valid=1
ORDER BY (page.sort_jd IS NULL) ASC, page.sort_jd DESC, page.id COLLATE BINARY DESC
"""


def _unavailable(reason: str, limit: int = 20) -> dict[str, Any]:
    return {"state": "unavailable", "reason": reason, "items": [], "preview_items": [],
        "total": None, "total_is_exact": False, "returned_count": 0, "preview_count": 0,
        "preview_limit": PREVIEW_LIMIT, "limit": limit, "has_more": False, "next_cursor": None,
        "retry_allowed": reason in {"read_unavailable", "read_contract_invalid"},
        "enrichment_state": "not_run"}


def _user_fingerprint(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()


def _canonical_cursor(data: dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _cursor_checksum(data: dict[str, Any]) -> str:
    return hashlib.sha256(_CURSOR_DOMAIN + _canonical_cursor(data)).hexdigest()


def _encode_cursor(user_id: str, item: Mapping[str, Any]) -> str:
    julian = item.get("sort_jd")
    data = {"v": 1, "u": _user_fingerprint(user_id), "i": str(item["id"]),
            "j": format(float(julian), ".17g") if julian is not None else None}
    data["c"] = _cursor_checksum(data)
    return base64.urlsafe_b64encode(_canonical_cursor(data)).decode("ascii").rstrip("=")


def _decode_cursor(value: Any, user_id: str) -> dict[str, Any] | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not 0 < len(value) <= MAX_CURSOR_BYTES or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("cursor_invalid")
    raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    if (len(raw) > MAX_CURSOR_JSON_BYTES
            or base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=") != value):
        raise ValueError("cursor_invalid")
    data = json.loads(raw)
    if (not isinstance(data, dict) or set(data) != {"v", "u", "i", "j", "c"}
            or type(data["v"]) is not int or data["v"] != 1 or data["u"] != _user_fingerprint(user_id)
            or not isinstance(data["i"], str) or not _ACTIVITY_ID.fullmatch(data["i"])):
        raise ValueError("cursor_invalid")
    if _canonical_cursor(data) != raw:
        raise ValueError("cursor_invalid")
    checksum = data.pop("c")
    if not isinstance(checksum, str) or checksum != _cursor_checksum(data):
        raise ValueError("cursor_invalid")
    julian = data["j"]
    if julian is not None:
        if not isinstance(julian, str) or not _JULIAN.fullmatch(julian):
            raise ValueError("cursor_invalid")
        number = float(julian)
        if not math.isfinite(number) or not 0 <= number <= 5373484.5:
            raise ValueError("cursor_invalid")
        data["jd_value"] = number
    else:
        data["jd_value"] = None
    return data


def _safe_entity_id(value: Any) -> str | None:
    if not isinstance(value, str) or not 0 < len(value) <= 128 or value != value.strip():
        return None
    if value in {".", ".."} or any(char in value for char in "/\\?#%") or any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    return value


def _resolve_item(row: Mapping[str, Any], resolve_target: Callable | None) -> tuple[dict[str, Any], bool]:
    kind = str(row.get("activity_type") or "").lower()[:64]
    target = str(row.get("target_type") or "").lower()[:64]
    raw_target_id = row.get("target_id")
    target_id = raw_target_id if isinstance(raw_target_id, str) and len(raw_target_id) <= 256 else ""
    known_date = row.get("sort_jd") is not None
    result = {"id": str(row["id"]), "activity_type": kind, "target_type": target,
        "target_id": target_id, "label": "Actividad registrada en tu cuenta.",
        "target_name": "", "canonical_target_id": "", "href": None, "target_state": "unknown",
        "created_at": str(row.get("created_at") or "")[:128] if known_date else "",
        "created_at_utc": str(row.get("created_at_utc") or "") if known_date else "",
        "date_state": "known" if known_date else "unknown",
        "date_label": "" if known_date else "Fecha no establecida"}
    if target in _SECTION_ROUTES:
        result["label"], result["href"] = _SECTION_ROUTES[target]
        result["target_state"] = "section"
        return result, False
    if target not in _ENTITY_ROUTES:
        return result, False
    noun = _ENTITY_NAMES[target]
    result["label"] = f"{noun} no disponible."
    if resolve_target is None or not target_id:
        return result, False
    try:
        identity = resolve_target(target, target_id)
    except Exception:
        result["target_state"] = "unavailable"
        return result, True
    if not isinstance(identity, Mapping) or identity.get("verified") is not True:
        if isinstance(identity, Mapping) and identity.get("state") in {"deleted", "ambiguous", "unknown", "unavailable"}:
            result["target_state"] = identity["state"]
        return result, False
    if identity.get("target_type") != target or identity.get("target_id") != target_id:
        result["target_state"] = "unavailable"
        return result, True
    canonical_id = identity.get("canonical_id")
    if canonical_id is None:
        direct = identity.get("id", identity.get("key"))
        canonical_id = direct if direct == target_id else None
    canonical_id = _safe_entity_id(canonical_id)
    name = identity.get("name")
    if canonical_id is None or not isinstance(name, str) or not 0 < len(name.strip()) <= 240:
        result["target_state"] = "unavailable"
        return result, True
    # Plain text only: callers must use normal template escaping, never |safe.
    name = str(name).strip()
    result.update(target_name=name, canonical_target_id=canonical_id, target_state="available",
                  href=_ENTITY_ROUTES[target] + quote(canonical_id, safe=""))
    action = "consultada" if target == "competition" else "consultado"
    result["label"] = (f"Favorito actualizado: {name}." if kind == "favorite"
                       else f"{noun} {action}: {name}." if kind == "view"
                       else f"{noun}: {name}.")
    return result, False


def build_client_activity_snapshot(query_rows: Callable, *, user_id: Any, limit: int = 20,
        cursor: Any = None, resolve_target: Callable | None = None) -> dict[str, Any]:
    """One user/growth-filtered SELECT yields exact total and bounded page.

    user_id must come from the authenticated caller context, not a query string.
    The optional resolver must return verified=True, matching target_type and
    target_id, canonical_id (or matching direct id/key), and a real local name.
    Its href and every user_activity payload are ignored. Do not use this module
    to enable browsing tracking, create records, or infer a deleted identity.
    """
    if (not isinstance(user_id, str) or not 0 < len(user_id) <= 256
            or any(ord(char) < 32 or ord(char) == 127 for char in user_id)):
        return _unavailable("user_required")
    if type(limit) is not int or not 1 <= limit <= MAX_PAGE_LIMIT:
        return _unavailable("limit_invalid")
    try:
        anchor = _decode_cursor(cursor, user_id)
    except (ValueError, TypeError, UnicodeError):
        return _unavailable("cursor_invalid", limit)
    anchor_id = anchor["i"] if anchor else ""
    anchor_jd = anchor["jd_value"] if anchor else None
    unknown = int(anchor is not None and anchor_jd is None)
    has_cursor = int(anchor is not None)
    params = (user_id, anchor_id, unknown, unknown, anchor_jd, has_cursor,
              has_cursor, anchor_id, anchor_id, limit + 1)
    try:
        raw_rows = query_rows(_ACTIVITY_QUERY, params)
        data = [dict(row) for row in itertools.islice(iter(raw_rows), limit + 2)]
    except Exception:
        return _unavailable("read_unavailable", limit)
    if not data or len(data) > limit + 1:
        return _unavailable("read_contract_invalid", limit)
    total = data[0].get("activity_total")
    cursor_valid = data[0].get("cursor_valid")
    if type(total) is not int or total < 0 or type(cursor_valid) is not int or cursor_valid not in (0, 1):
        return _unavailable("read_contract_invalid", limit)
    if any(row.get("activity_total") != total or row.get("cursor_valid") != cursor_valid for row in data):
        return _unavailable("read_contract_invalid", limit)
    if not cursor_valid:
        return _unavailable("cursor_invalid", limit)
    page = [row for row in data if row.get("id") is not None]
    if any(not isinstance(row["id"], str) or not _ACTIVITY_ID.fullmatch(row["id"]) for row in page):
        return _unavailable("read_contract_invalid", limit)
    if (total == 0 and page) or len(page) > total:
        return _unavailable("read_contract_invalid", limit)
    has_more = len(page) > limit
    selected = page[:limit]
    target_cache: dict[tuple[str, str], tuple[bool, Any]] = {}
    def cached_resolver(target: str, identifier: str):
        key = (target, identifier)
        if key not in target_cache:
            try:
                target_cache[key] = (True, resolve_target(target, identifier))
            except Exception:
                target_cache[key] = (False, None)
        succeeded, value = target_cache[key]
        if not succeeded:
            raise RuntimeError("local_target_resolution_unavailable")
        return value
    effective_resolver = cached_resolver if resolve_target is not None else None
    resolved = [_resolve_item(row, effective_resolver) for row in selected]
    items = [item for item, _error in resolved]
    partial = any(error for _item, error in resolved)
    return {"state": "available" if total else "empty", "reason": "some_targets_unavailable" if partial else "",
        "items": items, "preview_items": items[:PREVIEW_LIMIT], "total": total, "total_is_exact": True,
        "returned_count": len(items), "preview_count": min(len(items), PREVIEW_LIMIT),
        "preview_limit": PREVIEW_LIMIT, "limit": limit, "has_more": has_more,
        "next_cursor": _encode_cursor(user_id, selected[-1]) if has_more and selected else None,
        "retry_allowed": partial, "enrichment_state": "partial" if partial else "complete",
        "tracking_enabled_by_this_read": False}
