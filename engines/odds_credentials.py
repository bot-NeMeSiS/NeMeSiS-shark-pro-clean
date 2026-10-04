"""GET-only credential selection. Secrets stay in the transport call's locals."""
from contextlib import contextmanager
from contextvars import ContextVar
import json
import os
import urllib.error
import urllib.parse

from engines.odds_provider_errors import KNOWN_ODDS_ERROR_CODES
from engines.cron_request_budget import exhausted

NAMES = {"PAID": "THE_ODDS_API_KEY_PAID", "FREE": "THE_ODDS_API_KEY_FREE",
         "LEGACY": "THE_ODDS_API_KEY"}
AUTH_CODES = frozenset({"INVALID_KEY", "DEACTIVATED_KEY", "UNAUTHORIZED"})
_SELECTION = ContextVar("odds_credential_tier", default=None)


def configured_tiers():
    return [tier for tier, name in NAMES.items() if bool(os.getenv(name, "").strip())]


def selected_tier():
    return _SELECTION.get() or next(iter(configured_tiers()), "")


def free_profile(tier=None):
    tier = selected_tier() if tier is None else tier
    return tier == "FREE" or (tier == "LEGACY" and os.getenv("ODDS_LEGACY_PROFILE", "FREE").upper() != "PAID")


def positive_setting(name, default):
    try:
        return max(1, int(os.getenv(name, str(default))))
    except (ValueError, TypeError):
        return default


@contextmanager
def refresh_selection():
    token = _SELECTION.set("")
    try:
        yield
    finally:
        _SELECTION.reset(token)


def profile_params(params, tier):
    result = dict(params or {})
    if free_profile(tier):
        if "regions" in result:
            regions = [r.strip() for r in result["regions"].split(",") if r.strip()]
            result["regions"] = ",".join(regions[:positive_setting("ODDS_FREE_MAX_REGIONS", 1)])
        if "markets" in result:
            markets = [m.strip() for m in result["markets"].split(",") if m.strip()]
            if "h2h" in markets:
                markets = ["h2h"] + [m for m in markets if m != "h2h"]
            result["markets"] = ",".join(markets[:positive_setting("ODDS_FREE_MAX_MARKETS", 1)])
    return result


def _integer(value):
    try:
        return max(0, int(value)) if value is not None else None
    except (ValueError, TypeError, OverflowError):
        return None


def _attempt(tier, path, params, transport):
    query = profile_params(params, tier)
    query["apiKey"] = os.getenv(NAMES[tier], "").strip()
    url = "https://api.the-odds-api.com/v4/" + path.strip("/") + "?" + urllib.parse.urlencode(query)
    result = {"ok": False, "payload": {}, "http_status": 0, "quota": {},
              "error": "", "error_code": ""}
    try:
        response = transport(url, timeout=12)
        result.update(ok=True, payload=response.get("payload"),
                      http_status=_integer(response.get("http_status")) or 200)
        headers = response.get("headers") or {}
    except Exception as exc:
        result["error"] = type(exc).__name__ if type(exc).__name__ in {
            "HTTPError", "TimeoutError", "URLError", "CronTimeBudget", "JSONDecodeError"
        } else "ProviderError"
        result["http_status"] = _integer(getattr(exc, "code", 0)) or 0
        headers = {}
        if isinstance(exc, urllib.error.HTTPError):
            raw_headers = exc.headers or {}
            headers = {field: raw_headers.get("x-" + field.replace("_", "-"))
                       for field in ("requests_used", "requests_remaining", "requests_last")}
            try:
                code = json.loads(exc.read(2048).decode("utf-8")).get("error_code")
                if isinstance(code, str) and code in KNOWN_ODDS_ERROR_CODES:
                    result["error_code"] = code
            except Exception:
                pass
    result["quota"] = {field: _integer(headers.get(field))
                       for field in ("requests_used", "requests_remaining", "requests_last")}
    return result


def request(path, params, transport, free_allowed=lambda: True):
    if _SELECTION.get() is not None:
        return _request(path, params, transport, free_allowed)
    with refresh_selection():
        return _request(path, params, transport, free_allowed)


def _request(path, params, transport, free_allowed):
    tiers = configured_tiers()
    current = selected_tier()
    if current in tiers:
        tiers = tiers[tiers.index(current):]
    if not tiers:
        return {"ok": False, "payload": {}, "http_status": 0, "quota": {},
                "error": "missing_key", "error_code": "", "external_calls": 0,
                "credential_tier_selected": "", "fallback_used": False}
    calls = 0
    previous = None
    for index, tier in enumerate(tiers[:2]):
        _SELECTION.set(tier)
        if exhausted() or (path.strip("/").endswith("/odds") and free_profile(tier) and not free_allowed()):
            result = dict(previous or {"http_status": 0, "quota": {}, "error_code": ""})
            result.update(ok=True, payload=[], error="", external_calls=calls,
                          credential_tier_selected=(previous or {}).get("credential_tier_selected", tier),
                          fallback_used=False,
                          controlled_deferrals=["TIME_BUDGET" if exhausted() else "FREE_BUDGET"])
            return result
        result = _attempt(tier, path, params, transport)
        calls += 1
        result.update(credential_tier_selected=tier, fallback_used=index > 0, external_calls=calls)
        if index or result["ok"] or result["http_status"] not in {401, 403} or result["error_code"] not in AUTH_CODES:
            return result
        previous = result
    return result
