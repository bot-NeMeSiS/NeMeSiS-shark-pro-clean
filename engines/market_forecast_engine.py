"""Transparent market-implied 1X2 reading from persisted, fresh odds only.

This is not a SHARK probability model or a betting recommendation. It performs
no network calls and never creates, edits, or publishes a pick.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from engines.match_odds_presentation import cached_match_odds


REQUIRED_OUTCOMES = {"home", "draw", "away"}
SUPPORTED_SOURCES = frozenset({"the odds api", "api-football", "api football", "api_football"})


def normalized_market_probabilities(prices):
    """Normalize a complete decimal-odds 1X2 market, without calling it SHARK confidence."""
    if not isinstance(prices, dict) or set(prices) != REQUIRED_OUTCOMES:
        return None
    inverse_prices = {}
    try:
        for key, value in prices.items():
            price = Decimal(str(value))
            if not price.is_finite() or price <= Decimal("1"):
                return None
            inverse_prices[key] = Decimal("1") / price
    except (InvalidOperation, TypeError, ValueError, OverflowError, ZeroDivisionError):
        return None

    total = sum(inverse_prices.values(), Decimal("0"))
    if not total.is_finite() or total <= Decimal("0"):
        return None
    raw = {key: value * Decimal("100") / total for key, value in inverse_prices.items()}
    try:
        rounded = {key: value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
                   for key, value in raw.items()}
    except (InvalidOperation, OverflowError):
        return None
    target = max(raw, key=raw.get)
    rounded[target] += Decimal("100.0") - sum(rounded.values(), Decimal("0"))
    leader = max(raw.values())
    leaders = [key for key, value in raw.items() if value == leader]
    return {
        "probabilities": {key: float(rounded[key]) for key in REQUIRED_OUTCOMES},
        "favorite_key": leaders[0] if len(leaders) == 1 else None,
    }


def market_implied_forecast(match, *, is_upcoming, now=None):
    match = match if isinstance(match, dict) else {}
    base = {
        "contract": "MARKET-IMPLIED-1X2-V1",
        "state": "UNAVAILABLE",
        "available": False,
        "outcomes": [],
        "favorite": None,
        "source": "",
        "bookmaker": "",
        "observed_at": "",
        "observed_label": "",
        "message": "No hay una lectura de mercado verificable para este partido.",
        "method": "",
        "disclaimer": "No es una probabilidad calibrada por SHARK ni una promesa de resultado.",
        "external_calls": 0,
    }
    if is_upcoming is not True:
        return {**base, "state": "NOT_UPCOMING", "message": "La lectura previa solo se muestra para partidos próximos."}

    quote_view = cached_match_odds(match, now=now)
    source = str(quote_view.get("source") or "").strip()
    base.update({
        "source": source,
        "bookmaker": str(quote_view.get("bookmaker") or ""),
        "observed_at": str(quote_view.get("observed_at") or ""),
        "observed_label": str(quote_view.get("observed_label") or ""),
    })
    if source.casefold() not in SUPPORTED_SOURCES:
        return {**base, "state": "UNVERIFIED_SOURCE", "message": "No se muestra una estimación porque la fuente de cuotas no está verificada."}

    items = [item for item in quote_view.get("items") or [] if isinstance(item, dict)]
    by_key = {str(item.get("key") or ""): item for item in items}
    if set(by_key) != REQUIRED_OUTCOMES:
        return {**base, "state": "INCOMPLETE_MARKET", "message": "No se calcula una lectura porcentual: faltan cuotas de una o más opciones 1X2."}
    if quote_view.get("current") is not True or any(item.get("freshness") != "FRESH" for item in by_key.values()):
        return {**base, "state": "STALE_MARKET", "message": "Las cuotas guardadas no son actuales; no se muestra una estimación porcentual."}

    normalized = normalized_market_probabilities({key: by_key[key].get("price") for key in REQUIRED_OUTCOMES})
    if normalized is None:
        return {**base, "state": "INCOMPLETE_MARKET", "message": "No se calcula una lectura porcentual: una cuota 1X2 no es válida."}

    definitions = (("home", "1", "Local"), ("draw", "X", "Empate"), ("away", "2", "Visitante"))
    outcomes = [
        {
            "key": key,
            "short_label": short_label,
            "label": str(by_key[key].get("label") or fallback_label),
            "odds": float(by_key[key]["price"]),
            "probability_pct": normalized["probabilities"][key],
        }
        for key, short_label, fallback_label in definitions
    ]
    favorite = next((item for item in outcomes if item["key"] == normalized["favorite_key"]), None)
    return {
        **base,
        "state": "CURRENT",
        "available": True,
        "outcomes": outcomes,
        "favorite": ({"key": favorite["key"], "label": favorite["label"], "probability_pct": favorite["probability_pct"]} if favorite else None),
        "source": source,
        "bookmaker": str(quote_view.get("bookmaker") or ""),
        "observed_at": str(quote_view.get("observed_at") or ""),
        "observed_label": str(quote_view.get("observed_label") or ""),
        "message": ("Lectura implícita calculada desde la última actualización de API-Football dentro de su ventana configurada; consulta la hora del proveedor."
                    if source.casefold() in {"api-football", "api football", "api_football"}
                    else "Lectura implícita calculada desde las tres cuotas 1X2 actuales."),
        "method": "1/cuota, normalizado entre local, empate y visitante.",
        "external_calls": 0,
    }
