"""Pure projection of persisted 1X2 prices; no network, DB or betting actions."""
import json
import math
from engines.madrid_time_engine import to_madrid_time, format_madrid_sync_label
from engines.v935_launch_trust_engine import madrid_now, match_status_truth, get_odds_freshness


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
    items = []
    for key,label in [('home',match.get('client_home') or match.get('home_team') or 'Local'),
                      ('draw','Empate'),('away',match.get('client_away') or match.get('away_team') or 'Visitante')]:
        value = snapshot.get(key)
        if isinstance(value, bool):
            continue
        try:
            price = float(value)
        except (ValueError, TypeError):
            continue
        if not math.isfinite(price) or price <= 1:
            continue
        freshness = get_odds_freshness(clock.isoformat(),now=evaluation,odds=price,
                                       source=source,match_lifecycle=lifecycle)
        items.append({'key':key,'label':label,'price':price,'freshness':freshness['status']})
    current = bool(items) and all(i['freshness']=='FRESH' for i in items)
    return {'available':bool(items),'items':items,'current':current,'bookmaker':str(bookmaker),
            'source':str(source),'observed_at':clock.isoformat(),'observed_label':format_madrid_sync_label(clock),
            'message':'Cuotas de la última actualización.' if current else
                      'Cuotas guardadas anteriormente. Pueden haber cambiado y no se consideran vigentes.'}
