"""Pure projection of persisted 1X2 prices; no network, DB or betting actions."""
import json
import math
import re
import unicodedata
from engines.madrid_time_engine import to_madrid_time, format_madrid_sync_label
from engines.v935_launch_trust_engine import madrid_now, match_status_truth, get_odds_freshness


def _normalized_outcome_name(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    text = ''.join(char for char in text if not unicodedata.combining(char)).casefold()
    # Provider labels sometimes punctuate abbreviations (e.g. "Granada C.F.").
    # Periods do not change the team identity, while other punctuation still
    # separates tokens so we avoid fuzzy or substring matching.
    text = text.replace('.', '')
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


def _valid_decimal_price(value):
    if isinstance(value, bool):
        return None
    try:
        price = float(str(value).strip().replace(',', '.'))
    except (TypeError, ValueError):
        return None
    return price if math.isfinite(price) and price > 1 else None


def outcome_prices_for_match(snapshot, match):
    """Read either normalized prices or The Odds API's named outcome rows.

    Team outcomes are matched by normalized exact name. Fuzzy or positional
    matching could assign a visitor price to the home team, so it is deliberately
    not used. Conflicting duplicate prices make that outcome unavailable.
    """
    candidates = {key: [] for key in ('home', 'draw', 'away')}
    for key in candidates:
        price = _valid_decimal_price(snapshot.get(key))
        if price is not None:
            candidates[key].append(price)

    home_name = _normalized_outcome_name(match.get('client_home') or match.get('home_team'))
    away_name = _normalized_outcome_name(match.get('client_away') or match.get('away_team'))
    if home_name and away_name and home_name != away_name:
        for outcome in snapshot.get('outcomes') or []:
            if not isinstance(outcome, dict):
                continue
            name = _normalized_outcome_name(outcome.get('name') or outcome.get('description'))
            if name in {'draw', 'tie', 'empate', 'x'}:
                key = 'draw'
            elif name == home_name:
                key = 'home'
            elif name == away_name:
                key = 'away'
            else:
                continue
            price = _valid_decimal_price(outcome.get('price') or outcome.get('odds'))
            if price is not None:
                candidates[key].append(price)

    result = {}
    for key, values in candidates.items():
        if not values:
            continue
        first = values[0]
        if all(math.isclose(first, value, rel_tol=1e-9, abs_tol=1e-9) for value in values[1:]):
            result[key] = first
    return result


def cached_match_odds(match, now=None):
    raw = match.get('odds_h2h_json')
    try:
        snapshot = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        snapshot = None
    if not isinstance(snapshot, dict):
        return {'available': False, 'items': [], 'current': False}
    bookmaker = snapshot.get('bookmaker') or match.get('bookmaker')
    source = snapshot.get('source')
    observed = snapshot.get('last_update') or match.get('odds_updated_at')
    clock = to_madrid_time(observed)
    evaluation = to_madrid_time(now) if now is not None else madrid_now()
    if not bookmaker or not source or not clock or not evaluation or clock > evaluation:
        return {'available': False, 'items': [], 'current': False}
    lifecycle = match_status_truth(match, now=evaluation)['lifecycle']
    labels = {
        'home': match.get('client_home') or match.get('home_team') or 'Local',
        'draw': 'Empate',
        'away': match.get('client_away') or match.get('away_team') or 'Visitante',
    }
    items = []
    prices = outcome_prices_for_match(snapshot, match)
    for key in ('home', 'draw', 'away'):
        price = prices.get(key)
        if price is None:
            continue
        freshness = get_odds_freshness(clock.isoformat(),now=evaluation,odds=price,
                                       source=source,match_lifecycle=lifecycle)
        items.append({'key':key,'label':labels[key],'price':price,'freshness':freshness['status']})
    current = bool(items) and all(i['freshness']=='FRESH' for i in items)
    return {'available':bool(items),'items':items,'current':current,'bookmaker':str(bookmaker),
            'source':str(source),'observed_at':clock.isoformat(),'observed_label':format_madrid_sync_label(clock),
            'message':'Cuotas de la última actualización.' if current else
                      'Cuotas guardadas anteriormente. Pueden haber cambiado y no se consideran vigentes.'}
