# TEAM CENTER REAL-DATA CERTIFICATION REPORT

Fecha Madrid: 2026-07-28 07:25
Modo: ejecución local segura
Producción modificada: false
DB real modificada: false
Telegram enviado: false
Stripe ejecutado: false
Llamadas externas: 0

## Decisión

PASS.

El Team Center queda certificado localmente con datos reales disponibles en el proyecto y fixtures production-like existentes. La certificación no demuestra producción, porque no hubo deploy ni acceso a DB real, pero sí valida el comportamiento del módulo con casos completos, parciales, sin escudo, alias, nombre largo, calendario amplio, equipo internacional disponible localmente y equipo no resuelto.

## Fuentes de datos utilizadas

- `data/v844_smoke.db` abierto como fuente local de lectura para equipos y competiciones seed existentes.
- `tests/test_team_center_premium_experience.py` como fixture local production-like para caso completo.
- `tests/test_v944_match_center_foundation.py` como fixture local production-like para nombre largo y relaciones Match Center.
- `tests/test_v940_calendar_sports_experience.py` como fixture local production-like para calendario amplio.
- DB temporal de QA: `%TEMP%/nemesis_team_center_real_data_certification.sqlite`.

No se usó `data/database.db`. No se hicieron llamadas a proveedores deportivos. No se descargaron escudos.

## Inventario certificado

- Equipos seed cargados desde `data/v844_smoke.db`: 26.
- Competiciones seed cargadas desde `data/v844_smoke.db`: 40.
- Fixtures locales cargados: 3 equipos base.
- Partidos QA production-like cargados en DB temporal: 24.
- Viewports probados: desktop 1366x768, tablet 834x1194, móvil 390x844.
- Capturas generadas: 21 en `browser_qa/TEAM_CENTER_REAL_DATA_CERTIFICATION/`.

## Casos probados

| Caso | Ruta | Resultado | Fuente |
|---|---|---:|---|
| Equipo completo | `/team/Club%20Local` | 200 PASS | fixture local existente |
| Equipo parcial | `/team/Real%20Madrid` | 200 PASS | `data/v844_smoke.db` |
| Equipo sin escudo provider real | `/team/Malaga%20CF` | 200 PASS | `data/v844_smoke.db` |
| Nombre largo | `/team/Real%20Club%20Deportivo%20Local` | 200 PASS | fixture local existente |
| Alias | `/team/Barcelona` | 200 PASS | `data/v844_smoke.db` + aliases existentes |
| Calendario amplio | `/team/Local%200` | 200 PASS | fixture local existente |
| Internacional | `/team/Manchester%20United` | 200 PASS | `data/v844_smoke.db` |
| No resuelto | `/team/Equipo%20No%20Disponible%20QA` | 404 seguro PASS | estado negativo controlado |

## Contrato validado

Para los casos 200 se validó:

- `canonical_team_id` presente.
- `provider_team_ids` presente cuando existe origen seguro.
- `official_name` y `display_name` sin sustitución inventada.
- `aliases` expuestos como lista segura.
- `crest` y `crest_source` declarados.
- `competition_ids`, `matches`, `recent_form`, `upcoming_matches`, `recent_results`, `streak`, `freshness`, `source`, `data_quality` y `limitations` disponibles en el contrato.
- `no_fake_data=true`.
- Diagnósticos: `database_writes=0`, `external_calls=0`, `telegram_sends=0`, `stripe_calls=0`.

## Escudos y fallbacks

Resultado: PASS.

- Escudos provider o fallback se resuelven mediante `/team-crest.svg?name=...` sin descargar assets externos.
- Imágenes rotas visibles: 0.
- URLs externas: 0.
- Duplicados visuales: 0 detectados.
- Se corrigió el tamaño del escudo principal del Team Center: el macro emitía `mega-crest`, pero el CSS no tenía regla scoped para esa clase. Se añadió regla limitada a `.team-center-crest .mega-crest` para que el escudo/fallback use el marco principal sin recortes.

## Problemas encontrados y corregidos

1. Escudo principal pequeño o fallback decorativo reportado como recortado.
   - Causa: el template usaba `size='mega'` y el CSS global no definía `.mega-crest` para Team Center.
   - Corrección: regla scoped en `static/v933-product.css` para `.team-center-crest .mega-crest`, imagen y fallback `em`.
   - Impacto: mejor jerarquía visual y fallback estable en desktop, tablet y móvil.

2. Copy visible con mojibake y acentos incorrectos en Team Center y estados preparados.
   - Causa: literales ya materializados como mojibake o sin acento.
   - Corrección: copy corregido en `templates/team_detail.html`, `templates/resource_unavailable.html` y rutas seguras de `app.py`.
   - Impacto: estado no resuelto y conexiones futuras comunican honestamente “No disponible” sin texto degradado.

3. Limitaciones visibles de Sports Knowledge en inglés.
   - Causa: mensajes internos compartidos por Team Center estaban en inglés.
   - Corrección: mensajes equivalentes en español en `engines/sports_knowledge_layer_engine.py`.
   - Impacto: cliente recibe transparencia consistente sin mezclar idiomas.

4. Regla Browser QA demasiado estricta para 404 esperado y emojis decorativos.
   - Causa: el navegador registra el documento 404 esperado como recurso fallido y los emojis de fallback como texto recortado.
   - Corrección: el QA ignora solo el 404 esperado del documento principal y clasifica emojis decorativos como iconos, sin ocultar texto informativo recortado.
   - Impacto: reduce falsos positivos manteniendo detección de overflow, texto real recortado y errores JS.

## Navegación y conexiones

Resultado: PASS.

- Team Center → Match Center usa `/match/<id>` cuando existe partido relacionado.
- Team Center → Competition Center usa `/competition/<canonical_competition_id>` cuando existe ID seguro.
- Team Center → Player Center permanece desactivado honestamente cuando no hay entidad real.
- Team Center → Sports Graph permanece como contrato interno cuando no hay pantalla pública.
- Team Center → Picks usa `/picks` sin inventar pick específico.
- No se crearon Competition Center ni Player Center.
- Enlaces rotos detectados por auditoría global: 0.

## Sports Graph

Resultado: PASS.

Relaciones disponibles sin generación artificial:

- `match_has_team`
- `team_has_match`
- `match_belongs_to_competition`
- `team_competes_in_competition`
- `match_belongs_to_season`
- `match_has_timeline_event`
- `match_has_evidence`
- `match_has_match_intelligence`
- `pick_references_match`
- `telegram_context_mentions_match`
- `shark_context_analyzes_match`
- `event_has_player` y `player_linked_to_team` solo cuando el fixture contiene evidencia.

En equipos parciales sin partidos locales, el grafo queda en 0 relaciones y se comunica como información pendiente, no como fallo.

## Browser QA

Resultado: PASS.

Archivo de evidencia: `browser_qa/TEAM_CENTER_REAL_DATA_CERTIFICATION/browser_qa_result.json`.

Validaciones finales:

- 0 overflow horizontal.
- 0 errores JS.
- 0 errores de página.
- 0 respuestas 500.
- 0 navegación duplicada.
- 0 mezcla cliente/admin.
- 0 imágenes rotas visibles.
- 0 datos ficticios.
- 0 bloques vacíos sin explicación.
- CLS: 0 en casos probados.
- Llamadas externas: 0.
- Provider calls: 0.

También se ejecutó el Browser QA dedicado existente en `browser_qa/TEAM_CENTER_PREMIUM_CLUB_EXPERIENCE/`: PASS.

## QA técnico ejecutado

- `python -m py_compile app.py engines/team_center_engine.py engines/sports_knowledge_layer_engine.py engines/sports_graph_foundation_engine.py engines/match_intelligence_engine.py engines/sports_domain_model_engine.py tools/run_team_center_real_data_certification.py` → PASS.
- `python -m compileall app.py engines tools -q` → PASS.
- `pytest -q --tb=short --basetemp browser_qa/_pytest_tmp_full_team_center_cert -p no:cacheprovider` → PASS.
- `tools/check_team_center_experience.py` → PASS.
- `tools/check_sports_knowledge_layer.py` → PASS.
- `tools/check_sports_core_match_intelligence_engine.py` → PASS.
- `tools/check_v944_match_center_foundation.py` → PASS.
- `tools/run_continuous_sentinel_static.py` → PASS, score 10.0, 0 issues.
- `tools/check_repository_privacy_and_secrets.py` → PASS, confirmed_secret_findings=0.
- `tools/verify_imports_and_routes.py` → PASS, route_count=658, missing_templates=[], missing_static=[].
- `tools/audit_all_routes_links.py` → PASS, routes_registered=707, broken_links=0, redirect_loops=0.

## Rendimiento y efectos secundarios

- No se añadieron llamadas externas.
- No se añadieron dependencias.
- Render no fue usado.
- Producción no fue modificada.
- DB real no fue usada ni escrita.
- Diagnóstico Team Center: `database_writes=0`, `external_calls=0`, `telegram_sends=0`, `stripe_calls=0`.

## Archivos eliminados

- Eliminado directorio temporal local de pytest: `browser_qa/_pytest_tmp_full_team_center_cert/`.

No se eliminaron capturas de evidencia, datos reales, fixtures ni assets.

## Riesgos y limitaciones

- Esta certificación es local; no certifica producción.
- `data/v844_smoke.db` contiene equipos seed parciales y sin partidos locales asociados; se validó el estado parcial, no cobertura deportiva completa real.
- Los fixtures production-like son útiles para QA, pero no sustituyen datos reales de producción.
- Los escudos no se descargaron ni se validaron contra proveedores externos por restricción de no llamadas externas.
- El estado “Manchester United” pasó porque existe localmente en el dataset seed usado por QA; no se asume cobertura internacional completa.

## Siguiente única acción recomendada

Revisar el diff completo del Sprint Team Center + certificación y decidir si se prepara un commit local único cuando el propietario autorice cierre Git. No comenzar Competition Center todavía.