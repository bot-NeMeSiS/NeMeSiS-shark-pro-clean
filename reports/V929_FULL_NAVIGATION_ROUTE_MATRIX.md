# V929 Full Navigation Route Matrix

- Rutas Flask: `646`
- Enlaces/acciones auditados: `929`
- Rotos: `0`
- Loops: `0`
- Botones sin acción: `0`
- Templates huérfanos detectados: `0`

| Origen | Texto | URL | Endpoint | Auth | Resultado | Corrección |
|---|---|---|---|---|---|---|
| templates/404.html:20 | {{ item.label }} | {{ item.href }} | dynamic_template | public | WARNING | — |
| templates/404.html:22 | Restablecer app/PWA | — | — | public | WARNING | — |
| templates/404.html:43 | Acción JavaScript | / | home | public | OK | — |
| templates/account_center.html:11 | Telegram | /telegram | telegram_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/account_center.html:11 | Cerrar sesión | /logout | logout_page | public | OK | — |
| templates/account_center.html:21 | Telegram {{ 'Vinculado' if data.telegram_state and data.telegram_state.linked else 'Pendiente' }} | /telegram | telegram_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/account_center.html:22 | Plan {{ plan }} | /membresias | membership_page | public | OK | — |
| templates/account_center.html:23 | Favoritos {{ data.account_center.favorites }} | /favorites | favorites_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/account_center.html:24 | Sesión Cerrar sesión | /logout | logout_page | public | OK | — |
| templates/account_center.html:30 | Gestionar plan | /membresias | membership_page | public | OK | — |
| templates/account_center.html:31 | Configurar | /telegram | telegram_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/account_center.html:32 | Formulario | /pagos/portal | payments_customer_portal | public | OK | — |
| templates/account_center.html:32 | Ver pagos | /membresias | membership_page | public | OK | — |
| templates/account_center.html:33 | Abrir favoritos | /favorites | favorites_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/account_center.html:36 | Ver todo → | /actividad | activity_page | public | OK | — |
| templates/account_center.html:40 | Cambiar contraseña Seguridad | /password-reset | v808_password_reset_alias | public | OK | — |
| templates/account_center.html:40 | Notificaciones Preferencias | /notificaciones | v808_notifications_alias | public | OK | — |
| templates/account_center.html:40 | Soporte Ayuda | /soporte | v724_contact_alias_page | public | OK | — |
| templates/account_center.html:40 | Cerrar sesión Salir de forma segura | /logout | logout_page | public | OK | — |
| templates/account_center.html:41 | Telegram configurar → | /telegram | telegram_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/account_center.html:41 | Plan {{ plan }} → | /membresias | membership_page | public | OK | — |
| templates/account_center.html:41 | Salir sesión segura ⏻ | /logout | logout_page | public | OK | — |
| templates/activity.html:7 | Mi perfil | /perfil | profile_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/activity.html:7 | Alertas | /alertas | alerts_page | public | OK | — |
| templates/adaptive_experience.html:14 | {{ k.label }} {{ k.value }} {{ k.hint }} | {{ k.href }} | dynamic_template | public | WARNING | — |
| templates/adaptive_experience.html:25 | {{ a.icon }} {{ a.label }} {{ a.badge }} | {{ a.href }} | dynamic_template | public | WARNING | — |
| templates/adaptive_experience.html:33 | Inicio cliente KPIs, acciones y foco visual. | /app | v757_client_app_center_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/adaptive_experience.html:34 | Calendario Densidad PC y tarjetas móvil. | /calendar | calendar_page | public | OK | — |
| templates/adaptive_experience.html:35 | Picks Lectura premium, riesgo y mercado. | /picks | picks_page | public | OK | — |
| templates/adaptive_experience.html:36 | Directo Marcador/minuto y legibilidad. | /live | live_page | public | OK | — |
| templates/admin_alerts.html:11 | Alertas | /admin/alerts | admin_alerts_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_alerts.html:12 | Telegram | /admin/telegram/diagnostics | admin_telegram_diagnostics_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_alerts.html:13 | Readiness | /admin/top-app-readiness | admin_top_app_readiness_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_api_sports_audit.html:9 | Ver JSON seguro | /api/admin/api-sports/status | api_admin_api_sports_status | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_api_sports_audit.html:10 | Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_api_sports_audit.html:11 | Daily Automation | /admin/daily-automation | admin_v818_daily_automation_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_app_experience_quality.html:10 | Calidad app | /admin/app-experience-quality | admin_v773_app_experience_quality_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_app_experience_quality.html:11 | Datos comerciales | /admin/data-marketplace | admin_v773_data_marketplace_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_app_experience_quality.html:12 | Automatización | /admin/automation-center | admin_v773_automation_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_app_experience_quality.html:13 | API QA | /api/admin/app-experience-quality | api_admin_v773_app_experience_quality | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_app_feel.html:10 | Ver cliente | /sports-hub | sports_hub_page | public | OK | — |
| templates/admin_app_feel.html:11 | Sistema visual | /admin/visual-experience | admin_visual_experience_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_app_feel.html:12 | QA cliente | /admin/client-experience | admin_client_experience_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_app_feel.html:13 | Go Live | /admin/go-live | admin_go_live_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_automation.html:11 | Formulario | /admin/automation | admin_automation_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_automation.html:15 | Backups | /admin/backups | admin_backups_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_automation.html:16 | Observabilidad | /admin/observability | admin_observability_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_automation_workforce.html:17 | Actualizar estado | — | — | public | WARNING | — |
| templates/admin_automation_workforce.html:18 | Verificar runtime | — | — | public | WARNING | — |
| templates/admin_automation_workforce.html:19 | Refrescar cola visual | — | — | public | WARNING | — |
| templates/admin_automation_workforce.html:233 | Release Manager dry-run | — | — | public | WARNING | — |
| templates/admin_automation_workforce.html:234 | Post-deploy Sentinel dry-run | — | — | public | WARNING | — |
| templates/admin_automation_workforce.html:235 | Browser QA status | — | — | public | WARNING | — |
| templates/admin_autonomous_company_sentinel.html:10 | Ejecutar revisión | — | — | public | WARNING | — |
| templates/admin_autonomous_company_sentinel.html:11 | Reference scan | — | — | public | WARNING | — |
| templates/admin_autonomous_company_sentinel.html:12 | Revisión diaria | — | — | public | WARNING | — |
| templates/admin_autonomous_company_sentinel.html:13 | Post-deploy | — | — | public | WARNING | — |
| templates/admin_autonomous_company_sentinel.html:14 | Ver incidencias | /admin/sentinel-issues | admin_sentinel_issues_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autonomous_company_sentinel.html:15 | Ver outbox Codex | /admin/sentinel-codex-outbox | admin_sentinel_codex_outbox_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autonomous_company_sentinel.html:16 | Plan de autofix | — | — | public | WARNING | — |
| templates/admin_autonomous_company_sentinel.html:17 | Estado Render | — | — | public | WARNING | — |
| templates/admin_autonomous_company_sentinel.html:82 | Ver outbox | /admin/sentinel-codex-outbox | admin_sentinel_codex_outbox_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autonomous_company_sentinel.html:83 | Ver gaps | — | — | public | WARNING | — |
| templates/admin_autonomous_company_sentinel.html:190 | Ver gaps | — | — | public | WARNING | — |
| templates/admin_autonomous_company_sentinel.html:191 | Ver outbox | /admin/sentinel-codex-outbox | admin_sentinel_codex_outbox_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autonomous_company_sentinel.html:220 | Copiar prompt | — | — | public | WARNING | — |
| templates/admin_autonomous_company_sentinel.html:241 | Abrir runtime seguro | /api/runtime-version | api_runtime_version | public | OK | — |
| templates/admin_autonomous_company_sentinel.html:255 | Abrir centro | /admin/sentinel-issues | admin_sentinel_issues_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autonomous_picks.html:8 | Auto Picks | /admin/autonomous-picks | admin_v808_autonomous_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autonomous_picks.html:9 | Picks | /admin/picks | admin_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autonomous_picks.html:10 | Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autonomous_picks.html:11 | Telegram | /admin/telegram | admin_telegram_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autonomous_picks.html:28 | Formulario | /admin/autonomous-picks | admin_v808_autonomous_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autonomous_sentinel.html:9 | Ejecutar revisión ahora | /api/admin/autonomous-sentinel/run?mode=safe_scan&dry_run=1 | api_admin_autonomous_sentinel_run | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autonomous_sentinel.html:10 | Ver outbox Codex | /api/admin/autonomous-sentinel/outbox | api_admin_autonomous_sentinel_outbox | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autonomous_sentinel.html:11 | Ver autofix plan | /api/admin/autonomous-sentinel/autofix-plan | api_admin_autonomous_sentinel_autofix_plan | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autonomous_sentinel.html:12 | Ver incidencias | /admin/sentinel-issues | admin_sentinel_issues_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autonomous_sentinel.html:85 | Abrir centro común | /admin/sentinel-issues | admin_sentinel_issues_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autonomous_sentinel.html:111 | Generar prompts | /api/admin/autonomous-sentinel/generate-codex-prompts | api_admin_autonomous_sentinel_generate_codex_prompts | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autopilot_audit.html:8 | Auditoría Telegram | /admin/telegram-audit | admin_v808_telegram_audit_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autopilot_audit.html:9 | Picks | /admin/picks | admin_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_autopilot_audit.html:10 | Estado del programador | /api/scheduler/status | api_scheduler_status | public | OK | — |
| templates/admin_backups.html:9 | Formulario | /admin/backups | admin_backups_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_backups.html:14 | Observabilidad | /admin/observability | admin_observability_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_backups.html:15 | Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_backups.html:40 | Descargar | /admin/backups/download/{{ backup.name }} | dynamic_template | admin | WARNING | — |
| templates/admin_backups.html:41 | Formulario | /admin/backups | admin_backups_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_backups.html:47 | Formulario | /admin/backups | admin_backups_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_betting_center.html:8 | Revisar recomendaciones | /admin/recommendations | v566_admin_recommendations_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_betting_center.html:9 | Abrir control de calidad | /admin/quality-center | admin_quality_center | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_betting_center.html:10 | Revisar Telegram | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_betting_center.html:11 | Admin picks | /admin/picks | admin_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_betting_center.html:35 | Revisar en Admin Picks | /admin/picks | admin_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_betting_center.html:35 | Ver partido | /match/{{ r.match_id }} | dynamic_template | public | WARNING | — |
| templates/admin_bootstrap.html:11 | Entrar como admin | /admin-login | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_bootstrap.html:15 | Formulario | /admin-bootstrap | admin_bootstrap_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_calendar_experience.html:17 | Ver calendario | /calendar | calendar_page | public | OK | — |
| templates/admin_client_experience.html:9 | Sistema | /admin/system | admin_system_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_client_experience.html:10 | Rutas | /admin/route-health | admin_route_health_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_client_experience.html:11 | Telegram | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_client_experience.html:12 | Cliente QA | /admin/client-experience | admin_client_experience_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_client_experience.html:13 | Producción | /admin/production-readiness | admin_production_readiness_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_client_screen_audit.html:14 | Ver cliente → | /app | v757_client_app_center_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/admin_client_screen_audit.html:15 | ↗ Ver informe completo API de auditoría › | /api/admin/client-screen-audit | api_admin_v791_client_screen_audit | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_client_success.html:9 | Cliente QA | /admin/client-experience | admin_client_experience_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_client_success.html:10 | Producción | /admin/production-readiness | admin_production_readiness_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_client_success.html:11 | Telegram | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_client_success.html:12 | Client Success | /admin/client-success | admin_client_success_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_client_success.html:30 | {{ action.title }} | {{ action.href }} | dynamic_template | public | WARNING | — |
| templates/admin_client_success.html:47 | Abrir | {{ pillar.href }} | dynamic_template | public | WARNING | — |
| templates/admin_codex_automation.html:96 | Memoria de datos | /admin/data-memory | admin_data_memory_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_codex_automation.html:97 | Telegram | /admin/telegram/diagnostics | admin_telegram_diagnostics_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_codex_automation.html:98 | Automatización | /admin/automation | admin_automation_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_codex_automation.html:99 | Observabilidad | /admin/observability | admin_observability_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:16 | 👥 Usuarios Clientes, roles y membresías. | /admin/users | admin_users_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:17 | 🗄️ Data Center Sync de calendario, cuotas y live. | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:18 | ✅ Calidad Salud global del ecosistema. | /admin/quality-center | admin_quality_center | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:19 | 🧠 Inteligencia SHARK, recomendaciones y estado deportivo. | /admin/intelligence-center | admin_v808_intelligence_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:20 | 🎯 Picks Crear, publicar y archivar picks. | /admin/picks | admin_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:21 | 📊 Rendimiento Resultados, ROI y control de picks. | /admin/pick-performance | admin_v808_pick_performance_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:22 | 💎 Recomendaciones Convertir análisis en picks revisados. | /admin/betting-center | admin_v808_betting_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:23 | 🧬 Motor picks Value, riesgo, confianza y picks revisados. | /admin/intelligence-engine | admin_v808_intelligence_engine_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:24 | 📲 Telegram Cola, envíos y automatización. | /admin/telegram | admin_telegram_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:25 | ⚽ Partidos Calendario y resultados. | /admin/matches-sync | admin_matches_sync_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:26 | 🛡️ SportsDB Escudos, equipos y feed legal. | /admin/sportsdb-sync | admin_sportsdb_sync_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:27 | 📥 Import Center CSV/JSON legal. | /admin/import-center | import_center | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:28 | 🛟 Soporte Feedback e incidencias. | /admin/support-center | admin_v808_support_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:29 | 💳 Membresías FREE / PRO / ELITE. | /admin/memberships | admin_memberships_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:30 | 🚀 Lanzamiento Checklist comercial. | /admin/launch-center | admin_v808_launch_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:31 | 🔁 Retención Progreso y actividad de clientes. | /admin/retention-center | admin_v808_retention_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_command_center.html:32 | ⚙️ Sistema Estado interno y diagnóstico. | /admin/system | admin_system_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_commercial_readiness.html:10 | Ir a Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_commercial_readiness.html:16 | {{ '✅' if c.ok else '⚠️' }}         {{ c.label }} {{ c.detail }} | {{ c.href or '#' }} | dynamic_template | public | WARNING | — |
| templates/admin_company_audit.html:50 | Abrir área | {{ board.href }} | dynamic_template | public | WARNING | — |
| templates/admin_company_os.html:41 | Abrir área | {{ worker.href }} | dynamic_template | public | WARNING | — |
| templates/admin_compliance_center.html:21 | Legal público | /legal | v566_legal_page | public | OK | — |
| templates/admin_compliance_center.html:21 | Juego responsable | /juego-responsable | v566_responsible_betting_page | public | OK | — |
| templates/admin_compliance_center.html:21 | QA final | /admin/final-qa | v566_admin_final_qa_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_content_rights.html:11 | Derechos | /admin/content-rights | admin_content_rights_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_content_rights.html:12 | Sale Ready | /admin/sale-ready | admin_sale_ready_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_content_rights.html:13 | Telegram | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_continuous_sentinel.html:10 | Quick cycle | — | — | public | WARNING | — |
| templates/admin_continuous_sentinel.html:11 | Client cycle | — | — | public | WARNING | — |
| templates/admin_continuous_sentinel.html:12 | Admin cycle | — | — | public | WARNING | — |
| templates/admin_continuous_sentinel.html:13 | Visual cycle | — | — | public | WARNING | — |
| templates/admin_daily_automation.html:32 | JSON | /api/admin/daily-automation/runs | api_admin_v818_daily_automation_runs | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_daily_automation.html:50 | D Dry-run Calcula jobs sin enviar Telegram real > | /api/admin/daily-automation/dry-run | api_admin_v818_daily_automation_dry_run | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_daily_automation.html:51 | H Health DB, APIs, Telegram y secret > | /api/admin/daily-automation/health | api_admin_v818_daily_automation_health | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_daily_automation.html:52 | C Centro legacy Cron anterior conservado > | /admin/automation-center | admin_v773_automation_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_dashboard.html:23 | Ver todo | /admin/observability/errors | admin_observability_errors_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_dashboard.html:29 | Abrir Workforce | /admin/automation-workforce | admin_automation_workforce_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_dashboard.html:30 | {{ item.get('title') }} {{ item.get('body') }} → | {{ item.get('href') }} | dynamic_template | public | WARNING | — |
| templates/admin_data_center.html:11 | Formulario | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_data_depth.html:45 | Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_data_marketplace.html:11 | CSV | /api/admin/data-marketplace/export/{{ item.get('key') }}?format=csv | dynamic_template | admin | WARNING | — |
| templates/admin_data_vault.html:12 | Data Vault | /admin/data-vault | admin_data_vault_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_data_vault.html:13 | Backups clásicos | /admin/backups | admin_backups_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_data_vault.html:14 | Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_data_vault.html:67 | Formulario | /api/admin/data-vault/create-backup | api_admin_data_vault_create_backup | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_data_vault.html:72 | Formulario | /api/admin/data-vault/validate-backup | api_admin_data_vault_validate_backup | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_final_release.html:10 | Go Live | /admin/go-live | admin_go_live_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_final_release.html:11 | Telegram | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_final_release.html:12 | Producción | /admin/production-readiness | admin_production_readiness_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_final_release.html:13 | Visual | /admin/visual-experience | admin_visual_experience_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_final_release.html:14 | Ver cliente | /sports-hub | sports_hub_page | public | OK | — |
| templates/admin_go_live.html:115 | Público grande Roadmap global | /admin/public-launch | admin_public_launch_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_go_live.html:116 | Telegram Status y dry-run | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_go_live.html:117 | Data Memory Memoria real | /admin/data-memory | admin_data_memory_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_go_live.html:118 | Track Record ROI real | /admin/track-record | admin_track_record_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_growth_center.html:32 | Usuarios | /admin/users | admin_users_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_growth_center.html:33 | Picks | /admin/picks | admin_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_growth_center.html:34 | Datos | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_growth_center.html:35 | Telegram | /admin/telegram | admin_telegram_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_growth_center.html:36 | QA final | /admin/final-qa | v566_admin_final_qa_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_highlights_center.html:8 | Sincronizar ahora | /api/admin/highlights/sync?force=1&days_back=7&limit=300 | api_admin_highlights_sync | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_highlights_center.html:8 | Vista cliente | /resumenes | highlights_page | public | OK | — |
| templates/admin_highlights_center.html:8 | API estado | /api/admin/highlights/status | api_admin_highlights_status | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_highlights_center.html:24 | Ver | {{ h.detail_url }} | dynamic_template | public | WARNING | — |
| templates/admin_highlights_center.html:30 | Partido | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/admin_intelligence.html:9 | Usuarios | /admin/users | admin_users_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_intelligence.html:9 | Membresías | /admin/memberships | admin_memberships_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_intelligence.html:9 | Automatización | /admin/automation | admin_automation_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_intelligence.html:28 | {{ u.name }} {{ u.email }} · {{ u.membership }} PRO | /admin/users | admin_users_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_intelligence.html:36 | {{ u.name }} Termina {{ u.membership_end_date }} · {{ u.membership_days_left }} días {{ u.membership }} | /admin/users | admin_users_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_intelligence.html:47 | {{ u.name }} {{ u.email }} {{ u.membership }} | /admin/users | admin_users_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_intelligence_center.html:7 | Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_intelligence_center.html:7 | Betting Center | /admin/betting-center | admin_v808_betting_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_intelligence_center.html:7 | Picks | /admin/picks | admin_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_intelligence_engine.html:8 | Revisar inteligencia | /admin/recommendations | v566_admin_recommendations_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_intelligence_engine.html:9 | Ver estado | /admin/intelligence-center | admin_v808_intelligence_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_intelligence_engine.html:10 | Betting Center | /admin/betting-center | admin_v808_betting_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_intelligence_engine.html:11 | Publicar picks | /admin/picks | admin_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_intelligence_engine.html:52 | Ver partido | /match/{{ r.match_id }} | dynamic_template | public | WARNING | — |
| templates/admin_intelligence_engine.html:53 | Revisar en Admin Picks | /admin/picks | admin_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_launch_center.html:9 | Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_launch_center.html:10 | Picks | /admin/picks | admin_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_launch_center.html:11 | Recomendaciones | /admin/betting-center | admin_v808_betting_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_launch_center.html:12 | Telegram | /admin/telegram | admin_telegram_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_legal_compliance.html:9 | Legal público | /legal | v566_legal_page | public | OK | — |
| templates/admin_legal_compliance.html:9 | Checkout cliente | /membresias | membership_page | public | OK | — |
| templates/admin_legal_compliance.html:9 | API | /api/admin/legal-compliance | api_admin_v787_legal_compliance | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_live_depth.html:10 | Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_live_depth.html:11 | Revisar fuentes | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_live_depth.html:28 | {{ match.v554_stats.label }}             {{ match.home_team }} vs {{ match.away_team }}             {{ (match.league_name or match.competition_name)\|competition_es }} · intensidad  | /match/{{ match.id }} | dynamic_template | public | WARNING | — |
| templates/admin_live_experience.html:11 | Live QA | /admin/live-experience | admin_live_experience_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_live_experience.html:12 | Ver cliente | /live | live_page | public | OK | — |
| templates/admin_live_experience.html:13 | Sale Ready | /admin/sale-ready | admin_sale_ready_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_live_experience.html:14 | Calendario | /admin/calendar-experience | admin_calendar_experience_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_login.html:9 | Formulario | /admin-login{% if request.args.get('next') %}?next={{ request.args.get('next')\|urlencode }}{% endif %} | dynamic_template | admin | WARNING | — |
| templates/admin_login.html:16 | Recuperar acceso admin | /admin-forgot-password | admin_forgot_password_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_login.html:17 | Volver al inicio | / | home | public | OK | — |
| templates/admin_login.html:22 | Inicio público | / | home | public | OK | — |
| templates/admin_match_intelligence.html:11 | Match Intelligence | /admin/match-intelligence | admin_match_intelligence_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_match_intelligence.html:12 | Readiness V745 | /admin/top-app-readiness | admin_top_app_readiness_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_match_intelligence.html:13 | Datos | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_matches_sync.html:11 | Formulario | /admin/matches-sync | admin_matches_sync_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_memberships.html:10 | Gestionar usuarios | /admin/users | admin_users_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_navigation_integrity.html:8 | Ver 404 | /admin/not-found-events | admin_not_found_events_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_navigation_integrity.html:37 | Abrir historial | /admin/not-found-events | admin_not_found_events_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_navigation_integrity.html:44 | Salud de rutas | /admin/route-health | admin_route_health_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_navigation_integrity.html:44 | Mapa admin | /admin/map | admin_v808_navigation_map_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_navigation_integrity.html:44 | Sentinel Issues | /admin/sentinel-issues | admin_sentinel_issues_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_navigation_integrity.html:44 | Workforce | /admin/automation-workforce | admin_automation_workforce_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_navigation_integrity.html:54 | Acción JavaScript | /api/admin/navigation-integrity/run | api_admin_navigation_integrity_run | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_navigation_map.html:18 | Panel | /admin/control-center | v566_admin_dashboard_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_navigation_map.html:19 | Vista cliente | /sports-hub | sports_hub_page | public | OK | — |
| templates/admin_navigation_map.html:20 | Mapa cliente | /app/mapa | v809_client_navigation_map_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/admin_navigation_map.html:21 | Calendario cliente | /calendar?lane=today | calendar_page | public | OK | — |
| templates/admin_navigation_map.html:22 | Directo cliente | /live | live_page | public | OK | — |
| templates/admin_navigation_map.html:23 | Picks cliente | /picks | picks_page | public | OK | — |
| templates/admin_navigation_map.html:24 | Salir | /logout | logout_page | public | OK | — |
| templates/admin_navigation_map.html:33 | {{ item.title }}           {{ item.body }}           Abrir → | {{ item.href }} | dynamic_template | public | WARNING | — |
| templates/admin_not_found_events.html:11 | Ver Sentinel | /admin/sentinel-issues | admin_sentinel_issues_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_not_found_events.html:40 | Copiar prompt Codex | — | — | public | WARNING | — |
| templates/admin_observability.html:8 | Observabilidad | /admin/observability | admin_observability_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_observability.html:9 | Errores | /admin/observability/errors | admin_observability_errors_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_observability.html:10 | Beta Center | /admin/beta-center | admin_v808_beta_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_observability.html:11 | Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_observability.html:12 | API resumen | /api/observability/summary | api_observability_summary | public | OK | — |
| templates/admin_observability.html:52 | Ver detalle | /admin/observability/errorserror_id={{ event.error_id }} | dynamic_template | admin | WARNING | — |
| templates/admin_observability_errors.html:8 | Resumen | /admin/observability | admin_observability_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_observability_errors.html:9 | API errores | /api/observability/errors | api_observability_errors | public | OK | — |
| templates/admin_observability_errors.html:10 | Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_observability_errors.html:24 | Ver detalle | /admin/observability/errorserror_id={{ item.error_id }} | dynamic_template | admin | WARNING | — |
| templates/admin_picks.html:11 | Formulario | /admin/picks | admin_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_production_readiness.html:9 | Sistema | /admin/system | admin_system_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_production_readiness.html:10 | Telegram | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_production_readiness.html:11 | Rutas | /admin/route-health | admin_route_health_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_production_readiness.html:12 | Cliente QA | /admin/client-experience | admin_client_experience_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_production_readiness.html:13 | Producción | /admin/production-readiness | admin_production_readiness_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_public_launch.html:64 | Producción Render, env y checklist | /admin/production-readiness | admin_production_readiness_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_public_launch.html:65 | Telegram Status, dry-run y preview | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_public_launch.html:66 | Track record ROI y resultados reales | /admin/track-record | admin_track_record_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_public_launch.html:67 | Pagos Stripe y suscripciones | /admin/payments | admin_payments_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_quality_center.html:34 | Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_quality_center.html:35 | Sincronizar partidos | /admin/matches-sync | admin_matches_sync_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_quality_center.html:36 | Escudos SportsDB | /admin/sportsdb-sync | admin_sportsdb_sync_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_quality_center.html:37 | Gestionar picks | /admin/picks | admin_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_quality_center.html:38 | Telegram | /admin/telegram | admin_telegram_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_quality_center.html:39 | JSON calidad | /api/quality-center/summary | api_quality_center_summary | public | OK | — |
| templates/admin_retention_center.html:37 | Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_retention_center.html:38 | Picks | /admin/picks | admin_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_retention_center.html:39 | Telegram | /admin/telegram | admin_telegram_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_route_health.html:9 | Sistema | /admin/system | admin_system_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_route_health.html:10 | Telegram | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_route_health.html:11 | Codex | /admin/codex-automation | admin_codex_automation_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_route_health.html:12 | Rutas | /admin/route-health | admin_route_health_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_route_health.html:13 | Producción | /admin/production-readiness | admin_production_readiness_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sale_ready.html:9 | Sale Ready | /admin/sale-ready | admin_sale_ready_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sale_ready.html:10 | Live QA | /admin/live-experience | admin_live_experience_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sale_ready.html:11 | Telegram | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sale_ready.html:12 | Calendario | /admin/calendar-experience | admin_calendar_experience_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sale_ready.html:13 | Visual | /admin/client-visual-qa | admin_client_visual_qa_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sale_ready.html:14 | Track Record | /admin/track-record | admin_track_record_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sale_ready.html:28 | Abrir directo | /live | live_page | public | OK | — |
| templates/admin_sale_ready.html:29 | Abrir calendario | /calendar | calendar_page | public | OK | — |
| templates/admin_sale_ready.html:30 | Abrir picks | /picks | picks_page | public | OK | — |
| templates/admin_sale_ready.html:31 | Diagnóstico | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sale_ready.html:32 | Vista cliente | /track-record | public_track_record_page | public | OK | — |
| templates/admin_sale_ready.html:33 | Runtime | /api/runtime-version | api_runtime_version | public | OK | — |
| templates/admin_sentinel_autopilot.html:9 | Ejecutar revisión segura | /api/admin/sentinel-autopilot/run?dry_run=1 | api_admin_sentinel_autopilot_run | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sentinel_autopilot.html:10 | Ver Centro de Incidencias | /admin/sentinel-issues | admin_sentinel_issues_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sentinel_autopilot.html:11 | Generar prompt Codex | /api/admin/sentinel-autopilot/generate-prompt | api_admin_sentinel_autopilot_generate_prompt | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sentinel_autopilot.html:12 | Exportar reporte | /api/admin/sentinel-autopilot/summary | api_admin_sentinel_autopilot_summary | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sentinel_codex_outbox.html:10 | Regenerar outbox | — | — | public | WARNING | — |
| templates/admin_sentinel_codex_outbox.html:11 | Ver JSON seguro | — | — | public | WARNING | — |
| templates/admin_sentinel_codex_outbox.html:12 | Volver al Sentinel | /admin/autonomous-company-sentinel | admin_autonomous_sentinel_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sentinel_codex_outbox.html:39 | Ver pipeline | /admin/autonomous-company-sentinel | admin_autonomous_sentinel_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sentinel_codex_outbox.html:40 | Ver gaps | — | — | public | WARNING | — |
| templates/admin_sentinel_codex_outbox.html:64 | Abrir outbox JSON | — | — | public | WARNING | — |
| templates/admin_sentinel_codex_outbox.html:65 | Ver gaps visuales | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:10 | Formulario | /api/admin/sentinel/issues/scan | api_admin_sentinel_issues_scan | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sentinel_issues.html:13 | Formulario | /api/admin/sentinel/issues/sync-autopilot | api_admin_sentinel_issues_sync_autopilot | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sentinel_issues.html:16 | Formulario | /api/admin/sentinel/issues/sync-visual-worker | api_admin_sentinel_issues_sync_visual_worker | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sentinel_issues.html:19 | Ver JSON seguro | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:48 | Todas | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:49 | Solo críticas | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:50 | Abiertas | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:51 | Codex Ready | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:52 | Reference gap | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:53 | Browser QA | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:54 | Mobile | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:55 | Desktop | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:56 | Admin | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:57 | Client | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:86 | Copiar fallo | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:87 | Copiar prompt Codex | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:124 | Copiar fallo | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:125 | Copiar prompt | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:126 | Copiar evidencia | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:127 | Checklist | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:128 | Marcar en revision | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:129 | Marcar como corregido | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:130 | Falso positivo | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:131 | Reabrir incidencia | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:132 | Ver JSON | — | — | public | WARNING | — |
| templates/admin_sentinel_issues.html:134 | Ver ruta | {{ issue.route }} | dynamic_template | public | WARNING | — |
| templates/admin_sentinel_issues.html:201 | Acción JavaScript | /api/admin/sentinel/issues/{{dynamic}} | dynamic_template | admin | WARNING | — |
| templates/admin_sentinel_workflow.html:10 | Ejecutar diagnóstico | — | — | public | WARNING | — |
| templates/admin_sentinel_workflow.html:60 | Ejecutar workflow | — | — | public | WARNING | — |
| templates/admin_shark_center.html:37 | API estado SHARK | /api/admin/shark-center | api_v570_admin_shark_center | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_shark_center.html:38 | API pregunta | /api/shark/ask?q=estado | api_shark_ask | public | OK | — |
| templates/admin_shark_center.html:39 | Telegram V844 | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_shark_center.html:40 | Vista cliente | /app | v757_client_app_center_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/admin_shark_sentinel.html:10 | Ejecutar diagnóstico admin | — | — | public | WARNING | — |
| templates/admin_shark_sentinel.html:130 | Acción JavaScript | /api/admin/shark-sentinel/run | api_admin_shark_sentinel_run | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sportsdb_feed.html:8 | Usuarios | /admin/users | admin_users_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sportsdb_feed.html:9 | Escudos | /admin/sportsdb-sync | admin_sportsdb_sync_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sportsdb_feed.html:10 | Feed real | /admin/sportsdb-feed | admin_sportsdb_feed_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sportsdb_feed.html:11 | Sistema | /admin/system | admin_system_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sportsdb_feed.html:24 | Formulario | /admin/sportsdb-feed | admin_sportsdb_feed_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sportsdb_sync.html:8 | Usuarios | /admin/users | admin_users_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sportsdb_sync.html:9 | SportsDB Feed | /admin/sportsdb-feed | admin_sportsdb_feed_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sportsdb_sync.html:10 | Import Center | /admin/import-center | import_center | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sportsdb_sync.html:11 | SportsDB Sync | /admin/sportsdb-sync | admin_sportsdb_sync_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_sportsdb_sync.html:12 | Diagnósticos | /api/thesportsdb/diagnostics | api_thesportsdb_diagnostics | public | OK | — |
| templates/admin_sportsdb_sync.html:25 | Formulario | /admin/sportsdb-sync | admin_sportsdb_sync_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_support_center.html:43 | Ver Launch Center | /admin/launch-center | admin_v808_launch_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram.html:8 | Telegram | /admin/telegram | admin_telegram_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram.html:9 | Command Center | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram.html:10 | Diagnóstico | /admin/telegram/diagnostics | admin_telegram_diagnostics_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram.html:11 | Automatización | /admin/automation | admin_automation_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram.html:12 | Datos | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram.html:61 | Formulario | /admin/telegram | admin_telegram_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram.html:73 | Formulario | /admin/telegram | admin_telegram_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram.html:74 | Formulario | /admin/telegram | admin_telegram_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram.html:75 | Formulario | /admin/telegram | admin_telegram_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram.html:76 | Formulario | /admin/telegram | admin_telegram_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram.html:77 | Formulario | /admin/telegram | admin_telegram_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram_audit.html:8 | Telegram | /admin/telegram | admin_telegram_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram_audit.html:9 | Piloto automático de picks | /admin/autopilot-audit | admin_v808_autopilot_audit_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram_audit.html:10 | Picks | /admin/picks | admin_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram_audit.html:11 | Abrir Command Center | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram_pro_preview.html:11 | Command Center | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram_pro_preview.html:11 | API preview | /api/admin/telegram/pro-preview | api_admin_v810_telegram_pro_preview | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_telegram_pro_preview.html:11 | Mapa admin | /admin/map | admin_v808_navigation_map_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_top_app_readiness.html:10 | Readiness | /admin/top-app-readiness | admin_top_app_readiness_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_top_app_readiness.html:11 | Data Vault | /admin/data-vault | admin_data_vault_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_top_app_readiness.html:12 | Match Intelligence | /admin/match-intelligence | admin_match_intelligence_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_top_app_readiness.html:13 | Highlights | /admin/video-highlights | admin_video_highlights_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_top_app_readiness.html:14 | Alertas | /admin/alerts | admin_alerts_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_track_record.html:32 | Ver vista cliente | /track-record | public_track_record_page | public | OK | — |
| templates/admin_unified_intelligence.html:20 | {{ tab.tab }} {{ tab.title }} {{ tab.value }} {{ tab.body }} | {{ tab.href }} | dynamic_template | public | WARNING | — |
| templates/admin_user_import.html:8 | Usuarios | /admin/users | admin_users_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_user_import.html:9 | Importar usuarios | /admin/user-import | admin_user_import_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_user_import.html:10 | Import Center | /admin/import-center | import_center | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_user_import.html:14 | Formulario | /admin/user-import | admin_user_import_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_users.html:10 | Formulario | /admin/users | admin_users_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_video_highlights.html:11 | Highlights | /admin/video-highlights | admin_video_highlights_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_video_highlights.html:12 | Derechos | /admin/content-rights | admin_content_rights_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_video_highlights.html:13 | Readiness | /admin/top-app-readiness | admin_top_app_readiness_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_visual_experience.html:10 | Ver experiencia cliente | /sports-hub | sports_hub_page | public | OK | — |
| templates/admin_visual_experience.html:11 | QA cliente | /admin/client-experience | admin_client_experience_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_visual_experience.html:12 | Go Live | /admin/go-live | admin_go_live_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_visual_worker.html:39 | Ejecutar visual | /api/admin/visual-worker/run?mode=visual-worker&dry_run=1 | api_admin_visual_worker_run | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_visual_worker.html:40 | Full company QA | /api/admin/visual-worker/run?mode=full-company-qa&dry_run=1 | api_admin_visual_worker_run | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/admin_visual_worker.html:41 | Enviar hallazgos a Incidencias | /admin/sentinel-issues | admin_sentinel_issues_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/alerts.html:7 | Volver al perfil | /perfil | profile_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/alerts.html:7 | Partidos | /match-hub | match_hub_page | public | OK | — |
| templates/alerts.html:7 | Picks | /picks | picks_page | public | OK | — |
| templates/alerts.html:13 | {{ alert.badge }}         {{ alert.title }}         {{ alert.body }} | {{ alert.href }} | dynamic_template | public | WARNING | — |
| templates/alerts.html:27 | {{ data.retention.next_best_action.badge }} {{ data.retention.next_best_action.title }} {{ data.retention.next_best_action.body }} | {{ data.retention.next_best_action.href }} | dynamic_template | public | WARNING | — |
| templates/alerts.html:31 | Ver actividad | /actividad | activity_page | public | OK | — |
| templates/auto_picks.html:7 | Picks publicados | /picks | picks_page | public | OK | — |
| templates/auto_picks.html:7 | {{ data.membership.next_cta }} | /membresias | membership_page | public | OK | — |
| templates/autonomous_ecosystem.html:8 | Ver Auto Picks | /auto-picks | v566_auto_picks_page | public | OK | — |
| templates/autonomous_ecosystem.html:9 | Recomendaciones | /recomendaciones | v566_recommendations_page | public | OK | — |
| templates/autonomous_ecosystem.html:10 | Picks publicados | /picks | picks_page | public | OK | — |
| templates/autonomous_ecosystem.html:32 | Detalle | {{ item.detail_url }} | dynamic_template | public | WARNING | — |
| templates/base.html:156 | Partidos | /calendar | calendar_page | public | OK | — |
| templates/base.html:157 | Directo | /live | live_page | public | OK | — |
| templates/base.html:158 | Picks | /picks | picks_page | public | OK | — |
| templates/base.html:159 | Planes | /membresias | membership_page | public | OK | — |
| templates/base.html:160 | Entrar | /cliente-login | client_login_page | public | OK | — |
| templates/base.html:161 | Crear cuenta | /registro | register_page | public | OK | — |
| templates/base.html:188 | {{ label }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/base.html:194 | Salir | /logout | logout_page | public | OK | — |
| templates/base.html:212 | Panel  Control | /admin/control-center | v566_admin_dashboard_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:213 | Workers  Empresa OS | /admin/company-os | admin_company_os_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:214 | Board  Product Board | /admin/company-audit | admin_company_audit_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:215 | AutoPilot  Self Improve | /admin/sentinel-autopilot | admin_sentinel_autopilot_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:216 | Visual  Worker | /admin/visual-worker | admin_visual_company_worker_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:217 | Mejora  Auto OS | /admin/auto-improvement | admin_auto_improvement_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:218 | Sentinel  QA Bot | /admin/shark-sentinel | admin_continuous_sentinel_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:219 | Loop  QA Loop | /admin/continuous-sentinel | admin_continuous_sentinel_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:220 | Workflow  Fix OS | /admin/sentinel-workflow | admin_sentinel_workflow_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:221 | Mapa  Rutas | /admin/map | admin_v808_navigation_map_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:222 | Clientes  Usuarios | /admin/users | admin_users_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:223 | Datos  Centro | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:224 | API  Sports | /admin/api-sports | admin_api_sports_audit_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:225 | Partidos  Sync | /admin/matches-sync | admin_matches_sync_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:226 | Directo  Live | /admin/live-depth | admin_live_depth_alias | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:227 | Picks  Control | /admin/picks | admin_picks_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:228 | Telegram  Canal | /admin/telegram/command-center | admin_telegram_command_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:229 | Preview  Mensajes | /admin/telegram/pro-preview | admin_v810_telegram_pro_preview_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:230 | Auto  Jobs | /admin/automation-center | admin_v773_automation_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:231 | Daily  Cron | /admin/daily-automation | admin_v818_daily_automation_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:232 | OS  Motor | /admin/automation-os | admin_v818_daily_automation_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:233 | Calidad  QA | /admin/app-experience-quality | admin_v773_app_experience_quality_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/base.html:235 | Vista pública | /sports-hub | sports_hub_page | public | OK | — |
| templates/base.html:235 | Cerrar sesión admin | /logout | logout_page | public | OK | — |
| templates/base.html:249 | Legal | /legal | v566_legal_page | public | OK | — |
| templates/base.html:249 | Términos | /terminos | v787_terms_page | public | OK | — |
| templates/base.html:249 | Privacidad | /privacidad | v787_privacy_page | public | OK | — |
| templates/base.html:249 | Juego responsable | /juego-responsable | v566_responsible_betting_page | public | OK | — |
| templates/base.html:249 | Soporte | /support | v724_contact_alias_page | public | OK | — |
| templates/base.html:256 | Inicio | /app | v757_client_app_center_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/base.html:257 | Partidos | /partidos | calendar_page | public | OK | — |
| templates/base.html:258 | Directo | /live | live_page | public | OK | — |
| templates/base.html:259 | Picks | /picks | picks_page | public | OK | — |
| templates/base.html:260 | SHARK | /shark | shark_page | public | OK | — |
| templates/base.html:262 | Inicio | / | home | public | OK | — |
| templates/base.html:263 | Partidos | /calendar | calendar_page | public | OK | — |
| templates/base.html:264 | Directo | /live | live_page | public | OK | — |
| templates/base.html:265 | Picks | /picks | picks_page | public | OK | — |
| templates/base.html:266 | Entrar | /cliente-login | client_login_page | public | OK | — |
| templates/base.html:273 | SHARK | — | — | public | WARNING | — |
| templates/base.html:277 | x | — | — | public | WARNING | — |
| templates/base.html:298 | Abrir SHARK | /shark | shark_page | public | OK | — |
| templates/base.html:400 | Arriba | — | — | public | WARNING | — |
| templates/base.html:326 | Acción JavaScript | /api/shark/ask | api_shark_ask | public | OK | — |
| templates/base.html:328 | Acción JavaScript | /api/shark/ask?q={{dynamic}} | dynamic_template | public | WARNING | — |
| templates/base.html:350 | Acción JavaScript | /api/favorites | api_favorites | public | OK | — |
| templates/base.html:579 | Acción JavaScript | /api/runtime-version | api_runtime_version | public | OK | — |
| templates/beta.html:29 | Formulario | /api/beta/join | — | public | RUTA_SIN_ACCESO_UI | Archivar o reactivar la plantilla antes de exponerla en navegacion. |
| templates/betting_markets.html:6 | Ver picks | /picks | picks_page | public | OK | — |
| templates/betting_markets.html:6 | Combis | /combis | combis_page | public | OK | — |
| templates/betting_markets.html:6 | Partidos con pick | /calendar?lane=with_pick | calendar_page | public | OK | — |
| templates/betting_markets.html:8 | {{ market.get('label') }} {{ market.get('client_label') or market.get('description') }}  Riesgo {{ market.get('risk') or 'Medio' }} | /mercados?tipo={{ market.get('key') }} | dynamic_template | public | WARNING | — |
| templates/betting_markets.html:9 | Abrir combis | /combis | combis_page | public | OK | — |
| templates/betting_recommendations.html:8 | Picks publicados | /picks | picks_page | public | OK | — |
| templates/betting_recommendations.html:9 | Combinadas | /combis | combis_page | public | OK | — |
| templates/betting_recommendations.html:10 | Calendario | /match-hub | match_hub_page | public | OK | — |
| templates/betting_recommendations.html:11 | Admin recomendaciones | /admin/betting-center | admin_v808_betting_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/betting_recommendations.html:26 | Ver partido | /match/{{ r.match_id }} | dynamic_template | public | WARNING | — |
| templates/betting_recommendations.html:26 | Publicar pick | /api/betting/convert-to-pickid={{ r.id }}&publish=1 | dynamic_template | public | WARNING | — |
| templates/calendar.html:22 | Formulario | /calendar | calendar_page | public | OK | — |
| templates/client_app_center.html:49 | Ver análisis completo | /picks | picks_page | public | OK | — |
| templates/client_login.html:11 | Formulario | /cliente-login | client_login_page | public | OK | — |
| templates/client_login.html:20 | He olvidado mi contraseña | /forgot-password | forgot_password_page | public | OK | — |
| templates/client_login.html:25 | {{ 'Crear cuenta y seguir' if selected in ['PRO','ELITE'] else 'Crear cuenta' }} | /registro{% if selected in ['PRO','ELITE'] %}?plan={{ selected }}&next={{ next_url\|urlencode }}{% endif %} | dynamic_template | public | WARNING | — |
| templates/client_login.html:26 | Ver planes y precios | /membresias | membership_page | public | OK | — |
| templates/client_menu.html:10 | Inicio | /app | v757_client_app_center_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/client_menu.html:10 | Hoy | /calendar?lane=today | calendar_page | public | OK | — |
| templates/client_menu.html:10 | Picks | /picks | picks_page | public | OK | — |
| templates/client_menu.html:10 | SHARK | /shark | shark_page | public | OK | — |
| templates/client_menu.html:15 | Ver partidos Hoy, directo y calendario. Lo primero que mira el cliente. | /calendar?lane=today | calendar_page | public | OK | — |
| templates/client_menu.html:16 | Picks Picks, combis y mercados. Cuota, stake, riesgo y motivo. | /picks | picks_page | public | OK | — |
| templates/client_menu.html:17 | Resultados Histórico, ROI y resúmenes. Solo datos reales cerrados. | /track-record | public_track_record_page | public | OK | — |
| templates/client_menu.html:18 | Alertas Telegram, cuenta y ayuda. Seguimiento sin entrar cada minuto. | /telegram | telegram_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/client_menu.html:26 | {{ item.title }} {{ item.body }} | {{ item.href }} | dynamic_template | public | WARNING | — |
| templates/client_navigation_map.html:10 | Partidos de hoy | /calendar?lane=today | calendar_page | public | OK | — |
| templates/client_navigation_map.html:10 | Directo | /live | live_page | public | OK | — |
| templates/client_navigation_map.html:10 | SHARK | /shark | shark_page | public | OK | — |
| templates/client_navigation_map.html:20 | 1 Partido elige encuentro real | /calendar?lane=today | calendar_page | public | OK | — |
| templates/client_navigation_map.html:21 | 2 Directo minuto y marcador | /live | live_page | public | OK | — |
| templates/client_navigation_map.html:22 | 3 Pick cuota y riesgo | /picks | picks_page | public | OK | — |
| templates/client_navigation_map.html:23 | 4 SHARK consulta final | /shark | shark_page | public | OK | — |
| templates/client_navigation_map.html:32 | {{ item.icon }}             {{ item.title }}             {{ item.body }}             Abrir → | {{ item.href }} | dynamic_template | public | WARNING | — |
| templates/client_overview.html:9 | Ver picks | /picks | picks_page | public | OK | — |
| templates/client_overview.html:10 | Recomendaciones | /recomendaciones | v566_recommendations_page | public | OK | — |
| templates/client_overview.html:11 | Live | /live | live_page | public | OK | — |
| templates/client_overview.html:12 | SHARK | /shark | shark_page | public | OK | — |
| templates/client_overview.html:30 | {{ item.type }} {{ item.title }} {{ item.body }} | {{ item.href }} | dynamic_template | public | WARNING | — |
| templates/client_overview.html:37 | Todos | /match-hub | match_hub_page | public | OK | — |
| templates/client_overview.html:40 | {{ m.home_team }} vs {{ m.away_team }} {{ m.league_name or m.competition_name or 'Competición' }} {{ m\|match_time_short }} | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/client_overview.html:45 | Ver picks | /picks | picks_page | public | OK | — |
| templates/client_overview.html:48 | {{ p.selection_display or p.selection or p.title or 'Pick publicado' }} {{ p.home_team }} {{ p.away_team and 'vs ' ~ p.away_team }} {{ p.confidence or p.score or 70 }}% | /picks | picks_page | public | OK | — |
| templates/client_overview.html:55 | Más | /menu | v566_client_menu_page | public | OK | — |
| templates/client_overview.html:57 | Resultados FT | /resultados | match_hub_page | public | OK | — |
| templates/client_overview.html:58 | Combis PRO | /combis | combis_page | public | OK | — |
| templates/client_overview.html:59 | Favoritos Feed | /favorites | favorites_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/client_overview.html:60 | Telegram Plan | /telegram | telegram_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/client_overview.html:61 | Auto Picks ELITE | /auto-picks | v566_auto_picks_page | public | OK | — |
| templates/client_overview.html:62 | Cuenta Yo | /mi-cuenta | account_center_page | public | OK | — |
| templates/client_success.html:10 | Siguiente paso | {{ success.next_actions[0].href if success.next_actions else '/sports-hub' }} | dynamic_template | public | WARNING | — |
| templates/client_success.html:11 | Inicio deportivo | /sports-hub | sports_hub_page | public | OK | — |
| templates/client_success.html:12 | Soporte | /ayuda#soporte | client_success_page | public | OK | — |
| templates/client_success.html:27 | {{ action.priority\|title }} {{ action.title }} | {{ action.href }} | dynamic_template | public | WARNING | — |
| templates/client_success.html:40 | {{ pillar.cta }} | {{ pillar.href }} | dynamic_template | public | WARNING | — |
| templates/client_success.html:52 | Enviar incidencia | /contact | v724_contact_alias_page | public | OK | — |
| templates/combis.html:6 | Combi responsable | /combis?tipo=mixta&partidos=3 | combis_page | public | OK | — |
| templates/combis.html:6 | Picks base | /picks | picks_page | public | OK | — |
| templates/combis.html:6 | Mercados | /mercados | betting_markets_page | public | OK | — |
| templates/combis.html:6 | {{ cb.get('plan') or (current_user.membership if current_user else 'FREE') }} Plan | — | — | public | RUTA_INTERNA_NO_DEBE_SER_VISIBLE | — |
| templates/combis.html:8 | Picks | /picks | picks_page | public | OK | — |
| templates/combis.html:8 | Combis | /combis | combis_page | public | OK | — |
| templates/combis.html:8 | Mercados | /mercados | betting_markets_page | public | OK | — |
| templates/combis.html:8 | Partidos con pick | /calendar?lane=with_pick | calendar_page | public | OK | — |
| templates/combis.html:11 | {{ ctx.client_date_label }} {{ ctx.client_time_label }} {{ ctx.safe_home }} vs {{ ctx.safe_away }} {{ ctx.client_competition }} Base | /match/{{ m.get('id') }} | dynamic_template | public | WARNING | — |
| templates/components/v827_design_system.html:6 | {{ primary_label }} | {{ primary_href }} | dynamic_template | public | WARNING | — |
| templates/components/v827_design_system.html:15 | {{ label }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/components/v832_design_system.html:7 | {{ primary_label }} | {{ primary_href }} | dynamic_template | public | WARNING | — |
| templates/components/v832_design_system.html:8 | {{ secondary_label }} | {{ secondary_href }} | dynamic_template | public | WARNING | — |
| templates/components/v832_design_system.html:16 | {{ item.kicker }}           {{ item.label }} | {{ item.href }} | dynamic_template | public | WARNING | — |
| templates/components/v832_design_system.html:25 | {{ title }}       {{ value }}      {% if detail %} {{ detail }} {% endif %} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/components/v928_navigation.html:8 | Partidos | /calendar | calendar_page | public | OK | — |
| templates/components/v928_navigation.html:8 | Directo | /live | live_page | public | OK | — |
| templates/components/v928_navigation.html:8 | Picks | /picks | picks_page | public | OK | — |
| templates/components/v928_navigation.html:8 | Planes | /membresias | membership_page | public | OK | — |
| templates/components/v928_navigation.html:8 | Entrar | /cliente-login | client_login_page | public | OK | — |
| templates/components/v928_navigation.html:8 | Crear cuenta | /registro | register_page | public | OK | — |
| templates/components/v928_navigation.html:14 | Entrar | /cliente-login | client_login_page | public | OK | — |
| templates/components/v928_navigation.html:24 | {{ label }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/components/v928_navigation.html:31 | Abrir cuenta | /profile | profile_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/components/v928_navigation.html:40 | {{ label }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/components/v928_navigation.html:43 | Cerrar sesión admin | /logout | logout_page | public | OK | — |
| templates/components/v928_navigation.html:49 | Formulario | /admin/map | admin_v808_navigation_map_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/components/v928_navigation.html:50 | Incidencias | /admin/sentinel-issues | admin_sentinel_issues_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/components/v928_navigation.html:50 | Administrador Panel protegido | /admin/automation-workforce | admin_automation_workforce_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/components/v928_navigation.html:57 | {{ label }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/components/v928_ui.html:18 | {{ action_label }}  → | {{ action_href }} | dynamic_template | public | WARNING | — |
| templates/components/v928_ui.html:31 | {{ action.get('label') or 'Abrir' }} | {{ action.get('href') or '#' }} | dynamic_template | public | WARNING | — |
| templates/components/v928_ui.html:51 | {{ icon(icon_name) }}    {{ title }} {{ body }}     → | {{ href }} | dynamic_template | public | WARNING | — |
| templates/components/v928_ui.html:62 | {{ action_label }} | {{ action_href }} | dynamic_template | public | WARNING | — |
| templates/components/v928_ui.html:104 | Ver partido | /match/{{ match_id }} | dynamic_template | public | WARNING | — |
| templates/components/v928_ui.html:137 | {{ item.get('label') or item.get('key') }} | {{ item.get('href') or '#' }} | dynamic_template | public | WARNING | — |
| templates/components/v928_ui.html:146 | {{ label }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/components/v928_ui.html:155 | {{ 'Plan actual' if current else 'Elegir ' ~ name }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/components/v928_ui.html:207 | {{ action_label or 'Revisar' }} | {{ action_href }} | dynamic_template | public | WARNING | — |
| templates/components/v928_ui.html:215 | Abrir | {{ href }} | dynamic_template | public | WARNING | — |
| templates/components/v928_ui.html:227 | Ver reporte | {{ report_href }} | dynamic_template | public | WARNING | — |
| templates/components/v930_navigation.html:11 | {{ label }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/components/v930_navigation.html:16 | {{ plan }} | /memberships | membership_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/components/v930_navigation.html:28 | Abrir cuenta | /profile | profile_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/components/v930_navigation.html:37 | Partidos | /calendar | calendar_page | public | OK | — |
| templates/components/v930_navigation.html:37 | Directo | /live | live_page | public | OK | — |
| templates/components/v930_navigation.html:37 | Picks | /picks | picks_page | public | OK | — |
| templates/components/v930_navigation.html:37 | Planes | /memberships | membership_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/components/v930_navigation.html:37 | Entrar | /cliente-login | client_login_page | public | OK | — |
| templates/components/v930_navigation.html:37 | Crear cuenta | /registro | register_page | public | OK | — |
| templates/components/v930_navigation.html:43 | Entrar | /cliente-login | client_login_page | public | OK | — |
| templates/components/v930_navigation.html:54 | {{ label }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/components/v930_navigation.html:58 | Cerrar sesión admin | /logout | logout_page | public | OK | — |
| templates/components/v930_navigation.html:64 | Formulario | /admin/map | admin_v808_navigation_map_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/components/v930_navigation.html:65 | Incidencias | /admin/sentinel-issues | admin_sentinel_issues_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/components/v930_navigation.html:65 | Administrador Panel protegido | /admin/automation-workforce | admin_automation_workforce_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/components/v930_navigation.html:79 | {{ label }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/components/v930_navigation.html:89 | {{ label }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/components/v930_ui.html:7 | {{ label }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/components/v930_ui.html:7 | {{ label }} | — | — | public | WARNING | — |
| templates/crests.html:9 | Ver partidos | /match-hub | match_hub_page | public | OK | — |
| templates/crests.html:11 | SportsDB Sync | /admin/sportsdb-sync | admin_sportsdb_sync_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/crests.html:12 | Import Center | /admin/import-center | import_center | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/crests.html:27 | Ver partido | /match-hub | match_hub_page | public | OK | — |
| templates/daily_briefing.html:11 | {{ briefing.next_action.title }} | {{ briefing.next_action.href }} | dynamic_template | public | WARNING | — |
| templates/daily_briefing.html:12 | Partidos | /match-hub | match_hub_page | public | OK | — |
| templates/daily_briefing.html:13 | Picks | /picks | picks_page | public | OK | — |
| templates/daily_briefing.html:14 | Favoritos | /favorites | favorites_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/daily_briefing.html:29 | {{ item.label }}         {{ item.value }}         Abrir sección relacionada | {{ item.href }} | dynamic_template | public | WARNING | — |
| templates/daily_briefing.html:41 | {{ briefing.next_action.badge }}         {{ briefing.next_action.title }}         {{ briefing.next_action.body }} | {{ briefing.next_action.href }} | dynamic_template | public | WARNING | — |
| templates/daily_briefing.html:60 | Calendario | /match-hub | match_hub_page | public | OK | — |
| templates/daily_briefing.html:65 | {{ m.safe_home or m.home_team }} vs {{ m.safe_away or m.away_team }} {{ (m.safe_competition or m.competition_name or m.league_name or 'Competición')\|competition_es }} {{ m\|match_ti | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/daily_briefing.html:72 | Abrir | /picks | picks_page | public | OK | — |
| templates/daily_briefing.html:75 | {{ p.home_team }} vs {{ p.away_team }} {{ p.selection_display or p.selection }} {{ p.confidence }}% | /picks | picks_page | public | OK | — |
| templates/daily_briefing.html:84 | Ver todo | /actividad | activity_page | public | OK | — |
| templates/data_depth.html:39 | Calendario | /match-hub | match_hub_page | public | OK | — |
| templates/data_depth.html:42 | {{ m.home_team }} vs {{ m.away_team }} {{ m.league_name or 'Competicion' }} {{ m\|match_time_short }} | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/data_depth.html:47 | Resultados | /resultados | match_hub_page | public | OK | — |
| templates/data_depth.html:50 | {{ m.home_team }} vs {{ m.away_team }} {{ m.league_name or 'Competicion' }} {{ m.home_score or 0 }}-{{ m.away_score or 0 }} | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/discovery.html:7 | Formulario | /explorar | — | public | RUTA_SIN_ACCESO_UI | Archivar o reactivar la plantilla antes de exponerla en navegacion. |
| templates/discovery.html:17 | {{ item.label }} | {{ item.href }} | dynamic_template | public | WARNING | — |
| templates/discovery.html:33 | {{ m.home_team }} vs {{ m.away_team }}           {{ (m.competition_name or m.league_name)\|competition_es }} · {{ m\|match_time_label }}           {{ m.status_info.label if m.status_ | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/discovery.html:49 | {{ (t.name or '')[:2] }} {{ t.name }} {{ t.league or t.country or 'Equipo' }} | /team/{{ t.id or t.key }} | dynamic_template | public | WARNING | — |
| templates/dynamic_mode.html:10 | {{ (dm.primary_action or {}).get('label','Ver calendario') }} | {{ (dm.primary_action or {}).get('href','/calendar') }} | dynamic_template | public | WARNING | — |
| templates/dynamic_mode.html:11 | Hoy | /calendar?lane=today | calendar_page | public | OK | — |
| templates/dynamic_mode.html:12 | Directo | /live?f=live | live_page | public | OK | — |
| templates/dynamic_mode.html:13 | Picks | /picks | picks_page | public | OK | — |
| templates/dynamic_mode.html:27 | {{ action.label }} Ir | {{ action.href }} | dynamic_template | public | WARNING | — |
| templates/dynamic_mode.html:35 | {{ m.client_date_label or (m\|match_date_label) }} {{ m.client_time_label or (m\|match_time_short) }}         {{ m.v764_title }} {{ m.v764_competition }} · {{ m.v764_status }}        | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/ecosystem.html:7 | Abrir inicio | /dashboard | v566_dashboard_page | public | OK | — |
| templates/ecosystem.html:7 | Ver picks | /picks | picks_page | public | OK | — |
| templates/ecosystem.html:21 | {{ m.name }} {{ m.status }} · {{ m.priority }} {{ m.level }} {{ m.detail }} | {{ m.route }} | dynamic_template | public | WARNING | — |
| templates/error_controlled.html:11 | Volver al inicio | / | home | public | OK | — |
| templates/error_controlled.html:12 | Ver partidos en directo | /live | live_page | public | OK | — |
| templates/error_controlled.html:13 | Ver picks | /picks | picks_page | public | OK | — |
| templates/error_controlled.html:15 | Ver detalle admin | /admin/observability/errorserror_id={{ error_id }} | dynamic_template | admin | WARNING | — |
| templates/favorites.html:26 | {% if live_depth.get('badge') == 'live' %}{{ live_depth.get('minute') or 'En directo' }}{% else %}{{ m\|match_time_short }}{% endif %} {{ live_depth.get('label') or (m\|match_date_la | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/favorites.html:27 | ★ | — | — | public | WARNING | — |
| templates/favorites.html:40 | Ver partidos | /sports-hub | sports_hub_page | public | OK | — |
| templates/favorites.html:40 | Ver picks | /picks | picks_page | public | OK | — |
| templates/favorites.html:53 | {{ m.home_team }} vs {{ m.away_team }} {{ (m.competition_name or m.league_name)\|competition_es }} {{ live_depth.get('label') or m.status or 'Live' }} | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/favorites.html:63 | {{ p.selection_display or p.selection or 'Pick SHARK' }} {{ p.home_team }} vs {{ p.away_team }}  {{ p.analysis_badge or 'Análisis' }} {{ p.confidence or 0 }}% | /picks | picks_page | public | OK | — |
| templates/favorites.html:82 | Formulario | /favorites | favorites_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/favorites.html:99 | Formulario | /favorites | favorites_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/growth_client.html:32 | Ver partidos | /match-hub | match_hub_page | public | OK | — |
| templates/growth_client.html:33 | Ver picks | /picks | picks_page | public | OK | — |
| templates/growth_client.html:34 | Configurar favoritos | /favorites | favorites_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/highlight_detail.html:7 | Volver a resúmenes | /resumenes | highlights_page | public | OK | — |
| templates/highlight_detail.html:16 | Ver partido | {{ h.match_url }} | dynamic_template | public | WARNING | — |
| templates/highlight_detail.html:17 | Resultados | /calendar?lane=results | calendar_page | public | OK | — |
| templates/highlight_detail.html:18 | Track Record | /track-record | public_track_record_page | public | OK | — |
| templates/highlight_detail.html:19 | Abrir fuente | {{ h.safe_url }} | dynamic_template | public | WARNING | — |
| templates/highlight_detail.html:28 | link | {{ h.safe_url }} | dynamic_template | public | WARNING | — |
| templates/highlights.html:7 | Resultados | /calendar?lane=results | calendar_page | public | OK | — |
| templates/highlights.html:7 | Resúmenes | /highlights | highlights_page | public | OK | — |
| templates/highlights.html:7 | Calendario | /calendar | calendar_page | public | OK | — |
| templates/highlights.html:7 | {{ (center.get('counts') or {}).get('embeddable',0) }} En app | — | — | public | RUTA_INTERNA_NO_DEBE_SER_VISIBLE | — |
| templates/highlights.html:9 | {% if h.thumbnail_url %} {% endif %} {{ h.match_label }} {{ h.event_date_label }}  {{ h.competition_label }} {{ h.client_status }} | {{ h.detail_url }} | dynamic_template | public | WARNING | — |
| templates/highlights.html:10 | {{ ctx.client_date_label }} {{ ctx.client_time_label }} {{ ctx.safe_home }} vs {{ ctx.safe_away }} {{ ctx.client_competition }}  {{ ctx.client_score_label }} Pendiente | /match/{{ m.get('id') }} | dynamic_template | public | WARNING | — |
| templates/home.html:13 | Abrir mi panel | /app | v757_client_app_center_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/home.html:13 | Ver partidos | /calendar | calendar_page | public | OK | — |
| templates/home.html:13 | Revisar picks | /picks | picks_page | public | OK | — |
| templates/home.html:17 | Crear cuenta | /registro | register_page | public | OK | — |
| templates/home.html:17 | Entrar | /cliente-login | client_login_page | public | OK | — |
| templates/home.html:17 | Ver partidos | /calendar | calendar_page | public | OK | — |
| templates/ia_shark.html:3 | Contexto IA | /api/v506/ecosystem | — | public | RUTA_SIN_ACCESO_UI | Archivar o reactivar la plantilla antes de exponerla en navegacion. |
| templates/ia_shark.html:3 | Picks explicables | /picks | picks_page | public | OK | — |
| templates/import_center.html:8 | Usuarios | /admin/users | admin_users_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/import_center.html:9 | Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/import_center.html:10 | Partidos | /admin/matches-sync | admin_matches_sync_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/import_center.html:11 | Import Center | /admin/import-center | import_center | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/import_center.html:12 | SportsDB Sync | /admin/sportsdb-sync | admin_sportsdb_sync_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/import_center.html:16 | Formulario | /api/import-competitions | api_import_competitions | public | OK | — |
| templates/import_center.html:24 | Formulario | /api/import-results | api_import_results | public | OK | — |
| templates/import_center.html:34 | Formulario | /api/import-matches | api_import_matches | public | OK | — |
| templates/import_center.html:60 | Formulario | /api/import-odds | api_import_odds | public | OK | — |
| templates/import_center.html:71 | Abrir Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/import_center.html:75 | Formulario | /api/import-picks | api_import_picks | public | OK | — |
| templates/import_center.html:87 | Formulario | /api/telegram/send | api_telegram_send | public | OK | — |
| templates/import_center.html:94 | Formulario | /api/import-teams | api_import_teams | public | OK | — |
| templates/legal_basic.html:9 | Crear cuenta | /registro | register_page | public | OK | — |
| templates/legal_basic.html:10 | Ver planes | /membresias | membership_page | public | OK | — |
| templates/legal_basic.html:11 | Juego responsable | /juego-responsable | v566_responsible_betting_page | public | OK | — |
| templates/legal_compliance.html:10 | Ver planes legales | /membresias | membership_page | public | OK | — |
| templates/legal_compliance.html:11 | No somos casa de apuestas | /no-somos-casa-de-apuestas | v787_not_bookmaker_page | public | OK | — |
| templates/legal_compliance.html:12 | Juego responsable | /juego-responsable | v566_responsible_betting_page | public | OK | — |
| templates/legal_compliance.html:24 | {{ item.label }} | {{ item.href }} | dynamic_template | public | WARNING | — |
| templates/legal_trust.html:19 | Configurar juego responsable | /juego-responsable | v566_responsible_betting_page | public | OK | — |
| templates/legal_trust.html:19 | Contactar soporte | /soporte | v724_contact_alias_page | public | OK | — |
| templates/live_depth.html:9 | Volver al directo | /live | live_page | public | OK | — |
| templates/live_depth.html:24 | {{ match.v554_stats.label }} {{ match.minute or '' }}           {{ match.home_team }} vs {{ match.away_team }}           {{ (match.league_name or match.competition_name)\|competitio | /match/{{ match.id }} | dynamic_template | public | WARNING | — |
| templates/live_depth.html:37 | {{ m.safe_home or m.home_team }} vs {{ m.safe_away or m.away_team }} {{ m.league_name or m.competition_name }} · {{ m\|match_full_datetime }} | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/match_detail.html:24 | Resumen | #resumen | fragment | public | OK | — |
| templates/match_detail.html:24 | Picks | #picks | fragment | public | OK | — |
| templates/match_detail.html:24 | Datos | #datos | fragment | public | OK | — |
| templates/match_detail.html:24 | Histórico | #historico | fragment | public | OK | — |
| templates/match_detail.html:24 | SHARK | #shark | fragment | public | OK | — |
| templates/match_detail.html:53 | Analizar este partido | /shark?match={{ match.get('id') }} | dynamic_template | public | WARNING | — |
| templates/match_hub.html:8 | Ver directo | /live | live_page | public | OK | — |
| templates/match_hub.html:8 | Mis favoritos | /favorites | favorites_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/match_hub.html:12 | Hoy | /match-hub?lane=today | match_hub_page | public | OK | — |
| templates/match_hub.html:13 | Mañana | /match-hub?lane=tomorrow | match_hub_page | public | OK | — |
| templates/match_hub.html:14 | Semana | /match-hub?lane=week | match_hub_page | public | OK | — |
| templates/match_hub.html:15 | Directo | /match-hub?lane=live | match_hub_page | public | OK | — |
| templates/match_hub.html:16 | Resultados | /match-hub?lane=results | match_hub_page | public | OK | — |
| templates/match_hub.html:17 | España | /match-hub?lane=spain | match_hub_page | public | OK | — |
| templates/match_hub.html:18 | Internacional | /match-hub?lane=international | match_hub_page | public | OK | — |
| templates/match_hub.html:19 | UEFA | /match-hub?lane=uefa | match_hub_page | public | OK | — |
| templates/match_hub.html:20 | Selecciones | /match-hub?lane=national | match_hub_page | public | OK | — |
| templates/match_hub.html:66 | {{ crest(m\|team_identity('home'), m.safe_home or m.home_team, 'small') }} {{ m.safe_home or m.home_team }} | /team/{{ (m._raw_home_team or m.home_team)\|urlencode }} | dynamic_template | public | WARNING | — |
| templates/match_hub.html:68 | {{ crest(m\|team_identity('away'), m.safe_away or m.away_team, 'small') }} {{ m.safe_away or m.away_team }} | /team/{{ (m._raw_away_team or m.away_team)\|urlencode }} | dynamic_template | public | WARNING | — |
| templates/match_hub.html:71 | Detalle | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/match_hub.html:86 | Sincronizar desde Data Center | /admin/data-center | admin_data_center_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/match_hub.html:86 | Import legal | /admin/import-center | import_center | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/match_hub.html:96 | {{ comp.name }}         {{ comp.country }} · calendario preparado | /match-hub?lane={{ 'spain' if comp.country == 'Spain' else 'uefa' if comp.region == 'UEFA' else 'international' }} | dynamic_template | public | WARNING | — |
| templates/match_hub.html:112 | {{ (m.safe_competition or m.competition_name or m.league_name)\|competition_es }} {{ m\|match_time_label }} {{ m.live_depth.minute }}                   {{ crest(m\|team_identity('home | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/membership.html:13 | {{ 'Plan actual' if current_plan == 'FREE' else 'Crear cuenta' }} | {{ '/app' if current_user else '/registro' }} | dynamic_template | public | WARNING | — |
| templates/membership.html:18 | Formulario | /pagos/checkout/{{ key }} | dynamic_template | public | WARNING | — |
| templates/membership.html:19 | Plan actual | /profile | profile_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/membership.html:20 | {{ 'Configuración pendiente' if not plan.get('configured') else 'Elegir ' ~ key }} | {{ '/membresias?plan=' ~ key if current_user else '/comprar/' ~ key }} | dynamic_template | public | WARNING | — |
| templates/onboarding.html:8 | Siguiente paso | {{ data.onboarding.next_step.href }} | dynamic_template | public | WARNING | — |
| templates/onboarding.html:8 | Mi cuenta | /mi-cuenta | account_center_page | public | OK | — |
| templates/onboarding.html:21 | {% if step.done %}OK{% else %}Pendiente{% endif %}         {{ step.label }}         {% if step.done %}Completado y listo para personalizar tu experiencia.{% else %}Pulsa aquí para  | {{ step.href }} | dynamic_template | public | WARNING | — |
| templates/partials/admin_visual_system.html:21 | ◢         NeMeSiS SHARK PRO | /admin/dashboard | v566_admin_dashboard_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| templates/partials/admin_visual_system.html:43 | {{ icon }} {{ label }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/partials/admin_visual_system.html:56 | Cerrar sesión | /logout | logout_page | public | OK | — |
| templates/partials/admin_visual_system.html:60 | ▣ Hoy | — | — | public | WARNING | — |
| templates/partials/brand_logo.html:2 | NeMeSiS       SHARK PRO | {{ href }} | dynamic_template | public | WARNING | — |
| templates/partials/client_flow_bar.html:3 | 01 Inicio Resumen real | /app | v757_client_app_center_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/partials/client_flow_bar.html:4 | 02 Partidos Calendario | /calendar?lane=today | calendar_page | public | OK | — |
| templates/partials/client_flow_bar.html:5 | 03 Directo Marcador | /live | live_page | public | OK | — |
| templates/partials/client_flow_bar.html:6 | 04 Picks Señales | /picks | picks_page | public | OK | — |
| templates/partials/client_flow_bar.html:7 | 05 Detalle Análisis | /calendar?lane=with_pick | calendar_page | public | OK | — |
| templates/partials/client_flow_bar.html:8 | 06 SHARK Consulta | /shark | shark_page | public | OK | — |
| templates/partials/ui_components.html:6 | {{ label }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/partials/ui_components.html:10 | {% else %} {% endif %}    {{ title }}     {{ value }}    {% if detail %} {{ detail }} {% endif %} {% if href %} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/partials/ui_components.html:21 | {{ primary_label }} | {{ primary_href }} | dynamic_template | public | WARNING | — |
| templates/partials/ui_components.html:43 | {{ action_label }} | {{ action_href }} | dynamic_template | public | WARNING | — |
| templates/partials/ui_components.html:51 | Ver partido | {{ href }} | dynamic_template | public | WARNING | — |
| templates/partials/ui_components.html:63 | Ver partido | {{ href }} | dynamic_template | public | WARNING | — |
| templates/partials/ui_components.html:64 | Abrir SHARK | {{ shark_href }} | dynamic_template | public | WARNING | — |
| templates/partials/ui_components.html:79 | {{ label }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/partials/ui_components.html:165 | {{ label }} | {{ href }} | dynamic_template | public | WARNING | — |
| templates/partials/v758_adaptive_strip.html:10 | Ajuste PC/Móvil | /experiencia | v758_adaptive_experience_page | public | OK | — |
| templates/partials/v758_adaptive_strip.html:13 | {{ k.label }} {{ k.value }} {{ k.hint }} | {{ k.href }} | dynamic_template | public | WARNING | — |
| templates/partials/v758_adaptive_strip.html:16 | {{ a.icon }} {{ a.label }} {{ a.badge }} | {{ a.href }} | dynamic_template | public | WARNING | — |
| templates/password_reset_form.html:9 | Solicitar otro enlace | {{ '/admin-forgot-password' if admin else '/forgot-password' }} | dynamic_template | public | WARNING | — |
| templates/password_reset_request.html:10 | abrir enlace de recuperación | {{ diagnostic_url }} | dynamic_template | public | WARNING | — |
| templates/password_reset_request.html:15 | Volver | {{ '/admin-login' if admin else '/cliente-login' }} | dynamic_template | public | WARNING | — |
| templates/pick_tracking.html:40 | Seguir | — | — | public | WARNING | — |
| templates/pick_tracking.html:63 | Quitar | — | — | public | WARNING | — |
| templates/picks.html:24 | Ver análisis completo | {{ featured.get('client_match_url') or ('/match/' ~ (featured.get('match_id') or featured.get('id'))) }} | dynamic_template | public | WARNING | — |
| templates/picks.html:24 | Explicar con SHARK | /shark?pick={{ featured.get('id') }} | dynamic_template | public | WARNING | — |
| templates/profile.html:29 | Cerrar sesión | /logout | logout_page | public | OK | — |
| templates/recommendations.html:7 | Picks publicados | /picks | picks_page | public | OK | — |
| templates/recommendations.html:7 | {{ data.membership.next_cta }} | /membresías | membership_page | public | OK | — |
| templates/recommendations.html:40 | Ver planes | /membresías | membership_page | public | OK | — |
| templates/register.html:11 | Formulario | /registro | register_page | public | OK | — |
| templates/register.html:27 | {{ 'Entrar y seguir' if selected in ['PRO','ELITE'] else 'Entrar' }} | /cliente-login{% if selected in ['PRO','ELITE'] %}?plan={{ selected }}&next={{ next_url\|urlencode }}{% endif %} | dynamic_template | public | WARNING | — |
| templates/register.html:28 | Ver planes y precios | /membresias | membership_page | public | OK | — |
| templates/resource_unavailable.html:14 | Volver a partidos | /calendar | calendar_page | public | OK | — |
| templates/resource_unavailable.html:15 | Ver calendario | /calendar | calendar_page | public | OK | — |
| templates/resource_unavailable.html:16 | Ver picks | /picks | picks_page | public | OK | — |
| templates/resource_unavailable.html:17 | Ir al inicio | / | home | public | OK | — |
| templates/responsible_betting.html:29 | Formulario | /api/responsible-betting/limits | — | public | RUTA_SIN_ACCESO_UI | Archivar o reactivar la plantilla antes de exponerla en navegacion. |
| templates/responsible_betting.html:52 | Formulario | /api/responsible-betting/ack | — | public | RUTA_SIN_ACCESO_UI | Archivar o reactivar la plantilla antes de exponerla en navegacion. |
| templates/responsible_betting.html:54 | Entrar para aceptar aviso | /cliente-login | client_login_page | public | OK | — |
| templates/shark.html:13 | Explorar partidos | /calendar | calendar_page | public | OK | — |
| templates/shark.html:13 | Directo | /live | live_page | public | OK | — |
| templates/shark.html:13 | Picks | /picks | picks_page | public | OK | — |
| templates/shark.html:21 | {{ action.get('label') }} | {{ action.get('url') }} | dynamic_template | public | WARNING | — |
| templates/shark_core.html:22 | Ver picks | /picks | picks_page | public | OK | — |
| templates/shark_core.html:26 | Ver auto picks | /auto-picks | v566_auto_picks_page | public | OK | — |
| templates/shark_core.html:35 | Ver recomendaciones | /recomendaciones | v566_recommendations_page | public | OK | — |
| templates/shark_core.html:46 | Mis favoritos | /favorites | favorites_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/shark_core.html:59 | {{ q.label }}  {{ q.question }} | /shark?q={{ q.question\|urlencode }} | dynamic_template | public | WARNING | — |
| templates/smart_dashboard.html:11 | {{ action.icon }}  {{ action.label }} | {{ action.href }} | dynamic_template | public | WARNING | — |
| templates/smart_dashboard.html:23 | Briefing completo | /mi-dia | daily_briefing_page | public | OK | — |
| templates/smart_dashboard.html:26 | {{ item.value }}         {{ item.title }}         {{ item.text }} | {{ item.href }} | dynamic_template | public | WARNING | — |
| templates/smart_dashboard.html:39 | Preguntar a SHARK | /shark | shark_page | public | OK | — |
| templates/smart_dashboard.html:39 | Ver recomendaciones | /recomendaciones | v566_recommendations_page | public | OK | — |
| templates/smart_dashboard.html:42 | Calendario | /match-hub | match_hub_page | public | OK | — |
| templates/smart_dashboard.html:47 | {{ m.safe_home or m.home_team }} vs {{ m.safe_away or m.away_team }} {{ (m.safe_competition or m.competition_name or m.league_name or 'Competición')\|competition_es }} {{ m\|match_ti | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/smart_dashboard.html:57 | Abrir picks | /picks | picks_page | public | OK | — |
| templates/smart_dashboard.html:60 | {{ p.home_team }} vs {{ p.away_team }} {{ p.selection_display or p.selection or p.market or 'Pick publicado' }} {{ p.odds or '—' }} | /picks | picks_page | public | OK | — |
| templates/smart_dashboard.html:67 | Gestionar | /favorites | favorites_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/smart_dashboard.html:70 | {{ f.label or f.value }} {{ f.kind }} ⭐ | /favorites | favorites_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/sports_hub.html:6 | Calendario | /calendar?lane=today | calendar_page | public | OK | — |
| templates/sports_hub.html:6 | Directo | /live | live_page | public | OK | — |
| templates/sports_hub.html:6 | Picks | /picks | picks_page | public | OK | — |
| templates/sports_hub.html:6 | {{ (hub.get('favorites') or [])\|length }} Favoritos | — | — | public | RUTA_INTERNA_NO_DEBE_SER_VISIBLE | — |
| templates/sports_hub.html:8 | {{ tab.label }} | {{ tab.href }} | dynamic_template | public | WARNING | — |
| templates/sports_hub.html:9 | {{ ctx.client_date_label }} {{ live.get('minute') if live.get('badge') == 'live' else ctx.client_time_label }} {% set home_identity = m\|team_identity('home') %}{% set away_identity | /match/{{ m.get('id') }} | dynamic_template | public | WARNING | — |
| templates/sports_hub.html:9 | Calendario | /calendar | calendar_page | public | OK | — |
| templates/sports_hub.html:9 | Picks | /picks | picks_page | public | OK | — |
| templates/sports_intelligence.html:7 | Ver recomendaciones | /recomendaciones | v566_recommendations_page | public | OK | — |
| templates/sports_intelligence.html:7 | Picks publicados | /picks | picks_page | public | OK | — |
| templates/support.html:10 | Volver a Mi día | /mi-dia | daily_briefing_page | public | OK | — |
| templates/support.html:11 | Preguntar a SHARK | /shark | shark_page | public | OK | — |
| templates/team_detail.html:13 | Formulario | /favorites | favorites_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/team_detail.html:20 | Calendario | /match-hub | match_hub_page | public | OK | — |
| templates/team_detail.html:21 | Preguntar a SHARK | /shark?team={{ t.name\|urlencode }} | dynamic_template | public | WARNING | — |
| templates/team_detail.html:48 | Abrir SHARK IA | /shark?team={{ t.name\|urlencode }} | dynamic_template | public | WARNING | — |
| templates/team_detail.html:66 | {{ (m.safe_competition or m.competition_name or m.league_name)\|competition_es }} {{ m\|match_time_label }} {{ m.live_depth.minute }}         {{ crest(m\|team_identity('home'), m.safe | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/team_detail.html:80 | {{ m.safe_home or m.home_team }} vs {{ m.safe_away or m.away_team }} {{ m.live_depth.score or m.score or 'FT' }} | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/team_detail.html:86 | {{ p.selection_display or p.selection }} {{ p.odds or '-' }} | /picks | picks_page | public | OK | — |
| templates/telegram.html:19 | Formulario | /telegram/desvincular | telegram_unlink_private | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/telegram.html:20 | Conectar Telegram | {{ state.get('deep_link') }} | dynamic_template | public | WARNING | — |
| templates/telegram.html:20 | Formulario | /telegram/regenerar-codigo | telegram_regenerate_code | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/unified_intelligence_hub.html:9 | Ver recomendaciones | /recomendaciones | v566_recommendations_page | public | OK | — |
| templates/unified_intelligence_hub.html:10 | Picks | /picks | picks_page | public | OK | — |
| templates/unified_intelligence_hub.html:11 | Directo | /live | live_page | public | OK | — |
| templates/unified_intelligence_hub.html:12 | Preguntar a SHARK | /shark | shark_page | public | OK | — |
| templates/unified_intelligence_hub.html:26 | {{ lane.key\|upper }}         {{ lane.title }}         {{ lane.value }}         {{ lane.body }} | {{ lane.href }} | dynamic_template | public | WARNING | — |
| templates/unified_intelligence_hub.html:38 | Calendario | /match-hub | match_hub_page | public | OK | — |
| templates/unified_intelligence_hub.html:41 | {{ m.safe_home or m.home_team }} vs {{ m.safe_away or m.away_team }} {{ m.league_name or m.competition_name or 'Competición' }} {{ m\|match_time_short }} | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/unified_intelligence_hub.html:46 | Picks | /picks | picks_page | public | OK | — |
| templates/unified_intelligence_hub.html:49 | {{ p.selection_display or p.selection or p.title or 'Pick publicado' }} {{ p.home_team }} {{ p.away_team and 'vs ' ~ p.away_team }} {{ p.confidence or p.score or 70 }}% | /picks | picks_page | public | OK | — |
| templates/unified_intelligence_hub.html:58 | Favoritos {{ hub.favorites }} | /favorites | favorites_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/unified_intelligence_hub.html:59 | Resultados {{ hub.results_total }} | /resultados | match_hub_page | public | OK | — |
| templates/unified_intelligence_hub.html:60 | Combis Builder | /combis | combis_page | public | OK | — |
| templates/unified_intelligence_hub.html:61 | Telegram {{ hub.telegram_pending }} | /telegram | telegram_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| templates/unified_intelligence_hub.html:62 | Seguimiento ROI | /seguimiento | public_track_record_page | public | OK | — |
| templates/unified_intelligence_hub.html:63 | Más Ordenado | /menu | v566_client_menu_page | public | OK | — |
| templates/world_cup_launch.html:10 | Hoy | /calendar?lane=today | calendar_page | public | OK | — |
| templates/world_cup_launch.html:11 | Directo | /live?f=live | live_page | public | OK | — |
| templates/world_cup_launch.html:12 | Picks | /picks | picks_page | public | OK | — |
| templates/world_cup_launch.html:13 | Histórico | /track-record | public_track_record_page | public | OK | — |
| templates/world_cup_launch.html:27 | Modo automático | /modo-dinamico | v764_dynamic_mode_page | public | OK | — |
| templates/world_cup_launch.html:32 | {{ (dm.primary_action or {}).get('label','Ver calendario') }} | {{ (dm.primary_action or {}).get('href','/calendar') }} | dynamic_template | public | WARNING | — |
| templates/world_cup_launch.html:41 | {{ m.client_date_label or (m\|match_date_label) }} {{ m.client_time_label or (m\|match_time_short) }}         {{ m.v763_title }} {{ m.v763_competition }} · {{ m.v763_status }}        | /match/{{ m.id }} | dynamic_template | public | WARNING | — |
| templates/world_cup_launch.html:53 | Ver picks | /picks | picks_page | public | OK | — |
| templates/world_cup_launch.html:56 | {{ p.client_match_label or 'Partido pendiente' }} {{ p.client_competition or 'Competición' }} · {{ p.client_full_datetime_label or (p\|match_full_datetime) }}         {{ p.client_se | {{ p.client_match_url or ('/match/' ~ (p.match_id or p.id)) }} | dynamic_template | public | WARNING | — |
| app.py:11851 | redirect | /admin-login?next=/admin/highlights-center | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:12610 | redirect | /cliente-login | client_login_page | public | OK | — |
| app.py:12617 | redirect | /favorites | favorites_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| app.py:12757 | redirect | /membresias? | membership_page | public | OK | — |
| app.py:12763 | redirect | /app | v757_client_app_center_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| app.py:12775 | redirect | /app | v757_client_app_center_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| app.py:12790 | redirect | /admin/users | admin_users_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:12792 | redirect | /app | v757_client_app_center_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| app.py:12793 | redirect | /cliente-login | client_login_page | public | OK | — |
| app.py:12802 | redirect | /app | v757_client_app_center_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| app.py:12810 | redirect | /app | v757_client_app_center_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| app.py:12840 | redirect | /cliente-login | client_login_page | public | OK | — |
| app.py:12886 | redirect | /admin-login | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:12922 | redirect | / | home | public | OK | — |
| app.py:12928 | redirect | /admin-login?next=/admin/data-center | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:12929 | redirect | /admin/control-center | v566_admin_dashboard_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:12935 | redirect | /admin-login?next=/admin/intelligence | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:12936 | redirect | /admin/unified-intelligence | v566_admin_unified_intelligence_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:12942 | redirect | /admin-login?next=/admin/observability | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:12949 | redirect | /admin-login?next=/admin/observability/errors | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:12964 | redirect | /admin-login?next=/admin/import-center | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:12971 | redirect | /admin-login?next=/admin/users | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:12997 | redirect | /admin-login?next=/admin/user-import | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13009 | redirect | /admin-login?next=/admin/sportsdb-sync | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13027 | redirect | /admin-login?next=/admin/sportsdb-feed | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13044 | redirect | /admin-login?next=/admin/matches-sync | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13068 | redirect | /admin-login?next=/admin/telegram | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13153 | redirect | /admin-login?next=/admin/telegram/command-center | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13571 | redirect | /admin-login?next=/admin/automation | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13586 | redirect | /admin-login?next=/admin/backups | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13615 | redirect | /admin-login?next=/admin/backups | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13625 | redirect | /admin-login?next=/admin/picks | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13657 | redirect | /admin-login?next=/admin/data-center | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13690 | redirect | /admin-login?next=/admin/api-sports | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13717 | redirect | /admin-login?next=/admin/company-os | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13736 | redirect | /admin-login?next=/admin/company-audit | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13755 | redirect | /admin-login?next=/admin/auto-improvement | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13777 | redirect | /admin-login?next=/admin/continuous-sentinel | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13787 | redirect | /admin-login?next=/admin/sentinel-workflow | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13800 | redirect | /admin-login?next=/admin/visual-worker | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13914 | redirect | /admin-login?next=/admin/autonomous-company-sentinel | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13925 | redirect | /admin-login?next=/admin/sentinel-codex-outbox | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:13990 | redirect | /admin-login?next=/admin/automation-workforce | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:14204 | redirect | /admin-login?next=/admin/sentinel-issues | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:14315 | redirect | /admin-login?next=/admin/sentinel-autopilot | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:14588 | redirect | /admin-login?next=/admin/system | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:14665 | redirect | /admin-login?next= | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:14749 | redirect | /admin-login?next=/admin/client-experience | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:14772 | redirect | /admin-login?next=/admin/production-readiness | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:14833 | redirect | /cliente-login | client_login_page | public | OK | — |
| app.py:14848 | redirect | /cliente-login | client_login_page | public | OK | — |
| app.py:14857 | redirect | /cliente-login | client_login_page | public | OK | — |
| app.py:14867 | redirect | /cliente-login | client_login_page | public | OK | — |
| app.py:14882 | redirect | /membresias | membership_page | public | OK | — |
| app.py:14932 | redirect | /cliente-login?next=/telegram | client_login_page | public | OK | — |
| app.py:14947 | redirect | /cliente-login?next=/telegram | client_login_page | public | OK | — |
| app.py:14953 | redirect | /telegram | telegram_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| app.py:14960 | redirect | /cliente-login?next=/telegram | client_login_page | public | OK | — |
| app.py:14967 | redirect | /telegram | telegram_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| app.py:15008 | redirect | /admin-login?next=/admin/telegram/diagnostics | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:15015 | redirect | /admin-login?next=/admin/time-diagnostics | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:15084 | redirect | /perfil | profile_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| app.py:17502 | redirect | /admin-login?next=/admin/data-memory | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:17511 | redirect | /admin-login?next=/admin/codex-automation | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:17546 | redirect | /admin-login?next=/admin/team-identity | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:18206 | redirect | /admin-login?next=/admin/not-found-events | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:18505 | redirect | /cliente-login | client_login_page | public | OK | — |
| app.py:18515 | redirect | /cliente-login | client_login_page | public | OK | — |
| app.py:18534 | redirect | /admin-login?next=/admin/memberships | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:18612 | redirect | /admin-login?next=/admin/client-success | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:18638 | redirect | /admin-login?next=/admin/go-live | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:18670 | redirect | /admin-login?next=/admin/public-launch | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:18767 | redirect | /admin-login?next=/admin/track-record | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:18824 | redirect | /admin-login?next=/admin/final-certification | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:18846 | redirect | /admin-login?next=/admin/payments | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:18932 | redirect | /cliente-login?next=/mi-cuenta | client_login_page | public | OK | — |
| app.py:18936 | redirect | /mi-cuenta?billing=portal_unavailable | account_center_page | public | OK | — |
| app.py:18945 | redirect | /cliente-login?next= | client_login_page | public | OK | — |
| app.py:18955 | redirect | /membresias? | membership_page | public | OK | — |
| app.py:18960 | redirect | /membresias?pago=cancelado | membership_page | public | OK | — |
| app.py:19176 | redirect | /admin-login?next=/admin/sports-data-picks | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:19452 | redirect | /app | v757_client_app_center_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| app.py:19467 | redirect | /cliente-login | client_login_page | public | OK | — |
| app.py:19481 | redirect | /admin-login?next=/admin/live-depth | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:19482 | redirect | /admin/live-qa | admin_live_experience_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:19580 | redirect | /admin-login?next=/admin/legal-compliance | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:19599 | redirect | /admin-login?next=/admin/real-launch | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:19619 | redirect | /admin-login?next=/admin/client-screen-audit | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:19742 | redirect | /admin-login?next=/admin/control-center | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:19802 | redirect | /admin-login?next=/admin/recommendations | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:19816 | redirect | /admin-login?next=/admin/final-qa | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:19845 | redirect | /admin-login?next=/admin/unified-intelligence | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20008 | redirect | /cliente-login?next=/shark-core | client_login_page | public | OK | — |
| app.py:20023 | redirect | /admin-login?next=/admin/shark-ai | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20066 | redirect | /admin-login?next=/admin/visual-experience | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20090 | redirect | /admin-login?next=/admin/app-feel | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20117 | redirect | /admin-login?next=/admin/client-visual-qa | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20139 | redirect | /admin-login?next=/admin/calendar-experience | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20166 | redirect | /admin-login?next=/admin/final-release | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20236 | redirect | /admin-login?next=/admin/live-experience | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20292 | redirect | /admin-login?next=/admin/sale-ready | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20332 | redirect | /admin-login?next=/admin/content-rights | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20471 | redirect | /admin-login?next=/admin/data-vault | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20537 | redirect | /admin-login?next=/admin/match-intelligence | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20555 | redirect | /admin-login?next=/admin/video-highlights | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20572 | redirect | /admin-login?next=/admin/alerts | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20589 | redirect | /admin-login?next=/admin/top-app-readiness | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20613 | redirect | /cliente-login?next=/app | client_login_page | public | OK | — |
| app.py:20663 | redirect | /cliente-login?next=/experiencia | client_login_page | public | OK | — |
| app.py:20745 | redirect | /admin-login?next=/admin/app-experience-quality | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:20803 | redirect | /admin-login?next=/admin/client-screen-quality | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21008 | redirect | /admin-login?next=/admin/client-product-quality | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21143 | redirect | /admin-login?next=/admin/client-organization-quality | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21152 | redirect | /admin-login?next=/admin/data-marketplace | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21191 | redirect | /admin-login?next=/admin/automation-center | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21307 | redirect | /admin-login?next=/admin/map | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21314 | redirect | /admin-login?next=/admin/support-center | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21323 | redirect | /admin-login?next=/admin/pick-performance | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21330 | redirect | /admin-login?next=/admin/betting-center | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21337 | redirect | /admin-login?next=/admin/intelligence-engine | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21421 | redirect | /cliente-login?next=/app/mapa | client_login_page | public | OK | — |
| app.py:21430 | redirect | /forgot-password | forgot_password_page | public | OK | — |
| app.py:21435 | redirect | /cliente-login?next=/notificaciones | client_login_page | public | OK | — |
| app.py:21436 | redirect | /telegram | telegram_page | client | REQUIERE_SESIÓN_CLIENTE | — |
| app.py:21441 | redirect | /admin-login?next=/admin/autonomous-picks | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21456 | redirect | /admin-login?next=/admin/autopilot-audit | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21462 | redirect | /admin-login?next=/admin/telegram-audit | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21470 | redirect | /admin-login?next=/admin/intelligence-center | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21485 | redirect | /admin-login?next=/admin/launch-center | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21508 | redirect | /admin-login?next=/admin/retention-center | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21516 | redirect | /admin-login?next=/admin/beta-center | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21565 | redirect | /admin-login?next=/admin/telegram/pro-preview | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:21830 | redirect | /admin-login?next=/admin/daily-automation | admin_login_page | admin | REQUIERE_SESIÓN_ADMIN | — |
| app.py:11886 | static | url_for('static') | static | public | OK | — |
| app.py:18405 | admin_login_page | url_for('admin_login_page') | admin_login_page | public | OK | — |
