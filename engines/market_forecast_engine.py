"""Transparent market-implied 1X2 reading from persisted, fresh odds only.

This is not a SHARK probability model or a betting recommendation. It performs
no network calls and never creates, edits, or publishes a pick.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from engines.match_odds_presentation import cached_match_odds


REQUIRED_OUTCOMES = {"home", "draw", "away"}
SUPPORTED_SOURCE = "the odds api"


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
    if source.casefold() != SUPPORTED_SOURCE:
        return {**base, "state": "UNVERIFIED_SOURCE", "message": "No se muestra una estimación porque la fuente de cuotas no está verificada."}

    items = [item for item in quote_view.get("items") or [] if isinstance(item, dict)]
    by_key = {str(item.get("key") or ""): item for item in items}
    if set(by_key) != REQUIRED_OUTCOMES:
        return {**base, "state": "INCOMPLETE_MARKET", "message": "No se calcula una lectura porcentual: faltan cuotas de una o más opciones 1X2."}
    if quote_view.get("current") is not True or any(item.get("freshness") != "FRESH" for item in by_key.values()):
        return {**base, "state": "STALE_MARKET", "message": "Las cuotas guardadas no son actuales; no se muestra una estimación porcentual."}

    inverse_prices = {}
    for key, item in by_key.items():
        try:
            price = Decimal(str(item.get("price")))
            if not price.is_finite() or price <= Decimal("1"):
                raise InvalidOperation
            inverse_prices[key] = Decimal("1") / price
        except (InvalidOperation, TypeError, ValueError, ZeroDivisionError):
            return {**base, "state": "INCOMPLETE_MARKET", "message": "No se calcula una lectura porcentual: una cuota 1X2 no es válida."}

    total = sum(inverse_prices.values(), Decimal("0"))
    if not total.is_finite() or total <= Decimal("0"):
        return {**base, "state": "INCOMPLETE_MARKET", "message": "No se calcula una lectura porcentual: el mercado no es válido."}

    definitions = (("home", "1", "Local"), ("draw", "X", "Empate"), ("away", "2", "Visitante"))
    raw_percentages = {key: value * Decimal("100") / total for key, value in inverse_prices.items()}
    rounded = {
        key: value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        for key, value in raw_percentages.items()
    }
    rounding_remainder = Decimal("100.0") - sum(rounded.values(), Decimal("0"))
    rounding_target = max(raw_percentages, key=raw_percentages.get)
    rounded[rounding_target] += rounding_remainder
    outcomes = [
        {
            "key": key,
            "short_label": short_label,
            "label": str(by_key[key].get("label") or fallback_label),
            "odds": float(by_key[key]["price"]),
            "probability_pct": float(rounded[key]),
        }
        for key, short_label, fallback_label in definitions
    ]
    leader = max(raw_percentages.values())
    leaders = [outcome for outcome in outcomes if raw_percentages[outcome["key"]] == leader]
    favorite = leaders[0] if len(leaders) == 1 else None
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
        "message": "Lectura implícita calculada desde las tres cuotas 1X2 actuales.",
        "method": "1/cuota, normalizado entre local, empate y visitante.",
        "external_calls": 0,
    }
