"""Client-first editorial projection from the existing canonical match snapshot.

Pure, deterministic, bounded. No model/API calls, no odds or opinion generation.
The returned text never claims a full chronicle when only a score is available.
"""
from __future__ import annotations
from collections.abc import Mapping
import hashlib
import json
from engines.ui_localization_engine import match_summary, translate, valid_language

CONTRACT = 'NEMESIS-MATCH-EDITORIAL-V1'


def obj(value):
    return dict(value) if isinstance(value, Mapping) else {}


def text(value, limit=400):
    return str(value if value is not None else '').strip()[:limit]


def build_editorial(context, news=None, language='es'):
    language = valid_language(language) or 'es'
    def ui(source, **values):
        return translate(source, language, **values)
    context = obj(context)
    life, score = obj(context.get('lifecycle')), obj(context.get('score'))
    events, stats = obj(context.get('event_summary')), obj(context.get('statistics'))
    evidence, story = obj(context.get('evidence')), obj(context.get('story'))
    final = life.get('is_finished') is True
    live = life.get('is_live') is True
    stale = life.get('is_stale') is True
    title = 'Así fue el partido' if final else 'Lo último confirmado' if live else 'Antes del partido' if life.get('key') == 'UPCOMING' else 'Estado del encuentro'
    summary = (match_summary(context, language) if context.get('summaries') else
               ui(text(story.get('summary'), 1000) or 'Todavía no hay información confirmada suficiente para resumir este encuentro.'))
    if stale:
        title = 'Última información disponible'
        summary = ui('La última lectura se conserva como contexto; no se presenta como información actual.')
    # Never promote a score to a final; use the canonical lifecycle and story.
    facts = []
    if stats.get('available') is True and stats.get('source') and not stale:
        for row in (stats.get('items') or [])[:20]:
            row = obj(row)
            if text(row.get('label')).casefold() not in {'posesión', 'tiros', 'tiros a puerta', 'córners'}:
                continue
            def value(side):
                raw = row.get(side)
                return '—' if raw in (None, '', 'No disponible', 'None', 'null') else text(raw, 24)
            home, away = value('home'), value('away')
            if home == away == '—':
                continue
            facts.append({'label':text(row.get('label'), 60), 'home':home, 'away':away})
            if len(facts) == 4:
                break
    moments = []
    if events.get('available') is True and events.get('source') and not stale:
        seen = set()
        candidates = []
        decisive = {'goal', 'own_goal', 'penalty_goal', 'missed_penalty', 'red_card',
                    'second_yellow', 'yellow_red_card', 'penalty_shootout_goal', 'penalty_shootout_miss'}
        for index, row in enumerate((events.get('items') or [])[:150]):
            row = obj(row)
            kind = text(row.get('type')).lower()
            if kind not in decisive | {'yellow_card', 'var', 'substitution'}:
                continue
            label = text(row.get('label') or row.get('detail'), 180)
            key = (row.get('id'), row.get('minute_label'), label, row.get('player'), row.get('team'))
            if not label or key in seen:
                continue
            seen.add(key)
            candidates.append((0 if kind in decisive else 1, index,
                               {'label':ui(label), 'minute':text(row.get('minute_label'), 20) or ui('Minuto no disponible'),
                                'player':text(row.get('player'), 100), 'team':text(row.get('team'), 120)}))
        # Select decisive facts first, then preserve the canonical timeline order.
        selected = sorted(candidates, key=lambda item: (item[0], item[1]))[:4]
        moments = [item[2] for item in sorted(selected, key=lambda item: item[1])]
    paragraphs = []
    if final and not stale:
        on_target = next((f for f in facts if f['label'] == 'Tiros a puerta'), None)
        if on_target and '—' not in (on_target['home'], on_target['away']):
            paragraphs.append(ui('La comparación disponible registra {home} tiros a puerta del local y {away} del visitante. Este dato no determina por sí solo quién dominó el encuentro.', home=on_target['home'], away=on_target['away']))
    for fact in facts:
        fact['label'] = ui(fact['label'])
    news = obj(news)
    articles = list(news.get('items') or [])[:6] if news.get('state') == 'VERIFIED' else []
    media = obj(context.get('media'))
    visible = list(media.get('visible_videos') or [])
    result = {
        'contract':CONTRACT, 'title':ui(title), 'summary':summary, 'paragraphs':paragraphs,
        'phase':ui(text(life.get('label')) or 'Por confirmar'),
        'source':text(evidence.get('source')) or ui('Fuente no identificada'),
        'observed_at':evidence.get('updated_at'),
        'facts':facts, 'stat_source':text(stats.get('source')), 'stat_observed_at':stats.get('updated_at'),
        'moments':moments, 'event_source':text(events.get('source')),
        'coverage':ui('Cierre con datos y hechos disponibles' if final and (facts or moments) else 'Cierre breve · cobertura parcial' if final else 'Información disponible'),
        'limitation': ui('No se dispone de una cronología completa verificada. El marcador no permite deducir cómo se desarrolló el encuentro.' if final and not moments else 'Se muestran hechos registrados, no una valoración de quién mereció ganar.'),
        'news':articles, 'news_state':news.get('state') or 'NOT_INITIALIZED',
        'video_count':len(visible), 'external_calls':0, 'generative_ai_calls':0,
    }
    # Stable content fingerprint, not a misleading "updated just now" label.
    result['revision'] = hashlib.sha256(json.dumps(result, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()[:16]
    return result
