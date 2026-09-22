"""Read an owned draft against current evidence; never update it or call providers.

Uses the same quote/lifecycle/entitlement rules as the constructor. An existing
pick ID is not permission to substitute another selection underneath a draft.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import re

from engines import client_combi_store as store
from engines.combi_advisor_engine import (
    CONTRACT, CombiError, capabilities, clock, decimal, key, preview, text, visible_pick,
)


def _unavailable():
    # Same response for missing IDs and another account's draft.
    return CombiError('DRAFT_UNAVAILABLE', 'Borrador no disponible para tu cuenta.', 404)


def _saved_payload(row):
    payload = store._json(row['payload_json'])
    legs = payload.get('legs')
    try:
        if payload.get('contract') != CONTRACT or not isinstance(legs, list) or not 2 <= len(legs) <= 15:
            raise ValueError('Invalid draft contract')
        if any(not isinstance(leg, dict) for leg in legs):
            raise ValueError('Invalid leg')
        ids = store._ids([leg.get('id') for leg in legs])
        amount = decimal(payload.get('stake'), money=True)
        for leg in legs:
            if not all(isinstance(leg.get(k), str) and leg[k] for k in
                       ('match_id', 'market', 'selection', 'bookmaker', 'event_key')):
                raise ValueError('Incomplete identity')
            decimal(leg.get('odds'))
    except (ValueError, TypeError, CombiError):
        raise CombiError('DRAFT_INVALID', 'El borrador guardado no se puede revisar con seguridad.', 409) from None
    return payload, legs, ids, amount


def review_draft(path, user_id, draft_id, *, now=None):
    """One query-only snapshot. A returned preview still needs explicit save.

    Old evidence remains unchanged. No automatic replacement, repricing, betting,
    settlement, bankroll write, Telegram message or provider request.
    """
    now = clock(now) or datetime.now(timezone.utc)
    with store.connection(path) as conn:
        user = store.actor(conn, user_id, now)
        if not user['id']:
            raise CombiError('AUTH_REQUIRED', 'Inicia sesión para revisar tus borradores.', 401)
        if not isinstance(draft_id, str) or not re.fullmatch(r'[a-f0-9]{32}', draft_id):
            raise _unavailable()
        if not store._table(conn, 'client_combi_drafts'):
            raise _unavailable()
        row = conn.execute('SELECT payload_json,created_at FROM client_combi_drafts WHERE id=? AND user_id=?',
                           (draft_id, user['id'])).fetchone()
        if not row:
            raise _unavailable()
        payload, previous, ids, amount = _saved_payload(row)
        cap = capabilities(user)
        raw_picks = []
        if store._table(conn, 'picks'):
            marks = ','.join('?' for _ in ids)
            raw_picks = [dict(p) for p in conn.execute('SELECT * FROM picks WHERE id IN ('+marks+')', ids)]
        if not cap['can_build'] or any(not visible_pick(leg, cap['plan']) for leg in previous + raw_picks):
            raise CombiError('PLAN_REQUIRED', 'Tu plan actual no permite revisar todas las selecciones de este borrador.', 403)
        pool = {leg['id']: leg for leg in store.candidates(conn, user, now, ids)}
        comparisons, current_legs = [], []
        blocked = 0
        identity_fields = ('match_id', 'market', 'selection', 'event_key')
        for old in previous:
            current = pool.get(old['id'])
            same = bool(current) and all(current.get(k) == old.get(k) for k in identity_fields)
            same = same and key((current or {}).get('bookmaker')) == key(old['bookmaker'])
            reasons = []
            state = 'UNCHANGED'
            if not current:
                state, reasons = 'UNAVAILABLE', ['La selección ya no está disponible. No se sustituye por otra.']
            elif not same:
                state, reasons = 'SELECTION_CHANGED', ['La selección o su partido han cambiado. No se reutiliza automáticamente el mismo identificador.']
            elif not current['eligible']:
                state, reasons = 'BLOCKED', list(current['reasons'])
            elif Decimal(old['odds']) != Decimal(current['odds']):
                state = 'PRICE_CHANGED'
            if state in {'UNAVAILABLE', 'SELECTION_CHANGED', 'BLOCKED'}:
                blocked += 1
            if current and same:
                current_legs.append(current)
            comparisons.append({
                'id': old['id'], 'match': text(old.get('match')), 'selection': text(old.get('selection_label')),
                'bookmaker': text(old['bookmaker']), 'previous_odds': text(old['odds']),
                'previous_at': text(old.get('observed_at')), 'state': state, 'reasons': reasons,
                'current_odds': current.get('odds') if current and same else None,
                'current_at': current.get('observed_at') if current and same else '',
                'current_is_eligible': bool(current and same and current['eligible']),
            })
        fresh_preview, reason = None, ''
        if not blocked:
            try:
                fresh_preview = preview(current_legs, str(amount), user=user, now=now)
            except CombiError as exc:
                reason = exc.message
        return {
            'contract': 'NEMESIS-COMBI-REVIEW-V1', 'draft_id': draft_id,
            'created_at': row['created_at'], 'checked_at': now.isoformat(),
            'stake': format(amount, 'f'), 'previous_total': text(payload.get('total_odds'), 200),
            'comparisons': comparisons, 'blocked_count': blocked,
            'changed_count': sum(leg['state'] == 'PRICE_CHANGED' for leg in comparisons),
            'preview': fresh_preview, 'can_prepare': fresh_preview is not None,
            'reason': reason, 'external_calls': 0, 'original_unchanged': True, 'not_a_bet': True,
        }
