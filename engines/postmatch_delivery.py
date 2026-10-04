"""Closed recovery evidence for admin UI and logs; never a licence or coverage claim."""
from __future__ import annotations

from datetime import datetime
import re
import sqlite3
from zoneinfo import ZoneInfo
from engines.automation_outcome import TECHNICAL_REASONS

REASON_TEXT = {
    'NO_EVENT': 'No se encontró un evento que coincida con este partido.',
    'NO_VIDEO': 'No se obtuvo un enlace de vídeo en las consultas realizadas.',
    'NO_STATISTICS': 'La consulta no devolvió estadísticas para guardar.',
    'NO_POSTMATCH_DETAILS': 'Las consultas no aportaron todos los eventos o alineaciones; se volverá a comprobar.',
    'MEDIA_PENDING': 'La cola de media del Cron maestro continúa la búsqueda de vídeo, sin duplicar consultas.',
    'ARCHIVE_BUDGET': 'Se alcanzó el límite del archivo pospartido; el trabajo permanece pendiente.',
    'UNSUPPORTED_STATISTICS': 'Llegaron estadísticas, pero sus nombres no están reconocidos por el lector.',
    'EMPTY_STATISTIC_VALUES': 'Llegaron métricas reconocidas sin valores disponibles.',
    'INVALID_VIDEO_URL': 'El enlace recibido no cumple el formato seguro y no se obtuvo una alternativa.',
    'VIDEO_LOOKUP_UNAVAILABLE': 'No se pudo establecer la fecha y liga necesarias para la búsqueda alternativa.',
    'HIGHLIGHT_RESPONSE_LIMIT': 'La respuesta llegó al límite: no demuestra ausencia de vídeo.',
    'AMBIGUOUS_VIDEO': 'Se encontraron enlaces distintos para el mismo evento; requiere revisión.',
    'RIGHTS_REVIEW': 'Se guardó el enlace y queda pendiente de revisión de publicación.',
    'COMPLETE': 'Tarea completada según sus comprobaciones.',
    'PARTIAL_COVERAGE': 'Se guardaron algunas estadísticas; faltan otras.',
    'CONFLICT': 'Hay valores discrepantes pendientes de revisión.',
    'MISSING_KEY': 'La fuente seleccionada no tiene una clave configurada.',
    'MALFORMED': 'La estructura de la respuesta no es la esperada; no se ha contado como ausencia de datos.',
    'ACCESS_DENIED': 'El proveedor rechazó el acceso.',
    'RATE_LIMIT': 'El proveedor indicó un límite de consultas.',
    'NETWORK': 'No se pudo completar la comunicación con el proveedor.',
    'DAILY_BUDGET': 'Se alcanzó el presupuesto diario de recuperación.',
    'TICK_BUDGET': 'Se alcanzó el límite de tiempo o consultas de este lote.',
    'SOURCE_COOLDOWN': 'La fuente está en espera tras un error o límite anterior.',
    'SOURCE_DISABLED': 'La fuente está desactivada.',
    'SOURCE_NOT_ALLOWED': 'La fuente no está seleccionada para esta recuperación.',
    'MISSING_PROVIDER_ID': 'Falta un identificador verificado para consultar esta fuente.',
    'AMBIGUOUS_MATCH': 'La respuesta no permite asociar el partido de forma inequívoca.',
    'IDENTITY_MISMATCH': 'El evento recibido no coincide con la identidad verificada del partido.',
    'IDENTITY_CHANGED': 'La identidad del partido cambió y se canceló esta tarea.',
    'NOT_FINAL': 'El partido no tiene un final confirmado.',
    'SOURCE_NOT_FINAL': 'La fuente no confirma que el evento haya terminado.',
    'INVALID_STATISTIC': 'Un valor estadístico no supera la validación.',
    'CONFLICTING_STATISTICS': 'La respuesta contiene valores contradictorios.',
    'INCONSISTENT_STATISTICS': 'Las estadísticas no son consistentes entre sí.',
    'REDIRECT_BLOCKED': 'El proveedor intentó redirigir la consulta; no se siguió el enlace.',
    'NO_APPROVED_SOURCE': 'No hay una fuente seleccionada que aporte los datos.',
    'STORAGE_UNAVAILABLE': 'No se pudo completar la operación sobre el almacenamiento.',
    'INTERNAL_ERROR': 'La ejecución necesita una revisión técnica.',
    'PAUSED_OR_RECLAIMED': 'La tarea se pausó o fue recuperada por otro proceso.',
    'UNKNOWN': 'No se pudo establecer un motivo verificable.',
}
STATE_TEXT = {'COMPLETE':'Completada', 'RETRY':'Reintento programado',
              'REVIEW_REQUIRED':'Pendiente de revisión', 'CANCELLED':'Cancelada',
              'PARTIAL':'Datos parciales', 'FAILED':'No completada', 'LEASE_LOST':'Ejecución interrumpida'}
RESULT_TEXT = {'COMPLETE':'Lote completado', 'PARTIAL':'Lote procesado con pendientes',
               'FAIL':'Error técnico de ejecución',
               'IDLE':'No había tareas pendientes de ejecutar', 'SKIPPED_DISABLED':'Recuperación en pausa',
               'STORAGE_UNAVAILABLE':'No se pudo completar el lote', 'UNKNOWN':'Resultado no disponible'}


def safe_diagnostics(value):
    """Only numeric IDs/counts and closed labels; no provider-supplied free text."""
    if not isinstance(value, dict):
        return {}
    output = {}
    for key in ('event_rows','statistics_received','statistics_recognized','statistics_accepted','highlight_rows','cache_hits'):
        number = value.get(key)
        if type(number) is int and 0 <= number <= 1500:
            output[key] = number
    sid = value.get('sportsdb_event_id')
    if isinstance(sid, str) and re.fullmatch(r'[1-9][0-9]{0,14}', sid):
        output['sportsdb_event_id'] = sid
    for key, allowed in {
        'key_mode': {'PUBLIC_DEMO_KEY','CONFIGURED_KEY_NOT_PLAN_VERIFIED'},
        'video_lookup': {'EVENT_LINK','LEAGUE_DAY','LEAGUE_DAY_LINK'},
    }.items():
        label = value.get(key)
        if isinstance(label, str) and label in allowed:
            output[key] = label
    return output


def _count(value, maximum):
    return value if type(value) is int and 0 <= value <= maximum else None


def safe_run_result(value):
    value = value if isinstance(value, dict) else {}
    result = value.get('result')
    output = {'ok': value.get('ok') is True,
              'result': result if isinstance(result, str) and result in RESULT_TEXT else 'UNKNOWN',
              'processed': _count(value.get('processed'), 2),
              'external_calls': _count(value.get('external_calls'), 12), 'jobs': []}
    output['pending_jobs'] = _count(value.get('pending_jobs'),2**53-1)
    output['content_pending'] = value.get('content_pending') if type(value.get('content_pending')) is bool else None
    rows = value.get('jobs')
    for row in rows[:2] if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        reason, state = row.get('reason'), row.get('state')
        job = {'job_id': _count(row.get('job_id'), 2**53 - 1),
               'kind': row.get('kind') if row.get('kind') in ('highlights','statistics','archive') else 'unknown',
               'reason': reason if isinstance(reason, str) and reason in REASON_TEXT else 'UNKNOWN',
               'state': state if isinstance(state, str) and state in STATE_TEXT else 'FAILED',
               'external_calls': _count(row.get('external_calls'), 6),
               'diagnostics': safe_diagnostics(row.get('diagnostics'))}
        errors = row.get('technical_errors')
        job['technical_errors'] = [error for error in errors[:12] if isinstance(error,str) and error in TECHNICAL_REASONS] if isinstance(errors,list) else []
        mid = row.get('match_id')
        if isinstance(mid, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', mid):
            job['match_id'] = mid
        due = row.get('due_at')
        if type(due) in (int, float) and 946684800 <= due <= 4102444800:
            job['due_at'] = due
        output['jobs'].append(job)
    return output


def present_run_result(value, store):
    output = safe_run_result(value)
    output['title'] = RESULT_TEXT[output['result']]
    output['available'] = isinstance(value, dict)
    for job in output['jobs']:
        job['kind_label'] = {'highlights':'Resumen en vídeo','statistics':'Estadísticas',
                             'archive':'Eventos y alineaciones'}.get(job['kind'],'Tarea sin identificar')
        job['state_label'] = STATE_TEXT[job['state']]
        job['reason_label'] = REASON_TEXT[job['reason']]
        job['match_label'] = 'Partido sin identificar en esta lectura'
        if job.get('match_id'):
            try:
                match = store.match(job['match_id'])
                if match:
                    job['match_label'] = (str(match.get('home_team') or '')[:100] + ' — ' + str(match.get('away_team') or '')[:100])
            except (sqlite3.Error, OSError, ValueError):
                pass
        if job.get('due_at'):
            job['due_label'] = datetime.fromtimestamp(job['due_at'], ZoneInfo('Europe/Madrid')).strftime('%d/%m/%Y %H:%M')
    return output
