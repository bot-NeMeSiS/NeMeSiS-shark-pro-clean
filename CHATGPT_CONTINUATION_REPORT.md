@"
# CHATGPT CONTINUATION REPORT - V844

## Estado base
La carpeta oficial estaba en V843, con producto comercial revisado, rutas corregidas y ZIP limpio.

## Qué cambia V844
V844 se centra en Telegram: calidad de candidatos, no-filler, bloqueo de ligas raras/deportes no permitidos y diagnóstico admin.

## Filtro creado
engines/telegram_quality_filter_engine.py permite fútbol top, bloquea NBA/otros deportes/youth/reserves/regional/amateur/friendly débil y penaliza segundas extranjeras o competiciones desconocidas.

## Telegram
No se envían mensajes reales en local. El canal público queda más conservador: si no hay contenido top, no se manda relleno.

## Pendiente real
Probar en Render con datos reales y TELEGRAM_CHAT_ID real para confirmar qué candidatos aparecen bloqueados y cuáles salen al canal.
## V845_SHARK_AI_INTELLIGENCE_PRODUCT_ASSISTANT_FINAL

Base real usada: `V844_TELEGRAM_TOP_PICK_QUALITY_CARDS_FILTER_FINAL`.

Objetivo de V845: convertir SHARK en un asistente de producto real, responsable y conectado con partidos, picks, Telegram V844, perfil y soporte.

Cambios principales:
- Se añadió `engines/shark_ai_product_assistant_engine.py`, motor local defensivo que no llama APIs externas por sí mismo.
- `/api/shark/ask` usa contexto real de usuario, membresía, partido, pick y filtro Telegram V844.
- `/shark` se reconstruyó como pantalla de asistente premium con respuesta, estado de datos, preguntas rápidas y acciones.
- `/picks` y `/match/` enlazan con textos claros: `Explicar pick con SHARK` y `Analizar con SHARK`.
- Se añadió `/admin/shark-ai` como entrada admin al centro SHARK con estado OpenAI/fallback y reglas anti-invención.
- `/api/runtime-version` expone V845 y `openai_configured` como booleano, sin secretos.

Política de seguridad:
- No inventa picks, cuotas, resultados, minutos, eventos, posesión, estadísticas ni ROI.
- Si falta información, muestra `Cuotas pendientes`, `Resultado pendiente`, `Sin pick real publicado` o recomienda esperar.
- Nunca usa lenguaje de garantía como `apuesta segura`, `garantizado` o `sin riesgo`.
- Si falta `OPENAI_API_KEY`, funciona en modo análisis interno.

Pendiente real:
- Probar visualmente en navegador real si se quiere declarar una revisión pixel-perfect.
- Con datos reales abundantes en producción, se puede ajustar el tono y longitud de las respuestas.
# V847_COMPANY_BRAIN_API_SPORTS_DATA_PROVIDER_AND_PRODUCT_QA_FINAL

Base real usada: V845_SHARK_AI_INTELLIGENCE_PRODUCT_ASSISTANT_FINAL desde la carpeta oficial. No se usó ZIP viejo como base.

Qué se hizo:

- Se auditó el uso real de API-SPORTS/API-Football en código, live, match detail, cron y engines.
- Se añadió `engines/api_sports_provider_engine.py` como fachada segura con cache, dry-run y guard anti-gasto.
- Se añadió `/admin/api-sports` y `/api/admin/api-sports/status` sin exponer secretos.
- `/api/runtime-version` ahora muestra `api_football_configured`, `api_sports_configured`, `the_odds_configured`, `provider_active`, `last_sync`, `last_error` y `usage_guard`.
- SHARK V845 recibe contexto seguro del proveedor.
- Telegram V844 queda intacto y sigue filtrando candidatos top.
- Queda documentado el backlog visual V848 para fondo SHARK/puntitos y pantallas de referencia.

Validaciones: ver `reports/V847_PRODUCTION_STABILITY_QA.md` y `RELEASE_MANIFEST_V847.json`.
# V848_REFERENCE_SHARK_VISUAL_PC_MOBILE_FINAL

Base real usada: V847_COMPANY_BRAIN_API_SPORTS_DATA_PROVIDER_AND_PRODUCT_QA_FINAL.

No se usó ZIP viejo como base.

# V851_LOGO_BRAND_HEADER_MOBILE_PC_FIX

Base real usada: `V850_LIVE_CRESTS_API_SPORTS_MATCH_DETAIL_FINAL`.

No se usó ZIP viejo como base.

Objetivo de V851: corregir la marca superior detectada en captura móvil y dejar el logo NeMeSiS SHARK PRO coherente en móvil, PC y admin.

Cambios principales:
- Se creó `templates/partials/brand_logo.html` con el componente reutilizable `nemesis_brand`.
- `templates/base.html` usa la misma marca en topbar, rail cliente y rail admin.
- Se añadió el bloque CSS `V851 LOGO BRAND HEADER MOBILE PC FIX` para proporciones, alineación, responsive y no deformación.
- Se corrigió `EspaÁa/Madrid` a `Hora España/Madrid`.
- `/api/runtime-version` expone `has_v851_logo_brand_header_fix`.

Preservado:
- V850 live/escudos.
- V847 API-SPORTS guard.
- V845 SHARK AI.
- V844 Telegram.
- V818 master tick.

# V852_REAL_VIDEO_PRODUCT_PERFECTION_LIVE_PICKS_VISUAL_QA_FINAL

Base real usada: `V851_LOGO_BRAND_HEADER_MOBILE_PC_FIX`.

No se usó ZIP viejo como base.

Objetivo de V852: corregir puntos detectados en vídeo real: copy visible, picks raros o caducados, live con proveedor activo pero 0 directos, y pulido visual PC/móvil sin romper V851/V850/V847/V845/V844/V818.

Cambios principales:
- `engines/picks_quality_engine.py` degrada competiciones de baja relevancia y picks pasados.
- `/picks` ordena por calidad, prioriza picks premium listos y marca como `Pick en revisión`, `Archivado` o `Liga baja relevancia` lo que no debe ocupar protagonismo.
- `/live` muestra un diagnóstico premium cuando API-Football está activo pero no devuelve directos: `Sin directos reales ahora mismo`.
- Se añadió CSS V852 para fondo/cards, picks en revisión, diagnóstico live y filtros móviles.
- Se validó que no quedan textos objetivo rotos como `lo primo`, `Result ados` o `EspaÁa/Madrid`.

Preservado:
- V851 logo/header.
- V850 live/escudos.
- V847 API-SPORTS guard.
- V845 SHARK AI.
- V844 Telegram.
- V818 master tick.

Qué se hizo:

- Se reforzó el fondo SHARK con patrón de puntitos, halo, glow y textura oscura premium.
- Se mejoró la profundidad visual de topbar, sidebar/rail, bottom nav, cards, botones, empty states y panel API-SPORTS.
- Se mantuvo móvil con safe-area, bottom nav centrada y floating SHARK por encima de la navegación.
- Se mantuvo admin sobrio, sin bottom nav cliente ni floating SHARK.
- Se preservó API-SPORTS V847, Telegram V844, SHARK V845 y master tick V818.
- Se añadieron checks V848 de runtime, visual, mobile, desktop, SHARK, admin, rutas y regresiones.

ZIP final esperado:
NeMeSiS_SHARK_PRO_V848_REFERENCE_SHARK_VISUAL_PC_MOBILE_FINAL_RENDER_READY.zip
# V849_FULL_COMPANY_VISUAL_PRODUCT_EXPERIENCE_ADVANCEMENT

Base real usada: V848_REFERENCE_SHARK_VISUAL_PC_MOBILE_FINAL.

No se usó ZIP viejo como base.

Qué se hizo:

- Avance visual controlado sobre V848: más densidad en cards, botones, chips, inputs y tablas.
- Móvil preserva bottom nav, safe-area y floating SHARK.
- PC preserva rail/dashboard y mejora command center.
- SHARK V845, Telegram V844 y API-SPORTS V847 quedan preservados por checks de regresión.
- Se añadieron checks V849 y reportes de producto/visual/rutas/regresiones.

ZIP final esperado:
NeMeSiS_SHARK_PRO_V849_FULL_COMPANY_VISUAL_PRODUCT_EXPERIENCE_ADVANCEMENT_RENDER_READY.zip
# V850 LIVE CRESTS API SPORTS MATCH DETAIL FINAL

Fecha: 2026-06-26

Base real usada: `V849_FULL_COMPANY_VISUAL_PRODUCT_EXPERIENCE_ADVANCEMENT`.

Nueva version: `V850_LIVE_CRESTS_API_SPORTS_MATCH_DETAIL_FINAL`.

Resumen:

- Se reforzo live/directo con payload seguro de marcador, minuto y estado.
- Se agrego `engines/live_match_experience_engine.py` con helpers cache-first y dry-run.
- Se agrego `engines/crest_logo_experience_engine.py` para escudos/logos/fallbacks sin descargas en render.
- Se mejoraron `/live`, `/directo`, `/calendar`, `/match/` y admin API-SPORTS.
- Se preservan V818, V844, V845, V847, V848 y V849.
- No se tocaron DB_PATH, usuarios, sesiones, membresias, pagos ni secretos.

Pendiente del cierre de turno: validaciones completas y ZIP Render Ready V850.
## V853_ADMIN_PC_COMMAND_CENTER_REFERENCE_PERFECTION_FINAL

Base real detectada: V852_REAL_VIDEO_PRODUCT_PERFECTION_LIVE_PICKS_VISUAL_QA_FINAL.

Trabajo aplicado:
- Se elevó VERSION.txt, APP_VERSION, base.html y runtime a V853.
- Se añadió banda admin `v853-admin-command-strip` con accesos a Dashboard, Datos, API-SPORTS, Telegram, SHARK AI, Master tick, Usuarios, Membresías, Pagos y Runtime.
- Se añadió CSS V853 para rail admin, headers, cards, tablas y ocultación de bottom nav/floating SHARK cliente dentro de admin.
- Se corrigieron textos visibles rotos en admin: `diagnsticos`, `Segn Render` y separadores Madrid/producción.
- Se añadieron checks V853 y reportes V853.

Preservado:
- V818 master tick.
- V844 Telegram.
- V845 SHARK AI.
- V847 API-SPORTS provider guard.
- V850 live/escudos.
- V851 branding.
- V852 live/picks/visual QA.
## V854_CLIENT_ADMIN_REAL_RENDER_FINAL_POLISH_AND_PRODUCT_QA

Base real detectada: V853_ADMIN_PC_COMMAND_CENTER_REFERENCE_PERFECTION_FINAL.

Trabajo aplicado:
- Se elevó VERSION.txt, APP_VERSION, base.html, cache CSS y runtime a V854.
- Se añadió capa CSS V854 acotada para cliente/admin: cards, estados vacíos, safe-area móvil, logos/escudos y separación admin/cliente.
- Se añadieron checks V854 para cliente, admin, live/API-SPORTS, picks, logos/escudos, SHARK, Telegram, visual PC/móvil, textos, rutas, regresión y release cleanliness.
- Se añadieron reportes V854 y manifest V854.

Preservado:
- V818 master tick.
- V844 Telegram.
- V845 SHARK AI.
- V847 API-SPORTS provider guard.
- V850 live/escudos.
- V851 logo/header.
- V852 live/picks/video polish.
- V853 admin command center.
## V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL

Base real detectada: V854_CLIENT_ADMIN_REAL_RENDER_FINAL_POLISH_AND_PRODUCT_QA.

Trabajo aplicado:
- Se elevó VERSION.txt, APP_VERSION, base.html, cache CSS y runtime a V855.
- Se creó `engines/membership_experience_engine.py` como motor de presentación para FREE, PRO, ELITE, ELITE+ y ADMIN.
- Se añadió capa CSS V855 para coordinar cliente, admin, móvil, PC, cards, filtros, estados vacíos, logos y separación admin/cliente.
- Se creó `tools/check_v855_full_ecosystem_reference_rebuild.py`.
- Se añadieron reportes V855 de preflight, gap audit, membresías, admin command center, rutas, cliente y estabilidad.

Preservado:
- V818 master tick.
- V844 Telegram.
- V845 SHARK.
- V847 API-SPORTS.
- V850 live/escudos.
- V853 admin command center.
- V854 polish global.

## V856_REAL_APP_REFERENCE_GAP_SECOND_PASS_TOTAL_REBUILD_FINAL

Base real detectada: V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL.

Trabajo aplicado:
- Se elevó VERSION.txt, APP_VERSION, base.html, cache CSS y runtime a V856.
- Se añadió capa CSS V856 de segunda pasada para cliente, móvil, PC, admin, SHARK, Telegram, picks, live, empty states y membresías.
- Se crearon motores de presentación puros para cliente, admin, match, live, picks, Telegram y SHARK.
- Se creó `tools/check_v856_real_app_reference_gap_second_pass.py`.
- Se añadieron reportes V856 de preflight, gap audit, admin, membresías, rutas, copy y estabilidad.

Preservado:
- V818 master tick.
- V844 Telegram.
- V845 SHARK.
- V847 API-SPORTS.
- V850 live/escudos.
- V853 admin command center.
- V854 polish global.
- V855 full ecosystem rebuild.

## V857_COMPANY_OPERATING_SYSTEM_PRODUCT_PERFECTION_FINAL

Base real detectada: V856_REAL_APP_REFERENCE_GAP_SECOND_PASS_TOTAL_REBUILD_FINAL.

Trabajo aplicado:
- Se elevó VERSION.txt, APP_VERSION, base.html, cache CSS y runtime a V857.
- Se creó `engines/company_operating_system_engine.py` como motor central de workers internos.
- Se añadió `/admin/company-os` con alias `/admin/empresa` y `/admin/operating-system`.
- Se añadió `/api/admin/company-os/summary` protegido por sesión admin.
- Se creó `templates/admin_company_os.html`.
- Se integró acceso a Empresa OS desde navegación admin, rail, dock y command strip.
- Se añadió capa CSS V857 para el panel Company OS.
- Se creó `tools/check_v857_company_operating_system_product_perfection.py`.
- Se añadieron reportes V857 de preflight, matriz de workers, QA, datos reales, rutas y notas Render.

Preservado:
- V818 master tick.
- V844 Telegram premium/no filler.
- V845 SHARK.
- V847 API-SPORTS.
- V850 live/escudos.
- V853 admin command center.
- V854/V855/V856.

## V858_VISUAL_DIRECTION_LOCK_FULL_APP_REFERENCE_FINAL

Base real detectada: V857_COMPANY_OPERATING_SYSTEM_PRODUCT_PERFECTION_FINAL.

Trabajo aplicado:
- Se elevó VERSION.txt, APP_VERSION, base.html, cache CSS y runtime a V858.
- Se añadió `data-v858-shell` y runtime flag `has_v858_visual_direction_lock`.
- Se creó una capa visual V858 para bloquear dirección final: tokens globales, fondo oscuro premium, puntos SHARK, glow, cards, botones, chips, tablas, forms, empty states, móvil, PC, admin y Company OS.
- Se reforzó la separación admin/cliente: sin bottom nav, floating SHARK ni scroll-to-top cliente en admin.
- Se marcó Company OS con `v858-visual-lock`.
- Se creó `tools/check_v858_visual_direction_lock.py`.
- Se añadieron reportes V858 de preflight, auditoría visual, visual lock, móvil, PC, admin, membresías, picks/live/SHARK/Telegram y notas Render.

Preservado:
- V818 master tick.
- V844 Telegram premium/no filler.
- V845 SHARK.
- V847 API-SPORTS.
- V850 live/escudos.
- V853 admin command center.
- V857 Company OS.

## V859_COMPANY_WIDE_ECOSYSTEM_AUDIT_AND_PRODUCT_BOARD_FINAL

Base real detectada: V858_VISUAL_DIRECTION_LOCK_FULL_APP_REFERENCE_FINAL.

Trabajo aplicado:
- Se elevó VERSION.txt, APP_VERSION, base.html, cache CSS y runtime a V859.
- Se creó `engines/company_audit_board_engine.py` como motor de auditoría global por boards.
- Se añadió `/admin/company-audit` con alias `/admin/auditoria-empresa` y `/admin/product-board`.
- Se añadió `/api/admin/company-audit/summary`, protegido por sesión admin.
- Se creó `templates/admin_company_audit.html`.
- Se integró Product Board en navegación admin y desde Company OS.
- Se añadió capa CSS V859 específica para el board de auditoría.
- Se creó `tools/check_v859_company_wide_audit_board.py`.
- Se añadieron reportes V859 y roadmap de prioridades.

Preservado:
- V818 master tick.
- V844 Telegram premium/no filler.
- V845 SHARK.
- V847 API-SPORTS.
- V850 live/escudos.
- V857 Company OS.
- V858 visual direction lock.

## V861_SELF_IMPROVING_OPERATIONS_OS_SAFE_AUTOMATION_FINAL

Base real detectada: V860_PROJECT_CLEANUP_LEGACY_PURGE_VISUAL_REFERENCE_ALIGNMENT_FINAL.

Trabajo aplicado:
- Se elevó VERSION.txt, APP_VERSION, base.html, cache CSS y runtime a V861.
- Se creó `engines/auto_improvement_engine.py` como motor seguro de mejora continua.
- Se añadió `/admin/auto-improvement` con alias `/admin/mejora-continua`, `/admin/shark-ops` y `/admin/continuous-improvement`.
- Se añadió `/api/admin/auto-improvement/summary`, protegido por sesión admin.
- Se añadió `/api/automation/auto-improvement/run`, protegido por AUTOMATION_SECRET.
- Se creó `templates/admin_auto_improvement.html`.
- Se integró Mejora continua en navegación admin, Company OS y Product Board.
- Se añadió capa CSS V861 específica para Auto-Improvement OS.
- Se creó `tools/check_v861_self_improving_operations_os.py`.
- Se añadieron reportes V861 de seguridad, niveles de acción, runbook cron, prompts Codex y notas Render.

Preservado:
- V818 master tick y health-check.
- V844 Telegram premium/no filler.
- V845 SHARK IA.
- V847 API-SPORTS guard.
- V850 live/escudos.
- V857 Company OS.
- V859 Product Board.
- V860 cleanup/visual alignment.

## V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL

Base real detectada: V861_SELF_IMPROVING_OPERATIONS_OS_SAFE_AUTOMATION_FINAL.

Trabajo aplicado:
- Se elevó VERSION.txt, APP_VERSION, base.html, cache CSS y runtime a V862.
- Se creó `engines/shark_sentinel_engine.py` como motor seguro de inspección de usuario real simulado.
- Se añadió `/admin/shark-sentinel` con alias `/admin/app-inspector`, `/admin/qa-bot` y `/admin/bot-auditor`.
- Se añadió `/api/admin/shark-sentinel/summary`, protegido por sesión admin.
- Se añadió `/api/admin/shark-sentinel/run`, protegido por sesión admin.
- Se añadió `/api/automation/shark-sentinel/run`, protegido por AUTOMATION_SECRET.
- Se creó `templates/admin_shark_sentinel.html`.
- Se creó `tools/run_shark_sentinel_static.py` para inspección local con Flask test client.
- Se integró Sentinel en navegación admin y Auto-Improvement OS.
- Se añadió capa CSS V862 específica para el panel Sentinel.
- Se creó `tools/check_v862_shark_sentinel_real_user_app_inspector.py`.
- Se añadieron reportes V862 de journeys, modelo de incidencias, política de autofix, admin QA, cron runbook y prompts Codex.

Preservado:
- V818 master tick y health-check.
- V844 Telegram premium/no filler.
- V845 SHARK IA.
- V847 API-SPORTS guard.
- V850 live/escudos.
- V857 Company OS.
- V859 Product Board.
- V861 Auto-Improvement OS.

## V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL

Base real detectada: V862_SHARK_SENTINEL_REAL_USER_APP_INSPECTOR_FINAL, evolucionada de forma controlada sobre la carpeta oficial.

Trabajo aplicado:
- Se elevó VERSION.txt, APP_VERSION, base.html, cache CSS y runtime a V862 Continuous.
- Se creó `engines/continuous_shark_sentinel_engine.py` como motor de ciclo continuo seguro.
- Se añadió `/admin/continuous-sentinel` con alias `/admin/shark-sentinel`, `/admin/app-inspector`, `/admin/qa-bot`, `/admin/bot-auditor` y `/admin/mejora-continua`.
- Se añadieron `/api/admin/continuous-sentinel/summary`, `/api/admin/continuous-sentinel/run` y `/api/admin/continuous-sentinel/issues`, protegidos por sesión admin.
- Se añadió `/api/automation/continuous-sentinel/run`, protegido por AUTOMATION_SECRET y limitado a diagnóstico dry-run.
- Se creó `templates/admin_continuous_sentinel.html`.
- Se creó `tools/run_continuous_sentinel_static.py` para ciclo local seguro con Flask test client.
- Se integró Continuous Sentinel en navegación admin, rail, dock y command strip.
- Se añadió capa CSS V862 Continuous específica para el panel.
- Se creó `tools/check_v862_continuous_shark_sentinel_loop.py`.
- Se añadieron reportes V862 Continuous de loop, seguridad, tracking, perfiles, Browser QA opcional, Company OS y Render Ready.

Modelo de seguridad:
- No modifica código automáticamente.
- No ejecuta deploys.
- No envía Telegram real.
- No llama APIs externas.
- No toca secretos.
- No escribe SQLite durante render.
- Genera diagnósticos, incidencias y prompts seguros para revisión humana.

Preservado:
- V818 master tick y health-check.
- V844 Telegram premium/no filler.
- V845 SHARK IA.
- V847 API-SPORTS guard.
- V850 live/escudos.
- V857 Company OS.
- V859 Product Board.
- V861 Auto-Improvement OS.
- V862 SHARK Sentinel real user inspector.

## V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL

Base real detectada: V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL.

Trabajo aplicado:
- Se elevó VERSION.txt, APP_VERSION, base.html, cache CSS y runtime a V863.
- Se comprobó producción real en `https://bot-apuestas-crgf.onrender.com/api/runtime-version`.
- Producción real devolvió V862 Continuous con HTTP 200 y flags críticos activos.
- Se documentó que V863 no queda certificada en Render hasta ejecutar deploy autorizado.
- Se añadió saneamiento de cabeceras y runtime para evitar valores con saltos de línea.
- Se creó `tools/check_v863_runtime_header_sanitization.py`.
- Se creó `tools/check_v863_real_world_certification.py`.
- Se probaron rutas públicas reales de Render y rutas protegidas/admin sin sesión.
- Se documentaron bloqueos exactos para admin autenticado, secrets de cron, Telegram real, APIs con gasto, Stripe test y QA visual con navegador.
- Se añadieron reportes V863 de certificación real máxima.

Preservado:
- V818 master tick y health-check.
- V844 Telegram premium/no filler.
- V845 SHARK IA.
- V847 API-SPORTS guard.
- V850 live/escudos.
- V857 Company OS.
- V859 Product Board.
- V861 Auto-Improvement OS.
- V862 Continuous Sentinel.

## V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL

Base real detectada: V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL.

Trabajo aplicado:
- Se elevó VERSION.txt, APP_VERSION, base.html, cache CSS y runtime a V864.
- Se añadió flag runtime `has_v864_pc_mobile_visual_big_leap`.
- Se añadió bloque CSS `V864 PC MOBILE VISUAL REFERENCE BIG LEAP`.
- Se reforzaron variables visuales, fondo, cards, botones, chips, match rows, pick cards, admin, bottom nav, responsive y safe-area.
- Se reforzó `templates/partials/ui_components.html` con macros/clases V864.
- Se amplió Continuous Sentinel con reglas visuales V864.
- Se creó `tools/check_v864_pc_mobile_visual_reference_big_leap.py`.
- Se añadieron reportes V864 de PC, móvil, admin, picks, live, SHARK, Telegram, Sentinel, membresías, componentes y próximos pasos.

Preservado:
- V818 master tick y health-check.
- V844 Telegram premium/no filler.
- V845 SHARK IA.
- V847 API-SPORTS guard.
- V850 live/escudos.
- V857 Company OS.
- V859 Product Board.
- V862 Continuous Sentinel.
- V863 real world certification/header sanitization.

## V865_SENTINEL_ISSUE_TO_IMPROVEMENT_WORKFLOW_FINAL

Base real continuada: V864/V865 local en carpeta oficial.

Trabajo aplicado:
- Se creó `engines/sentinel_improvement_workflow_engine.py`.
- Se extendió Continuous Sentinel con `mode=workflow`.
- Se añadió `improvement_workflow_ready` al resumen Sentinel.
- Se crearon rutas admin `/admin/sentinel-workflow`, `/admin/issue-to-improvement` y `/admin/fix-pipeline`.
- Se crearon APIs protegidas `/api/admin/sentinel-workflow/summary`, `/tasks`, `/generate-prompt` y `/update-issue`.
- Se creó `templates/admin_sentinel_workflow.html`.
- Se integró Workflow en topbar, rail, dock y command strip admin.
- Se añadió flag runtime `has_v865_sentinel_improvement_workflow`.
- Se añadió bloque CSS `V865 SENTINEL ISSUE TO IMPROVEMENT WORKFLOW`.
- Se creó `tools/check_v865_sentinel_issue_to_improvement_workflow.py`.
- Se añadieron reportes V865 de preflight, workflow, seguridad, prompts, lifecycle, admin QA, cron runbook y próximos pasos.

Modelo de seguridad:
- No modifica código automáticamente.
- No ejecuta deploys.
- No envía Telegram real.
- No llama APIs externas caras.
- No toca secretos, pagos, usuarios ni DB real.
- Genera tareas y prompts para Codex con aprobación humana.

Preservado:
- V818 master tick y health-check.
- V844 Telegram premium/no filler.
- V845 SHARK IA.
- V847 API-SPORTS guard.
- V850 live/escudos.
- V857 Company OS.
- V859 Product Board.
- V862 Continuous Sentinel.
- V863 real world certification/header sanitization.
- V864 PC/mobile visual big leap.

## V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL

Base real continuada: V865_SENTINEL_ISSUE_TO_IMPROVEMENT_WORKFLOW_FINAL.

Trabajo aplicado:
- Se auditó Render real contra runtime local sin tocar secretos.
- Render respondió `/api/runtime-version` con V865, APIs/Telegram/Odds configurados y `last_error` por cabecera inválida con salto de línea.
- Se añadió `sanitize_runtime_error_value` y se saneó `last_error` en runtime sin ocultar el diagnóstico.
- Se elevó VERSION.txt, APP_VERSION, base.html, cache CSS y runtime a V866.
- Se añadió flag runtime `has_v866_real_render_visual_telegram_picks_payments`.
- Se reforzaron estados de picks: `Cuota pendiente`, `Selección pendiente`, `Pick en revisión`, `Sin pick real publicado` y `Proveedor sin datos ahora mismo`.
- Se ajustó Sentinel para revisar `None/null/undefined` solo en texto visible, cerrando los 19 low como falsos positivos.
- Sentinel V866 quedó en score 10.0, 0 issues y 0 críticos.
- Se ejecutó browser QA móvil local con viewport 390x844 y capturas para `/`, `/app` redirigido a login, `/picks`, `/live` y `/shark`; sin scroll horizontal detectado.
- Se corrigió admin pagos para no afirmar Stripe operativo si `stripe_runtime_status` no lo confirma.
- Se añadieron reportes V866, checks V866 y manifiesto V866.

No realizado:
- No se hizo deploy.
- No se hizo push.
- No se envió Telegram real.
- No se probaron pagos reales.
- No se afirmó pixel-perfect.

Preservado:
- V818 master tick y health-check.
- V844 Telegram premium/no filler.
- V845 SHARK IA.
- V847 API-SPORTS guard.
- V850 live/escudos.
- V857 Company OS.
- V859 Product Board.
- V862 Continuous Sentinel.
- V863 header sanitization.
- V864 visual.
- V865 Sentinel Workflow.
