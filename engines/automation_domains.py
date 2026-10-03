"""Canonical production ownership. Existing module paths remain adapters.

This registry has no imports of workers, no scheduler, and no side effects.
QA and development orchestration must not become production recurrence.
"""
DOMAINS = (
    {'key': 'sports', 'label': 'Sports', 'modules': ['sports_service', 'engines.daily_automation_engine'], 'endpoint': '/api/automation/telegram/tick', 'diagnostic': '/admin/data-center', 'state_key': 'last_cron_telegram_call', 'scope': 'TheSportsDB · The Odds API · sincronización · cuotas · evaluación'},
    {'key': 'media', 'label': 'Highlights', 'modules': ['engines.sportsdb_highlights_engine', 'engines.highlight_review_engine', 'engines.highlight_policy_engine'], 'endpoint': '/api/automation/highlights/sync', 'diagnostic': '/admin/highlights', 'state_key': 'last_cron_highlights_sync', 'scope': 'Catálogo y asociación automáticos; publicación con derechos acreditados'},
    {'key': 'postmatch', 'label': 'Postmatch', 'modules': ['engines.postmatch_recovery', 'engines.postmatch_store'], 'endpoint': '/api/automation/postmatch/tick', 'diagnostic': '/admin/highlights-review#postmatch-workers', 'state_key': '', 'scope': 'Cola persistente · caché · reintentos · presupuesto máximo 60/día'},
    {'key': 'delivery', 'label': 'Delivery / Telegram', 'modules': ['telegram_service', 'engines.telegram_autonomous_delivery_engine'], 'endpoint': '/api/automation/telegram/tick', 'diagnostic': '/admin/telegram/command-center', 'state_key': 'last_cron_telegram_call', 'scope': 'Entrega automática con deduplicación y recuperación'},
    {'key': 'maintenance', 'label': 'Maintenance / Backups', 'modules': ['engines.data_vault_engine', 'engines.product_review_system_engine'], 'endpoint': '/api/automation/data-backup/run', 'extra_endpoints': {'evolution': '/api/automation/continuous-evolution/tick'}, 'diagnostic': '/admin/backups', 'state_key': 'last_cron_data_backup_call', 'scope': 'Backup diario · retención · evolución segura'},
)


def production_endpoint(domain, flow='primary'):
    owner = next(item for item in DOMAINS if item['key'] == domain)
    return owner['endpoint'] if flow == 'primary' else owner['extra_endpoints'][flow]


def domain_summary(state):
    result = []
    for domain in DOMAINS:
        last = state.get(domain['state_key']) or {}
        detail = last.get('result') or {}
        result.append({**domain, 'owner': 'NeMeSiS Master Automation',
                       'last_run': last.get('time') or last.get('created_at') or '',
                       'last_result': detail.get('status') if isinstance(detail, dict) else '',
                       'observation': 'RECORDED' if last else 'NOT_OBSERVED'})
    return result
