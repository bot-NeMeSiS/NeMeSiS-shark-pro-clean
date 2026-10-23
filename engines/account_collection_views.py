"""Pure presentation of account collections and recorded backup evidence."""
from datetime import datetime

from engines.app_navigation import navigation_matches


_BACKUP_STAGE_LABELS = {
    'ATTEMPT': 'Intento completo', 'LOCK': 'Bloqueo de exclusión',
    'RECOVERY': 'Recuperación temporal', 'PREPARATION': 'Preparación',
    'CAPACITY_PREFLIGHT': 'Preanálisis de capacidad',
    'CAPACITY_DB_ESTIMATE': 'Estimación de base de datos',
    'CAPACITY_DISK_CHECK': 'Comprobación de espacio',
    'CAPACITY_BACKUP_INVENTORY': 'Inventario de copias previas',
    'CAPACITY_BACKUP_VERIFY': 'Verificación de copia previa',
    'CAPACITY_VERIFY_HISTORY': 'Verificación del historial',
    'CAPACITY_RECLAIM': 'Recuperación de espacio',
    'COMPACT_CAPACITY_PREFLIGHT': 'Estimación de copia compacta',
    'WORKSPACE': 'Preparación de copia', 'SNAPSHOT': 'Creación de copia',
    'INTEGRITY': 'Comprobación de integridad', 'METADATA': 'Lectura de resumen',
    'HASH': 'Cálculo de huella', 'MANIFEST': 'Preparación de manifiesto',
    'PUBLICATION': 'Publicación', 'RETENTION': 'Retención',
    'CLEANUP': 'Limpieza temporal',
}
_BACKUP_STAGE_STATUSES = {
    'finished': 'Finalizada', 'failed': 'Fallida',
    'rejected': 'Rechazada', 'skipped': 'Omitida',
}
_BACKUP_METRICS = (
    'snapshot_bytes', 'compact_snapshot_bytes', 'required_bytes',
    'free_before', 'free_after', 'free_bytes', 'reusable_page_bytes',
)
_BACKUP_COMPACT_STATES = {
    'READY': 'Copia compacta estimada viable',
    'NO_REUSABLE_PAGES': 'SQLite no tiene páginas reutilizables suficientes para reducir la copia.',
    'INSUFFICIENT_SPACE': 'La copia compacta estimada supera el espacio libre.',
    'CAPACITY_CHECK_FAILED': 'No se pudo estimar la capacidad de copia compacta.',
}


def _backup_diagnostic_summary(result):
    result = result if isinstance(result, dict) else {}
    stages = []
    raw_stages = result.get('diagnostic_stages')
    if isinstance(raw_stages, list):
        for raw in raw_stages[-32:]:
            if not isinstance(raw, dict):
                continue
            label = _BACKUP_STAGE_LABELS.get(raw.get('stage'))
            status = _BACKUP_STAGE_STATUSES.get(raw.get('status'))
            duration = raw.get('duration_ms')
            if (not label or not status or isinstance(duration, bool)
                    or not isinstance(duration, int) or not 0 <= duration <= 86_400_000):
                continue
            stages.append({'label': label, 'status': status, 'duration_ms': duration})

    storage = result.get('storage')
    storage = storage if isinstance(storage, dict) else {}
    metrics = {}
    for key in _BACKUP_METRICS:
        value = storage.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 10**15:
            metrics[key] = value
    compact = storage.get('compact_candidate')
    compact = compact if isinstance(compact, dict) else {}
    compact_fields = {
        'compact_snapshot_bytes': 'compact_snapshot_bytes',
        'compact_required_bytes': 'required_bytes',
        'compact_free_bytes': 'free_bytes',
        'compact_reusable_page_bytes': 'reusable_page_bytes',
    }
    for output_key, source_key in compact_fields.items():
        value = compact.get(source_key)
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 10**15:
            metrics[output_key] = value
    candidate_state = compact.get('reason_code')
    candidate_state = candidate_state if isinstance(candidate_state, str) and candidate_state in _BACKUP_COMPACT_STATES else ''
    required = metrics.get('compact_required_bytes')
    free = metrics.get('compact_free_bytes')
    shortfall = max(0, required - free) if required is not None and free is not None else None
    return {
        'stages': stages,
        'storage': metrics,
        'compact_candidate_state': candidate_state,
        'compact_candidate_label': _BACKUP_COMPACT_STATES.get(candidate_state, ''),
        'compact_shortfall_mib': round(shortfall / 1048576, 1) if shortfall else None,
    }


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
            'CAPACITY': 'El intento no disponía del espacio necesario.',
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
    return {'label': label, 'detail': detail, 'tone': tone, 'time': observed_at,
            'diagnostics': _backup_diagnostic_summary(result)}
