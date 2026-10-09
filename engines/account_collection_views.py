"""Pure presentation of account collections and recorded backup evidence."""
from datetime import datetime

from engines.app_navigation import navigation_matches


def favorite_collection(favorites, query='', kind=''):
    query = str(query or '').strip()[:90]
    kind = kind if kind in {'team', 'league', 'match'} else ''
    items = [item for item in favorites
             if (not kind or item.get('kind') == kind)
             and navigation_matches(str(item.get('label') or '') + ' ' + str(item.get('value') or ''), query)]
    return {'items': items, 'query': query, 'kind': kind,
            'total': len(favorites), 'filtered': bool(query or kind)}


def backup_observation(record):
    """Only allowlisted labels and a parsed timestamp; never raw error payloads."""
    record = record if isinstance(record, dict) else {}
    result = record.get('result')
    result = result if isinstance(result, dict) else {}
    try:
        observed_at = datetime.fromisoformat(str(record.get('time') or '')).isoformat()
    except ValueError:
        observed_at = ''
    label, detail = 'Sin observación disponible', 'No hay un resultado automático legible para mostrar.'
    tone = 'unknown'
    if result.get('backup_created') is True and result.get('ok') is False:
        label, tone = 'Copia creada con incidencias', 'warning'
        detail = 'Se registró un archivo nuevo, pero el proceso no terminó correctamente. Revisa el diagnóstico.'
    elif result.get('ok') is False:
        label, tone = 'Último intento sin copia creada', 'warning'
        stage = result.get('failure_stage')
        detail = {
            'STORAGE_CAPACITY': 'El intento no disponía del espacio necesario.',
            'SNAPSHOT': 'La creación de la copia no terminó.',
            'INTEGRITY': 'La comprobación de integridad no terminó correctamente.',
            'HASH': 'El cálculo de la huella de la copia no terminó.',
        }.get(stage, 'Revisa el diagnóstico del último intento antes de dar la copia por válida.')
    elif result.get('ok') is True and result.get('backup_created') is True:
        label, tone = 'Creación automática registrada', 'recorded'
        detail = 'El proceso registró una copia creada. Comprueba su disponibilidad en la lista.'
    elif str(result.get('status') or '').startswith('SKIPPED_'):
        label, detail = 'Última ejecución sin copia nueva', 'Una ejecución omitida no acredita una copia nueva.'
    elif result.get('status') == 'DISABLED':
        label, detail = 'Copia automática desactivada', 'La última ejecución indicó que la copia automática estaba desactivada.'
    return {'label': label, 'detail': detail, 'tone': tone, 'time': observed_at}
