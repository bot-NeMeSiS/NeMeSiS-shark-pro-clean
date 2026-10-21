"""One explicit UI catalogue. Never translates arbitrary provider/user content."""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from string import Formatter

LANGUAGES = ('es', 'en', 'fr')
LANGUAGE_NAMES = {'es': 'Español', 'en': 'English', 'fr': 'Français'}
CATALOG_PATH = Path(__file__).resolve().parents[1] / 'localization' / 'ui.json'
LOG = logging.getLogger(__name__)


def valid_language(value):
    return value if isinstance(value, str) and value in LANGUAGES else None


def preferred_terms(value, language='es'):
    """Canonical product vocabulary for app-owned copy only."""
    text = str(value or '')
    if (valid_language(language) or 'es') != 'es' or not text:
        return text
    text = re.sub(r'\bpick\(s\)', 'pronóstico(s)', text, flags=re.IGNORECASE)
    def repl(match):
        token = match.group(0)
        replacement = 'pronósticos' if token.lower().endswith('s') else 'pronóstico'
        if token.isupper():
            return replacement.upper()
        if token[:1].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement
    return re.sub(r'\bpicks?\b', repl, text, flags=re.IGNORECASE)


@lru_cache(maxsize=1)
def catalogue():
    groups = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
    entries = {}
    for group in groups.values():
        for source, translations in group.items():
            if source in entries:
                raise ValueError('Duplicate UI source in catalogue')
            entries[source] = translations
    return entries


def translate(source, language='es', **values):
    source = str(source or '')
    language = valid_language(language) or 'es'
    translated = source if language == 'es' else catalogue().get(source, {}).get(language)
    if translated is None:
        live = re.fullmatch(r"En directo( · [0-9]{1,3}(?:\+[0-9]{1,2})?['’]?)", source)
        if live:
            translated = translate('En directo', language) + live[1]
    if translated is None:
        # Never log a dynamic value: it could be a name, message or other PII.
        LOG.debug('UI translation fallback: locale=%s', language)
        translated = source
    translated = preferred_terms(translated, language)
    fallback = preferred_terms(source, language)
    try:
        return translated.format_map(values) if values else translated
    except (KeyError, ValueError):
        return fallback.format_map(values) if values else fallback


def _country_key(value):
    text = unicodedata.normalize('NFKD', str(value or '').strip().casefold())
    text = ''.join(char for char in text if not unicodedata.combining(char))
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


_COUNTRY_ROWS = (
    ('Spain', 'España', 'Espagne'), ('England', 'Inglaterra', 'Angleterre'),
    ('Scotland', 'Escocia', 'Écosse'), ('Wales', 'Gales', 'Pays de Galles'),
    ('Northern Ireland', 'Irlanda del Norte', 'Irlande du Nord'),
    ('Ireland', 'Irlanda', 'Irlande'), ('France', 'Francia', 'France'),
    ('Germany', 'Alemania', 'Allemagne'), ('Italy', 'Italia', 'Italie'),
    ('Portugal', 'Portugal', 'Portugal'), ('Netherlands', 'Países Bajos', 'Pays-Bas'),
    ('Belgium', 'Bélgica', 'Belgique'), ('Switzerland', 'Suiza', 'Suisse'),
    ('Austria', 'Austria', 'Autriche'), ('Poland', 'Polonia', 'Pologne'),
    ('Ukraine', 'Ucrania', 'Ukraine'), ('Romania', 'Rumanía', 'Roumanie'),
    ('Russia', 'Rusia', 'Russie'), ('Turkey', 'Turquía', 'Turquie'),
    ('Greece', 'Grecia', 'Grèce'), ('Armenia', 'Armenia', 'Arménie'),
    ('Azerbaijan', 'Azerbaiyán', 'Azerbaïdjan'),
    ('Bosnia and Herzegovina', 'Bosnia y Herzegovina', 'Bosnie-Herzégovine'),
    ('Croatia', 'Croacia', 'Croatie'), ('Serbia', 'Serbia', 'Serbie'),
    ('Slovakia', 'Eslovaquia', 'Slovaquie'), ('Slovenia', 'Eslovenia', 'Slovénie'),
    ('Hungary', 'Hungría', 'Hongrie'), ('Czech Republic', 'República Checa', 'Tchéquie'),
    ('Bulgaria', 'Bulgaria', 'Bulgarie'), ('Cyprus', 'Chipre', 'Chypre'),
    ('Malta', 'Malta', 'Malte'), ('Estonia', 'Estonia', 'Estonie'),
    ('Finland', 'Finlandia', 'Finlande'), ('Norway', 'Noruega', 'Norvège'),
    ('Denmark', 'Dinamarca', 'Danemark'), ('Sweden', 'Suecia', 'Suède'),
    ('Iceland', 'Islandia', 'Islande'), ('Brazil', 'Brasil', 'Brésil'),
    ('Argentina', 'Argentina', 'Argentine'), ('Chile', 'Chile', 'Chili'),
    ('Colombia', 'Colombia', 'Colombie'), ('Ecuador', 'Ecuador', 'Équateur'),
    ('Peru', 'Perú', 'Pérou'), ('Venezuela', 'Venezuela', 'Venezuela'),
    ('Bolivia', 'Bolivia', 'Bolivie'), ('Paraguay', 'Paraguay', 'Paraguay'),
    ('Uruguay', 'Uruguay', 'Uruguay'), ('Mexico', 'México', 'Mexique'),
    ('United States', 'Estados Unidos', 'États-Unis'), ('Canada', 'Canadá', 'Canada'),
    ('Costa Rica', 'Costa Rica', 'Costa Rica'), ('Panama', 'Panamá', 'Panama'),
    ('Japan', 'Japón', 'Japon'), ('South Korea', 'Corea del Sur', 'Corée du Sud'),
    ('Thailand', 'Tailandia', 'Thaïlande'), ('China', 'China', 'Chine'),
    ('Indonesia', 'Indonesia', 'Indonésie'), ('Singapore', 'Singapur', 'Singapour'),
    ('Malaysia', 'Malasia', 'Malaisie'), ('India', 'India', 'Inde'),
    ('Australia', 'Australia', 'Australie'),
    ('New Zealand', 'Nueva Zelanda', 'Nouvelle-Zélande'),
    ('Egypt', 'Egipto', 'Égypte'), ('South Africa', 'Sudáfrica', 'Afrique du Sud'),
    ('Morocco', 'Marruecos', 'Maroc'), ('Tunisia', 'Túnez', 'Tunisie'),
    ('Algeria', 'Argelia', 'Algérie'), ('Nigeria', 'Nigeria', 'Nigeria'),
    ('Ghana', 'Ghana', 'Ghana'), ('Senegal', 'Senegal', 'Sénégal'),
    ('Cameroon', 'Camerún', 'Cameroun'), ('Kenya', 'Kenia', 'Kenya'),
    ('Uganda', 'Uganda', 'Ouganda'), ('Rwanda', 'Ruanda', 'Rwanda'),
    ('Ethiopia', 'Etiopía', 'Éthiopie'), ('Liberia', 'Liberia', 'Libéria'),
    ('Congo DR', 'RD del Congo', 'RD Congo'), ('Ivory Coast', 'Costa de Marfil', 'Côte d’Ivoire'),
    ('Angola', 'Angola', 'Angola'), ('Saudi Arabia', 'Arabia Saudí', 'Arabie saoudite'),
    ('United Arab Emirates', 'Emiratos Árabes Unidos', 'Émirats arabes unis'),
    ('Qatar', 'Catar', 'Qatar'), ('Iran', 'Irán', 'Iran'), ('Iraq', 'Irak', 'Irak'),
    ('Turkmenistan', 'Turkmenistán', 'Turkménistan'),
    ('Uzbekistan', 'Uzbekistán', 'Ouzbékistan'),
    ('Kyrgyzstan', 'Kirguistán', 'Kirghizistan'), ('Kosovo', 'Kosovo', 'Kosovo'),
    ('Guatemala', 'Guatemala', 'Guatemala'), ('Nicaragua', 'Nicaragua', 'Nicaragua'),
    ('World', 'Mundial', 'Monde'), ('Global', 'Global', 'Global'),
    ('International', 'Internacional', 'International'), ('Europe', 'Europa', 'Europe'),
    ('South America', 'Sudamérica', 'Amérique du Sud'),
    ('North America', 'Norteamérica', 'Amérique du Nord'),
    ('Africa', 'África', 'Afrique'), ('Asia', 'Asia', 'Asie'),
    ('Oceania', 'Oceanía', 'Océanie'),
)

_COUNTRY_ALIASES = {
    'usa': 'United States', 'us': 'United States', 'united states of america': 'United States',
    'korea republic': 'South Korea', 'republic of korea': 'South Korea',
    'czechia': 'Czech Republic', 'holland': 'Netherlands',
    'bosnia herzogovina': 'Bosnia and Herzegovina',
    'bosnia herzegovina': 'Bosnia and Herzegovina',
    'bosnia and herzegovina': 'Bosnia and Herzegovina',
    'congo dr': 'Congo DR', 'congo drc': 'Congo DR', 'congo democratic republic': 'Congo DR',
    'cote d ivoire': 'Ivory Coast', 'cote divoire': 'Ivory Coast',
    'uae': 'United Arab Emirates', 'saudi arabia': 'Saudi Arabia',
}
_COUNTRY_DISPLAY_NAMES = {}
for _english_name, _spanish_name, _french_name in _COUNTRY_ROWS:
    for _alias in (_english_name, _spanish_name, _french_name):
        _COUNTRY_DISPLAY_NAMES[_country_key(_alias)] = (_spanish_name, _english_name, _french_name)
for _alias, _canonical in _COUNTRY_ALIASES.items():
    _row = next(row for row in _COUNTRY_ROWS if row[0] == _canonical)
    _COUNTRY_DISPLAY_NAMES[_country_key(_alias)] = (_row[1], _row[0], _row[2])


def country_display_name(value, language='es'):
    """Localize a known provider country only at display time; preserve unknown labels."""
    source = str(value or '')
    if not source.strip():
        return ''
    language = valid_language(language) or 'es'
    localized = _COUNTRY_DISPLAY_NAMES.get(_country_key(source))
    if localized:
        return localized[{'es': 0, 'en': 1, 'fr': 2}[language]]
    # This also handles explicitly catalogued region labels such as Europa (UEFA).
    return translate(source, language)


def catalogue_issues():
    issues = []
    for source, translations in catalogue().items():
        fields = {name for _, name, _, _ in Formatter().parse(source) if name is not None}
        for language in ('en', 'fr'):
            value = translations.get(language)
            if not isinstance(value, str) or not value:
                issues.append({'source': source, 'language': language, 'reason': 'missing'})
            elif {name for _, name, _, _ in Formatter().parse(value) if name is not None} != fields:
                issues.append({'source': source, 'language': language, 'reason': 'placeholders'})
    return issues


def plural(singular, multiple, count, language='es', **values):
    return translate(singular if count == 1 else multiple, language, count=count, **values)


def identity_value(value, language='es'):
    """Only missing-value sentinels are UI; proper nouns stay byte-for-byte."""
    if value is None or str(value).strip() in {'', 'No disponible', 'None', 'null', 'undefined'}:
        return translate('No disponible', language)
    return value


def owned_text(value, language='es'):
    """Explicit legacy app-copy patterns. Never use for provider or user narrative."""
    text = str(value or '')
    if not text or text in {'None', 'null', 'undefined'}:
        return translate('No disponible', language)
    codes = {
        'UPCOMING': 'Próximo', 'SCHEDULED': 'Programado', 'LIVE': 'En directo',
        'FINISHED': 'Finalizado', 'FINAL': 'Finalizado', 'POSTPONED': 'Aplazado',
        'SUSPENDED': 'Suspendido', 'STALE': 'Datos desactualizados',
        'UNKNOWN': 'Estado pendiente', 'HIGH': 'Alto', 'MEDIUM': 'Medio', 'LOW': 'Bajo',
        'W': 'Victoria', 'D': 'Empate', 'L': 'Derrota',
    }
    if text in codes:
        return translate(codes[text], language)
    patterns = (
        (r'Temporada confirmada: (.+)\.', 'Temporada confirmada: {value}.'),
        (r'Jornada o fase visible: (.+)\.', 'Jornada o fase visible: {value}.'),
        (r'(\d+) partidos en directo confirmados en la muestra local\.', '{value} partidos en directo confirmados en la muestra local.'),
        (r'(.+) presiona', '{value} presiona'),
        (r'Jornada (\d+)', 'Jornada {value}'),
        (r'Temporada (\d+(?:/\d+)?)', 'Temporada {value}'),
        (r'Posición (\d+)', 'Posición {value}'),
        (r'Actualizado hace (\d+) min', 'Actualizado hace {value} min'),
        (r'Más de (\d+(?:[.,]\d+)?) goles', 'Más de {value} goles'),
        (r'Menos de (\d+(?:[.,]\d+)?) goles', 'Menos de {value} goles'),
        (r'Hay (\d+) partido\(s\) en directo\. Revisa marcador, estado y favoritos\.', 'Hay {value} partido(s) en directo. Revisa marcador, estado y favoritos.'),
        (r'Tienes (\d+) pick\(s\) visibles según tu membresía\.', 'Tienes {value} pick(s) visibles según tu membresía.'),
        (r'Tus (\d+) favorito\(s\) alimentan partidos, equipos, ligas y alertas futuras\.', 'Tus {value} favorito(s) alimentan partidos, equipos, ligas y alertas futuras.'),
    )
    for pattern, source in patterns:
        match = re.fullmatch(pattern, text)
        if match:
            parameter = owned_text(match[1], language) if source == 'Jornada o fase visible: {value}.' else match[1]
            return translate(source, language, value=parameter)
    return translate(text, language)


def entity_copy(detail, kind, language='es', datetime_label=None):
    """Localize existing entity context, preserving available identities and facts."""
    if kind == 'team':
        upcoming, picks = detail.get('upcoming') or [], detail.get('picks') or []
        parts = [translate('Contexto SHARK para {team} preparado con datos cacheados reales.', language, team=detail.get('name') or '')]
        if upcoming:
            first = upcoming[0]
            parts.append(translate('Próximo partido: {home} vs {away} ({datetime}).', language,
                home=first.get('home_team') or '', away=first.get('away_team') or '',
                datetime=(datetime_label or (lambda _: ''))(first)))
        else:
            parts.append(translate('No hay próximos partidos sincronizados para este equipo todavía.', language))
        parts.append(plural('Hay {count} pick relacionado publicado o preparado.', 'Hay {count} picks relacionados publicados o preparados.', len(picks), language)
                     if picks else translate('Aún no hay picks relacionados publicados.', language))
        return {'summary':' '.join(parts)}
    context = detail.get('shark_context') or {}
    evidence = [owned_text(text, language) for text in context.get('evidence') or []]
    return {**context, 'summary':' '.join(evidence) if evidence else owned_text(context.get('summary'), language), 'evidence':evidence}


def form_summary(form, language='es'):
    """Localize an already validated result sequence, not raw scores."""
    outcomes = form.get('form') or []
    if not form.get('available') or not outcomes:
        return translate('No hay resultados finalizados confirmados', language)
    return ' · '.join(plural(one, many, outcomes.count(code), language) for code, one, many in (
        ('W', '{count} victoria', '{count} victorias'),
        ('D', '{count} empate', '{count} empates'),
        ('L', '{count} derrota', '{count} derrotas'),
    ))


def context_copy(context, language='es', datetime_label=None):
    """Present typed context evidence without mutating the sports snapshot."""
    intelligence = context.get('context_intelligence') or {}
    if language == 'es':
        return {'headline': intelligence.get('headline') or '',
                'evidence': [item.get('text') or '' for item in intelligence.get('evidence') or []]}
    present_date = datetime_label or (lambda value: '')
    texts = []
    for item in intelligence.get('evidence') or []:
        kind = item.get('kind')
        if kind == 'recent_form' and item.get('id') in ('recent-form-home', 'recent-form-away'):
            side = item['id'].rsplit('-', 1)[-1]
            form = (context.get('recent_form') or {}).get(side) or {}
            texts.append(translate('Forma de {team}: {summary}.', language,
                                   team=form.get('team') or '', summary=form_summary(form, language)))
        elif kind == 'head_to_head':
            count = (context.get('head_to_head') or {}).get('count')
            if isinstance(count, int):
                texts.append(plural('{count} enfrentamiento finalizado con resultado confirmado.',
                                    '{count} enfrentamientos finalizados con resultado confirmado.', count, language))
        elif kind == 'standings':
            standings = context.get('standings') or {}
            names = {(team or {}).get('name') for team in (context.get('teams') or {}).values() if isinstance(team, dict)}
            parts = []
            for row in standings.get('rows') or []:
                if row.get('team_name') not in names:
                    continue
                values = [str(row['team_name'])]
                if row.get('position') is not None:
                    values.append(translate('Posición {position}', language, position=row['position']))
                if row.get('points') is not None:
                    values.append(translate('{points} puntos', language, points=row['points']))
                parts.append(' · '.join(values))
            if parts:
                text = translate('Clasificación disponible: {summary}.', language, summary='; '.join(parts))
                if standings.get('updated_at'):
                    text += ' ' + translate('Observada: {datetime}', language, datetime=present_date(standings['updated_at']))
                texts.append(text)
        else:
            # Unrecognized evidence retains the original; never invent a translation.
            texts.append(translate(item.get('text') or '', language))
    if texts:
        return {'headline': texts[0], 'evidence': texts}
    identity = intelligence.get('identity') or {}
    parts = [identity['competition']] if identity.get('competition') else []
    if identity.get('season'):
        parts.append(translate('Temporada {season}', language, season=identity['season']))
    if identity.get('round'):
        parts.append(owned_text(identity['round'], language))
    if context.get('match'):
        parts.append(present_date(context['match']))
    missing = translate('Faltan clasificación, forma reciente y H2H confirmados para explicar su relevancia deportiva.', language)
    return {'headline': (' · '.join(filter(None, parts)) + '. ' if parts else '') + missing, 'evidence': []}


def shark_copy(context, language='es'):
    """Consume canonical conclusions; no inference or provider translation."""
    original = context.get('shark_context') or {}
    result = dict(original)
    if language == 'es' or not original.get('available'):
        return result
    conclusions = (context.get('intelligence') or {}).get('conclusions') or {}
    def value(key):
        conclusion = conclusions.get(key) or {}
        return (conclusion.get('value') or {}) if conclusion.get('state') in ('VERIFIED', 'PARTIALLY_VERIFIED') else {}
    team = original.get('dominant_team')
    result['headline'] = translate('Dominio observado: {team}', language, team=team) if team else translate('Contexto disponible', language)
    result['phase'] = translate(original.get('phase'), language)
    signals = []
    pressure = value('presion')
    if pressure.get('home_pct') is not None and pressure.get('away_pct') is not None:
        teams = context.get('teams') or {}
        signals.append(translate('Presión observada: {home} {home_pct}% · {away} {away_pct}%', language,
                                 home=(teams.get('home') or {}).get('name') or '', away=(teams.get('away') or {}).get('name') or '',
                                 home_pct=pressure['home_pct'], away_pct=pressure['away_pct']))
    elif pressure.get('label'):
        signals.append(owned_text(pressure['label'], language))
    count = value('cambios_recientes').get('count')
    if isinstance(count, int) and count > 0:
        signals.append(plural('{count} cambio confirmado en la ventana reciente', '{count} cambios confirmados en la ventana reciente', count, language))
    result['signals'] = signals
    result['quality_label'] = translate(original.get('quality_label'), language)
    result['evidence'] = [owned_text(item, language) for item in original.get('evidence') or []]
    return result


def price_label(label, language='es'):
    """Only the known configured cadence is UI; amounts/currency remain untouched."""
    value = str(label or '')
    if value.endswith('/mes'):
        return value[:-4] + translate('/mes', language)
    return translate(value or 'Precio no configurado', language)


def match_summary(context, language='es'):
    """Present an existing canonical summary type, never infer match lifecycle."""
    factual = ((context.get('summaries') or {}).get('items') or [{}])[0]
    fallback = factual.get('text') or (context.get('story') or {}).get('summary') or 'No disponible todavía.'
    if language == 'es':
        return fallback
    kind = factual.get('type')
    teams = context.get('teams') or {}
    values = {side: (teams.get(side) or {}).get('name') or '' for side in ('home','away')}
    score = context.get('score') or {}
    scored = score.get('confirmed') is True and bool(score.get('label'))
    values['score'] = score.get('label') if scored else ''
    messages = {
        'FULLTIME_SUMMARY': '{home} y {away} finalizaron {score}.' if scored else '{home} y {away} finalizaron.',
        'PREMATCH_SUMMARY': '{home} y {away} tienen un partido programado.',
        'STALE_SUMMARY': 'La actualización del partido no está confirmada.',
        'HALFTIME_SUMMARY': '{home} y {away} están al descanso.',
        'LIVE_SUMMARY': '{home} y {away} están disputando el partido.',
        'RESULT_PENDING_SUMMARY': 'El resultado definitivo está pendiente de confirmación.',
        'CANCELLED_SUMMARY': 'El partido entre {home} y {away} figura como cancelado.',
        'POSTPONED_SUMMARY': 'El partido entre {home} y {away} figura como aplazado.',
        'SUSPENDED_SUMMARY': 'El partido entre {home} y {away} figura como suspendido.',
        'ABANDONED_SUMMARY': 'El partido entre {home} y {away} figura como abandonado.',
    }
    if kind not in messages:
        return translate(fallback, language)
    result = translate(messages[kind], language, **values)
    if scored and kind in {'STALE_SUMMARY','LIVE_SUMMARY','HALFTIME_SUMMARY'}:
        suffix = 'Último marcador conocido: {score}; no confirma el estado actual.' if kind == 'STALE_SUMMARY' else 'Marcador confirmado: {score}.'
        result += ' ' + translate(suffix, language, **values)
    return result
