# Codex Outbox - V913 Browser QA Truth

pixel_perfect_claim: false
generated_at_madrid: 2026-07-08T12:40:04+02:00
browser_qa_status: PACKAGE_MISSING
screenshots_captured: 0
visual_queue_total: 18
visual_queue_blocked: 18
visual_queue_ready: 0

## V913_BROWSER_QA_EXECUTION_REQUIRED
- Ejecutar Browser QA real o importar resultados antes de cerrar gaps visuales.
- Comando local: `.\.venv\Scripts\python.exe tools\run_browser_reference_qa.py --base-url https://bot-apuestas-crgf.onrender.com --output reports/browser_qa_render --mobile --desktop --write-json`
- Importar resultados: `.\.venv\Scripts\python.exe tools\import_browser_qa_results.py --input reports/browser_qa_render --update-runtime-data`

## V913_READY_FOR_CODEX_WITH_SCREENSHOTS
- Sin prompts visuales accionables porque no hay screenshots reales.

## V913_BLOCKED_NO_SCREENSHOT
- `/` `desktop` -> Captura real pendiente.
- `/admin-login` `desktop` -> Captura real pendiente.
- `/admin/autonomous-company-sentinel` `desktop` -> Captura real pendiente.
- `/admin/dashboard` `desktop` -> Captura real pendiente.
- `/admin/not-found-events` `desktop` -> Captura real pendiente.
- `/admin/sentinel-codex-outbox` `desktop` -> Captura real pendiente.
- `/admin/sentinel-issues` `desktop` -> Captura real pendiente.
- `/admin/telegram/command-center` `desktop` -> Captura real pendiente.
- `/app` `desktop` -> Captura real pendiente.
- `/calendar` `desktop` -> Captura real pendiente.
- `/cliente-login` `desktop` -> Captura real pendiente.
- `/live` `desktop` -> Captura real pendiente.
- `/picks` `desktop` -> Captura real pendiente.
- `/profile` `desktop` -> Captura real pendiente.
- `/registro` `desktop` -> Captura real pendiente.
- `/shark` `desktop` -> Captura real pendiente.
- `/support` `desktop` -> Captura real pendiente.
- `/telegram` `desktop` -> Captura real pendiente.

## V913_RUNTIME_STATUS_FIXES
- Runtime V913 expone estado real de Browser QA, cola visual y siguiente accion.
- Estados V910 historicos se mantienen como auditoria; V913 publica resumen propio veraz.

## V913_SAFE_FIXES_APPLIED
- Cola visual normalizada a estados permitidos.
- Outbox evita prompts visuales falsos sin captura.
- Importador seguro creado para resultados externos.

## V913_DANGEROUS_REQUIRES_APPROVAL
- Sin acciones peligrosas ejecutadas.
- No tocar pagos, DB, usuarios, Telegram real, secretos ni deploy sin aprobacion.

## ARCHIVED_OBSOLETE_PROMPTS
- Prompts visuales sin screenshot quedan archivados como no accionables hasta Browser QA real.
