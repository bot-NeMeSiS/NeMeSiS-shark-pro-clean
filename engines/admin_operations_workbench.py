"""Pure presentation of the existing operations snapshot, not another task system.

No IO, providers, persistence, scheduling or status mutations. A generated-at time
belongs to this local reading, not to external evidence freshness. Links are an
explicit registry of existing admin pages, never URLs supplied by an incident.
"""
from __future__ import annotations
from datetime import datetime
import re
from collections import Counter

CONTRACT = 'NEMESIS-ADMIN-WORKBENCH-V1'
MAX_ITEMS = 200
TOOLS = (
    ('sports_data', 'Datos y cuotas', '/admin/data-center', 'Partidos, estadísticas, proveedores y sincronización'),
    ('picks', 'Picks y edición', '/admin/picks', 'Selecciones publicadas y revisión editorial'),
    ('support', 'Atención al cliente', '/admin/support-center', 'Mensajes, tickets y feedback recibido'),
    ('users', 'Usuarios', '/admin/users', 'Cuentas y acceso'),
    ('memberships', 'Membresías', '/admin/memberships', 'Plan, caducidad y origen'),
    ('telegram', 'Telegram', '/admin/telegram/command-center', 'Cola, destinos y última entrega'),
    ('cron', 'Automatizaciones', '/admin/automation-workforce', 'Trabajos, estado y evidencias de ejecución'),
    ('stripe', 'Pagos', '/admin/payments', 'Configuración y revisión; entrar no realiza un cobro'),
    ('backups', 'Copias y recuperación', '/admin/data-vault', 'Respaldo, integridad y recuperación'),
    ('sentinel', 'Incidencias Sentinel', '/admin/sentinel-issues', 'Hallazgos y evidencia antes de cerrar'),
    ('observability', 'Observabilidad', '/admin/observability', 'Errores y diagnóstico'),
    ('highlights', 'Vídeo-resúmenes', '/admin/highlights-center', 'Enlaces, asociación y estado del contenido'),
)
AREA_TOOL = {'database':'backups', 'continuity':'backups', 'render':'observability',
             'runtime':'observability', 'security':'sentinel', 'shark':'sports_data',
             'sports_gateway':'sports_data', 'sports_core':'sports_data'}
SEVERITIES = {'critical':(0,'Crítica'), 'high':(1,'Alta'), 'medium':(2,'Media'),
              'low':(3,'Baja'), 'info':(4,'Informativa')}
CONFIRMED = {'CONFIRMADO', 'VERIFIED'}
UNVERIFIED = {'NO_CERTIFICADO','NOT_CERTIFIED','CERTIFICATION_REQUIRED',
              'BLOQUEADO_POR_ACCESO','BLOCKED_BY_ACCESS','REQUIERE_REVISION','HIPOTESIS','HYPOTHESIS'}


def _text(value, limit=600):
    if value is None or not isinstance(value,(str,int,float)) or isinstance(value,bool):
        return ''
    value = re.sub(r'[\x00-\x1f\x7f]', ' ', str(value)).strip()
    if value.casefold() in {'none','null','undefined','nan'}:
        return ''
    # The workbench does not need tokens or URL credentials in investigation text.
    value = re.sub(r'(?i)\b(password|secret|token|api[_-]?key|authorization)\s*[:=]\s*[^\s,;]+',
                   lambda m:m.group(1)+'=[oculto]',value)
    value = re.sub(r'(?i)https?://[^\s/@]+:[^\s/@]+@', 'https://[oculto]@', value)
    return value[:limit]


def _stamp(value):
    value = _text(value,64)
    try:
        parsed = datetime.fromisoformat(value.replace('Z','+00:00'))
        return parsed.isoformat() if parsed.tzinfo else ''
    except (TypeError,ValueError):
        return ''


def build_admin_workbench(snapshot):
    """Reorder supplied evidence without declaring incidents solved or jobs alive."""
    snapshot = snapshot if isinstance(snapshot,dict) else {}
    raw = snapshot.get('incidents')
    readable = isinstance(raw,list)
    records = raw[:MAX_ITEMS] if readable else []
    tools = [{'key':k,'title':t,'href':h,'description':d} for k,t,h,d in TOOLS]
    by_tool = {t['key']:t for t in tools}
    ids = Counter(_text(r.get('issue_id'),120) for r in records if isinstance(r,dict))
    tasks,invalid = [],0
    for index,row in enumerate(records):
        if not isinstance(row,dict) or not _text(row.get('issue_id'),120):
            invalid += 1
            continue
        ident = _text(row['issue_id'],120)
        evidence = _text(row.get('evidence_state'),80).upper()
        state = _text(row.get('status'),80).upper()
        category = ('verify' if state=='CERTIFICATION_REQUIRED' or evidence in UNVERIFIED
                    else 'confirmed' if evidence in CONFIRMED else 'investigate')
        severity = _text(row.get('severity'),40).lower()
        rank,label = SEVERITIES.get(severity,(5,'Sin clasificar'))
        area = _text(row.get('area'),80)
        tool = by_tool.get(AREA_TOOL.get(area,area),by_tool['sentinel'])
        title = _text(row.get('title'),160) or 'Hallazgo sin título'
        detail = _text(row.get('evidence'),1400) or 'No se adjunta evidencia descriptiva.'
        next_step = _text(row.get('next_action'),700) or 'Revisar el origen del hallazgo antes de decidir.'
        category_label = {'confirmed':'Hallazgo confirmado','verify':'Evidencia pendiente',
                          'investigate':'Por investigar'}[category]
        brief = '\n'.join([
            'NeMeSiS SHARK PRO · tarea de investigación', f'ID: {ident}', f'Área: {area or "Sin clasificar"}',
            f'Clasificación: {category_label}. Prioridad: {label}.',
            f'Evidencia recibida: {detail}', f'Fuente: {_text(row.get("source"),240) or "Sin identificar"}',
            f'Siguiente paso sugerido: {next_step}', f'Panel de revisión: {tool["href"]}',
            'Objetivo: reproducir o refutar el hallazgo, proponer la reparación mínima y añadir una prueba.',
            'Cierre: adjuntar evidencia del resultado. Revisar o copiar esta tarea NO significa resolverla.',
            'No convierte falta de certificación en caída. No ejecutar cobros, envíos, deploys, borrados ni cambios de secretos.',
        ])
        tasks.append({'id':ident,'dom_id':f'admin-task-{index}', 'title':title,'area':area,
                      'category':category,'category_label':category_label, 'severity':severity,
                      'severity_label':label,'evidence':detail,'next_action':next_step,
                      'source':_text(row.get('source'),240) or 'Sin identificar',
                      'href':tool['href'],'tool_title':tool['title'], 'brief':brief,
                      'identity_conflict':ids[ident]>1, 'rank':rank,
                      'needs_confirmation':row.get('requires_approval') is not False})
    tasks.sort(key=lambda t:({'confirmed':0,'investigate':1,'verify':2}[t['category']],t['rank'],t['title'],t['dom_id']))
    counts = {c:sum(t['category']==c for t in tasks) for c in ('confirmed','verify','investigate')}
    return {'contract':CONTRACT,'state':'READABLE' if readable and not invalid else 'PARTIAL' if readable else 'UNAVAILABLE',
            'tasks':tasks,'tools':tools,'counts':counts if readable else None,
            'total_supplied':len(raw) if readable else None,'displayed':len(tasks),
            'invalid':invalid,'truncated':readable and len(raw)>MAX_ITEMS,'limit':MAX_ITEMS,
            'generated_at':_stamp(snapshot.get('generated_at_madrid')),
            'timestamp_scope':'LOCAL_SNAPSHOT_NOT_PROVIDER_FRESHNESS', 'external_calls':0,
            'writes':0,'next_task':tasks[0] if tasks else None}
