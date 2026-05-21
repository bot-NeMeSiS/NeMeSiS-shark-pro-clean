# -*- coding: utf-8 -*-
"""V327 · SHARK COMBI INTELLIGENCE PRO
Capa inteligente sobre V326. No llama APIs externas; reutiliza datos/cache de la app.
"""
from __future__ import annotations
from typing import Any, Dict


def build_shark_combi_intelligence(count=9, stake=0.10, risk='balanceado', day='hoy') -> Dict[str, Any]:
    try:
        from services.shark_combi_1x2_service_v326 import build_shark_combi_1x2
        payload = build_shark_combi_1x2(count=count, stake=stake, risk=risk, day=day)
    except Exception as exc:
        return {
            'ok': True,
            'version': 'V327',
            'touches_api': False,
            'headline': 'SHARK Combi Intelligence en modo seguro',
            'summary': {'total_odds': 0, 'stake': float(stake or 0.10), 'possible_return': 0, 'possible_profit': 0, 'avg_score': 0, 'risk_label': 'Sin datos'},
            'selections': [],
            'warnings': [str(exc)[:180], 'No se hacen llamadas API desde esta pantalla.'],
            'copy_text': 'Sin combinada disponible todavía.'
        }

    selections = payload.get('selections') or []
    enhanced = []
    for s in selections:
        odds = float(s.get('odds') or 0)
        score = float(s.get('score') or s.get('confidence') or 65)
        ev = float(s.get('ev') or 0)
        stability = max(0, min(100, score + min(10, ev) - max(0, odds - 2.2) * 9))
        if odds >= 3.9:
            tag = 'Cuota alta'
        elif stability >= 82:
            tag = 'Muy estable'
        elif stability >= 70:
            tag = 'Correcta'
        else:
            tag = 'Vigilar'
        item = dict(s)
        item['confidence'] = round(stability, 1)
        item['intelligence_tag'] = tag
        item['why'] = item.get('reason') or item.get('why') or 'Selección 1X2 elegida por equilibrio entre cuota, score y datos disponibles.'
        enhanced.append(item)

    payload['version'] = 'V327'
    payload['headline'] = 'SHARK Combi Intelligence 1X2'
    payload['subheadline'] = 'Ranking inteligente de selecciones 1X2 para combinadas del día.'
    payload['selections'] = enhanced
    payload['intelligence'] = {
        'mode': str(risk or 'balanceado'),
        'rules': ['Evita mercados no 1X2', 'Filtra cuotas extremas', 'No rellena combinadas sin datos suficientes', 'No gasta API extra'],
    }
    return payload
