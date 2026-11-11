"""Public field availability from the existing validated Match Center context.

No provider calls, database access or inference of subscription/coverage.
AVAILABLE means recorded content, never proof of current provider access.
"""
def match_field_availability(context):
    lifecycle=context.get('lifecycle') or {}
    score=context.get('score') or {}
    events=context.get('event_summary') or {}
    lineups=context.get('lineups') or {}
    stats=context.get('statistics') or {}
    teams=lineups.get('teams') or []
    has_players=bool(lineups.get('confirmed') and lineups.get('player_count'))
    formations=[team.get('formation') for team in teams]
    rows=[]
    def add(key,label,available,partial=False,applicable=True):
        state=('NOT_APPLICABLE' if not applicable else 'PARTIAL' if partial else
               'RECORDED' if available else 'NOT_ESTABLISHED')
        rows.append(dict(key=key,label=label,state=state,available=bool(available and applicable and not partial),
            message={'NOT_APPLICABLE':'No corresponde al estado actual.',
                'PARTIAL':'Información registrada incompleta.',
                'RECORDED':'Datos registrados; consulta su hora y fuente.',
                'NOT_ESTABLISHED':'Sin datos verificados en esta ficha.'}[state]))
    add('score','Marcador',score.get('confirmed') is True)
    add('minute','Minuto',lifecycle.get('minute') is not None,
        applicable=lifecycle.get('is_live') is True)
    add('events','Eventos',events.get('available') is True)
    add('lineups','Alineaciones',lineups.get('confirmed') is True)
    add('formation','Formación',bool(teams) and all(formations),
        partial=bool(any(formations) and not all(formations)))
    add('players','Jugadores',has_players)
    add('statistics','Estadísticas',stats.get('available') is True)
    return dict(contract='NEMESIS-MATCH-FIELD-AVAILABILITY-V1',fields=rows,
        meaning='Persisted presentation availability, not provider plan or ingestion certification',
        external_calls=0)
