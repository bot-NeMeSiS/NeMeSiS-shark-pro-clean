"""One evidence contract for private 1X2 drafts and SHARK explanations.

Pure computation: no providers, bets, payments, Telegram, or database access.
A multiplied quote is an illustration, never a bookmaker offer or win probability.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext, ROUND_HALF_UP
import hashlib
import json
import re
import unicodedata
from urllib.parse import quote

from engines.membership_engine import can_access_feature, get_membership_limits
from engines.v935_launch_trust_engine import get_odds_freshness, match_kickoff_madrid, match_status_truth

CONTRACT = 'NEMESIS-COMBI-ADVICE-V1'
MAX_LEGS = 15
RANK = {'FREE': 0, 'PRO': 1, 'ELITE': 2, 'ADMIN': 3}


class CombiError(ValueError):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def text(value, limit=240):
    if value is None:
        return ''
    return re.sub(r'[\x00-\x1f\x7f]', ' ', str(value)).strip()[:limit]


def key(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', text(value).casefold()) if not unicodedata.combining(c)).strip()


def clock(value):
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
    return dt.astimezone(timezone.utc) if dt.tzinfo else None


def decimal(value, *, money=False):
    raw = str(value).strip().replace(',', '.')
    if type(value) is bool or len(raw) > 32 or not re.fullmatch(r'\d+(?:\.\d+)?', raw):
        raise CombiError('INVALID_NUMBER', 'Introduce un número decimal válido.')
    try:
        number = Decimal(raw)
    except InvalidOperation:
        raise CombiError('INVALID_NUMBER', 'Número no válido.') from None
    if not number.is_finite() or number <= 0 or number > 1000:
        raise CombiError('INVALID_NUMBER', 'El valor debe ser mayor que cero y no superar 1.000.')
    if money and number != number.quantize(Decimal('.01')):
        raise CombiError('INVALID_AMOUNT', 'El importe simulado admite como máximo dos decimales.')
    if not money and number <= 1:
        raise CombiError('INVALID_ODDS', 'La cuota decimal debe ser mayor que uno.')
    return number


def capabilities(user):
    plan = text((user or {}).get('membership') or 'FREE').upper()
    if plan not in RANK:
        plan = 'FREE'
    principal = {'membership': plan}
    basic = can_access_feature(principal, 'combis_basic')
    advanced = can_access_feature(principal, 'combis_advanced')
    return {'plan': plan, 'can_build': basic, 'can_suggest': advanced,
            'max_legs': min(MAX_LEGS, get_membership_limits(plan)['combi_matches']) if basic else 0}


def visible_pick(pick, plan):
    needed = text(pick.get('membership_required') or 'FREE').upper()
    return needed in RANK and RANK.get(plan, 0) >= RANK[needed]


def outcome(pick, match):
    # No substring guessing: "draw no bet" and "double chance" are not 1X2.
    market = key(pick.get('market') or pick.get('pick_type'))
    if market not in {'1x2', 'h2h', 'match winner', 'match result', 'resultado final', 'ganador del partido'}:
        return ''
    value = key(pick.get('selection'))
    home, away = key(match.get('home_team')), key(match.get('away_team'))
    if value in {'1', 'home', 'local'} or (home and value == home):
        return '1'
    if value in {'x', 'draw', 'empate'}:
        return 'X'
    if value in {'2', 'away', 'visitante'} or (away and value == away):
        return '2'
    return ''


def _assess_selection(pick, match, odds_record, user, *, now=None, editorial=True):
    """The caller supplies persisted records; client-submitted prices are never used."""
    now = clock(now) or datetime.now(timezone.utc)
    pid, mid = text(pick.get('id'), 180), text(match.get('id'), 180)
    truth = match_status_truth(match, now=now) if match else {}
    issues = []
    if any(key(row.get(flag)) in {'true','1','yes'} for row in (pick,match) for flag in ('is_fake','is_demo','simulated')):
        issues.append('Registro de demostración: no se utiliza para una combinada real.')
    if not pid or not mid or text(pick.get('match_id'), 180) != mid:
        issues.append('Partido no asociado de forma inequívoca.')
    if editorial and (text(pick.get('status')).lower() not in {'published', 'publicado'} or key(pick.get('result_status')) not in {'', 'pending', 'pendiente'}):
        issues.append('La selección no está publicada y pendiente de resultado.')
    sport = key(match.get('sport_key'))
    if not sport or not (sport.startswith('soccer') or sport in {'football', 'futbol', 'fútbol'}):
        issues.append('Esta versión del constructor solo admite fútbol.')
    kickoff = match_kickoff_madrid(match) if match else None
    if truth.get('lifecycle') != 'UPCOMING' or not kickoff or kickoff <= now:
        issues.append('El encuentro no está confirmado como próximo.')
    selection = outcome(pick, match)
    if not selection:
        issues.append('Mercado o selección 1X2 sin identificar.')
    # Team identity, not the pick's denormalized labels, drives every link and label.
    for side in ('home', 'away'):
        if pick.get(side + '_team') and key(pick[side + '_team']) != key(match.get(side + '_team')):
            issues.append('Los equipos del pick y del partido no coinciden.')
            break
    quote_row = dict(odds_record or {})
    bookmaker = text(quote_row.get('bookmaker'), 120)
    source = text(quote_row.get('source'), 120)
    stamp = clock(quote_row.get('observed_at'))
    try:
        odd = decimal(quote_row.get('odds'))
    except CombiError:
        odd = None
    if key(bookmaker) in {'','none','null','unknown','desconocido','pendiente','shark'} or key(source) in {'','none','null','unknown','pendiente'} or not stamp or stamp > now:
        issues.append('Falta casa, procedencia u hora válida de la cuota.')
    fresh = get_odds_freshness(stamp, now, odds=float(odd) if odd else None, source=source,
                               match_lifecycle=truth.get('lifecycle', 'INCOMPLETE'),
                               market_open=not bool(quote_row.get('closed')))
    # Stricter than a display-only recorded price: drafts use only fresh quotes.
    if fresh.get('status') != 'FRESH':
        issues.append('La cuota no está vigente para construir una combinada.')
    if not visible_pick(pick, capabilities(user)['plan']):
        issues.append('La selección no está incluida en tu plan.')
    home, away = text(match.get('home_team'), 120), text(match.get('away_team'), 120)
    answer = {'contract': CONTRACT, 'id': pid, 'match_id': mid, 'eligible': not issues,
              'match': f'{home} vs {away}', 'home': home, 'away': away,
              'competition': text(match.get('competition_name') or match.get('league_name'), 160),
              'kickoff': kickoff.isoformat() if kickoff else '',
              'date': kickoff.date().isoformat() if kickoff else '',
              'market': '1X2', 'selection': selection,
              'selection_label': {'1': f'Gana {home}', 'X': 'Empate', '2': f'Gana {away}'}.get(selection, 'Selección pendiente'),
              'odds': format(odd, 'f') if odd else None, 'bookmaker': bookmaker,
              'odds_source': source, 'observed_at': stamp.isoformat() if stamp else '',
              'quote_id': text(quote_row.get('id'), 180),
              'quote_clock_scope':text(quote_row.get('clock_scope') or 'RECORDED_QUOTE_TIME'),
              'membership_required': text(pick.get('membership_required') or 'FREE'),
              'match_url': '/match/' + quote(mid, safe=''),
              'advice_url': ('/shark?pick=' + quote(pid, safe='')) if editorial else ('/shark?match_id=' + quote(mid, safe='')),
              'selection_origin': 'editorial_pick' if editorial else 'customer_market_choice',
              'reasons': list(dict.fromkeys(issues)),
              'risk_note': text(pick.get('warning_reason'), 600),
              'editorial_reason': text(pick.get('reasoning'), 1000),
              'model_probability': None,
              'status': truth.get('lifecycle', 'INCOMPLETE')}
    # Conservative duplicate key across provider/local aliases: no second selection
    # on the same ordered teams and Madrid day even with two local fixture IDs.
    answer['event_key'] = hashlib.sha256(json.dumps([key(home), key(away), answer['date']], ensure_ascii=False).encode()).hexdigest()
    return answer


def assess_pick(pick, match, odds_record, user, *, now=None):
    return _assess_selection(pick, match, odds_record, user, now=now, editorial=True)


def assess_market_choice(choice, match, odds_record, user, *, now=None):
    """A customer choice backed by saved odds, not a fabricated editorial pick."""
    result = _assess_selection(choice, match, odds_record, user, now=now, editorial=False)
    if key(match.get('source')) in {'','none','null','unknown','demo','fake'}:
        result['eligible'] = False
        result['reasons'].append('Falta una fuente identificable del encuentro.')
    return result


def preview(legs, stake, *, user, now=None):
    cap = capabilities(user)
    if not cap['can_build']:
        raise CombiError('PLAN_REQUIRED', 'Combinadas básicas disponibles desde PRO.', 403)
    if not isinstance(legs, list) or not 2 <= len(legs) <= cap['max_legs']:
        raise CombiError('LEG_COUNT', f'Selecciona entre 2 y {cap["max_legs"]} partidos distintos.')
    if any(not leg.get('eligible') for leg in legs):
        raise CombiError('INELIGIBLE_PICK', 'Alguna selección ya no es válida. Revisa la lista antes de continuar.', 409)
    if len({p['event_key'] for p in legs}) != len(legs) or len({p['id'] for p in legs}) != len(legs):
        raise CombiError('DUPLICATE_EVENT', 'No se pueden combinar dos selecciones del mismo partido.')
    if len({key(p['bookmaker']) for p in legs}) != 1:
        raise CombiError('MIXED_BOOKMAKERS', 'Utiliza cuotas de una misma casa. No existe una oferta conjunta confirmada entre casas.')
    amount = decimal(stake, money=True)
    with localcontext() as ctx:
        ctx.prec = 90
        total = Decimal(1)
        for leg in legs:
            total *= decimal(leg['odds'])
        payout = (amount * total).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        total_string = format(total, 'f')
        result = {'contract': CONTRACT, 'status': 'DRAFT', 'legs': legs,
                  'stake': format(amount.quantize(Decimal('.01')), 'f'), 'total_odds': total_string,
                  'potential_return': format(payout, 'f'), 'potential_net': format(payout-amount, 'f'),
                  'bookmaker': legs[0]['bookmaker'], 'probability': None,
                  'not_a_bet': True, 'created_at': (clock(now) or datetime.now(timezone.utc)).isoformat(),
                  'warnings': ['Simulación: no coloca apuestas ni confirma que la casa acepte la combinación.',
                               'El retorno solo se ilustra si todas las selecciones se resuelven como ganadoras a esas cuotas.',
                               'No calculamos una probabilidad conjunta: no hay un modelo calibrado de dependencias.']}
    if len(legs) >= 5:
        result['warnings'].append('Combinada larga: basta una selección perdida para perder el importe simulado; no hay garantía de éxito.')
    teams = [key(p[side]) for p in legs for side in ('home', 'away')]
    if len(teams) != len(set(teams)):
        result['warnings'].append('Hay equipos repetidos en diferentes encuentros: las selecciones pueden estar relacionadas.')
    result['fragile_leg'] = max(legs, key=lambda p: Decimal(p['odds']))['id']
    result['fragile_explanation'] = 'La cuota individual más alta implica un umbral de acierto menor en el precio, no una predicción validada de SHARK.'
    evidence = {k: result[k] for k in ('contract', 'legs', 'stake', 'total_odds', 'bookmaker')}
    result['revision'] = hashlib.sha256(json.dumps(evidence, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    result['copy_text'] = '\n'.join(['Combinada 1X2 · BORRADOR · no es una apuesta', *[
        f"{i}. {p['match']} · {p['selection_label']} · cuota {p['odds']} · {p['bookmaker']} · {p['observed_at']}"
        for i,p in enumerate(legs,1)], f"Producto orientativo: {total_string} · Importe simulado: {result['stake']} EUR",
        'Confirmar cuotas y condiciones en la casa. Sin beneficio garantizado.'])
    return result


def suggest(candidates, count, *, user, risk='conservador', date='', bookmaker=''):
    if not capabilities(user)['can_suggest']:
        raise CombiError('PLAN_REQUIRED', 'La propuesta automática pertenece a ELITE.', 403)
    if type(count) is not int or not 2 <= count <= MAX_LEGS or risk not in {'conservador', 'equilibrado', 'agresivo'}:
        raise CombiError('INVALID_OPTIONS', 'Revisa número de selecciones y perfil.')
    groups = {}
    for leg in candidates:
        if not leg['eligible'] or (date and leg['date'] != date) or (bookmaker and key(leg['bookmaker']) != key(bookmaker)):
            continue
        group = groups.setdefault(key(leg['bookmaker']), {})
        old = group.get(leg['event_key'])
        if not old or (Decimal(leg['odds']), leg['id']) < (Decimal(old['odds']), old['id']):
            group[leg['event_key']] = leg
    choices = [sorted(g.values(), key=lambda p:(Decimal(p['odds']),p['kickoff'],p['id'])) for g in groups.values() if len(g) >= count]
    if not choices:
        raise CombiError('INSUFFICIENT_EVIDENCE', 'No hay suficientes partidos 1X2 válidos de una misma casa. No se completa con relleno.', 409)
    # Never label a heuristic as model confidence. All modes stay within eligible
    # records; aggressive changes ordering, not the permission/freshness rules.
    if risk == 'agresivo':
        choices = [list(reversed(g)) for g in choices]
    elif risk == 'equilibrado':
        choices = [sorted(g, key=lambda p:(p['kickoff'],Decimal(p['odds']),p['id'])) for g in choices]
    return sorted(choices,key=lambda g:(-len(g),key(g[0]['bookmaker'])))[0][:count]
