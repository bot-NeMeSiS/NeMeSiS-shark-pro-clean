# Preflight Git y reparacion aislada de PR91 - 2026-09-23

## Estado remoto comprobado
Fetch repetido al finalizar; las referencias no avanzaron.

| Referencia | SHA exacto | Estado |
| --- | --- | --- |
| origin/main | 2b59d3fca4f2982652279004ecffc3ea56617807 | Base V940 |
| PR91 | 4043d3ce3a1a9264220dbc9acb81ab225db5c74d | OPEN, DRAFT, mergeable=true; no fusionada |
| PR90 | 860aa4462ac621c4ca8a0d93ca45b59c52a250c2 | OPEN, DRAFT, mergeable=true; no fusionada |

PR91: https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean/pull/91
PR90: https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean/pull/90

CI del HEAD remoto exacto de PR91:
- QA SUCCESS: https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean/actions/runs/35916556779
- Render Deploy Guard SUCCESS: https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean/actions/runs/35916556853
- Smoke FAILURE: https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean/actions/runs/35916556801

No hay HEAD nuevo certificado por CI. El log remoto contiene 2464 pruebas estandar aprobadas antes del fallo visual; ese resultado pertenece exclusivamente a 4043d3ce y no certifica la reparacion local.

## Reparacion local, separada de V941
Worktree: data/local_dev/pr91-reconcile
Rama: codex/pr91-smoke-repair-local
Padre: 4043d3ce3a1a9264220dbc9acb81ab225db5c74d
Commit local: db3670e7c2e1c5da65d2435f28ff254dee7673a6
Tres archivos, 10 inserciones y 2 eliminaciones. Worktree limpio tras commit. Sin push.

Causas y alcance:
1. main elimino el import _fetch_one y STATIC_ROOT que el motor visual sigue utilizando. Se restauran las dependencias del cache local; no se anaden descargas ni envios.
2. Al resolver ese bloqueo, la galeria revela una llamada con highlight={} a build_result_visual_card_payload, cuya firma solo admite match/pick. Se elimina el argumento invalido de la prueba; permanecen todas sus aserciones.
3. El paso posterior de Smoke, omitido por el fallo anterior, conserva un recuento HTTP 23 frente a 24 tareas reales. Se alinea con el lector ya corregido en PR91 y se comprueba TG-001 QA/LOCAL_ONLY.

Sin cambios a la evidencia de proveedores, cuotas, claves, cola documental, pagos o logica de membresias. No se incorporan archivos V941.

## Verificacion local del contenido del commit
Python 3.12.14, pytest 8.3.4, Chromium local 1228. CI usa Python 3.11 y otro build de Chromium: pendiente revalidacion remota.

- 126 PASS: Telegram visual premium (74) y proveedores/Project Control reader (52).
- 18 PASS: Project Control HTTP (8), Sentinel jobs HTTP (9), Sentinel operational browser (1), cada suite en proceso nuevo.
- 35 PASS: final replay (10), betting evidence (11), client continuity (1), membership preservation (13), cada suite LOCAL SAFE en proceso nuevo.
- Total: 179 pruebas distintas, sin fallos ni omisiones en estas ejecuciones finales.
- Compilacion sintactica de los tres archivos modificados: PASS.
- git diff --check: PASS para el parche PR91.
- BOUNDARY_EVENTS [] en las ejecuciones supervisadas. No Telegram real, pagos, proveedores externos ni secretos.

Evidencia XML dentro del worktree:
- data/local_dev/candidate-6af2a6a8f61a499795fb4eb03a3e0e3f/result.xml
- data/local_dev/repair-final-project_control_http.xml
- data/local_dev/repair-final-sentinel_jobs_http.xml
- data/local_dev/repair-final-sentinel_operational_browser.xml
- data/local_dev/candidate-ad7f31f26b0f47b1b341f842097d37f4/result.xml
- data/local_dev/candidate-35c0062e9a364c3cb66cd8d326c06714/result.xml
- data/local_dev/candidate-2dcf6b522e08430c905c3f80ead1d6a9/result.xml
- data/local_dev/candidate-c058f036ec614951b3c6ebb5b4df7c60/result.xml

## PR90: analisis de reutilizacion, reconciliacion pendiente
Base declarada anterior: 2ed4b799b472bd702b0e325d3a4f5ea2a942dbb1.
Los verdes del HEAD 860aa446 sobre esa base no se heredan para un futuro HEAD reconciliado.

Sus siete archivos aportan team_form_snapshot, componente/CSS de Admin Match Intelligence y tres suites de pruebas. La comparacion desde el ancestro comun a main no muestra cambios en team_form_engine.py, admin_match_intelligence.html ni team_result_evidence_engine.py. No hay solapamiento directo con los archivos V941 modificados. Esto favorece una reconciliacion limpia, pero no demuestra ausencia de regresiones.

Trabajo valido que preservar:
- Reutiliza build_team_result_evidence, no crea otra fuente de resultados.
- Solo finales confirmados con fecha e identidad; excluye provisionales y contradicciones; conserva marcadores cero.
- Cinco resultados validos mas recientes, muestra omisiones, sin llamadas externas.
- coverage_state=LOADED_SAMPLE_ONLY, season_complete=False y expected_played=None: muestra alcance real, no promete temporada completa.
- Componente visual y enlaces existentes deben integrarse, no duplicarse.

SHARK debe reutilizar team_form_snapshot y exponer form_available, sample_size, coverage_state y omisiones. ok=true no debe interpretarse como datos completos, acceso al proveedor ni probabilidad de ganar. No convertir goles o balance de muestra en recomendaciones o liquidaciones.

Rebase/integracion y pruebas del nuevo HEAD pendientes hasta resolver el gate rojo de PR91. No se descarta ni copia PR90; no se ha alterado su rama remota.

## V941 y produccion
El trabajo local V941 se conserva aparte en codex/admin-pc-master-v941 sobre main@2b59d3f. Su ZIP anterior NO incorpora PR90/PR91 y NO satisface la base reconciliada exigida. Se considera PROVISIONAL / NO CERTIFICADO PARA ENTREGA; no se ha regenerado ni publicado otro ZIP o version.
Los resultados anteriores de 517 pruebas son historicos de ese contenido y no certifican CI, reconciliacion ni produccion.
SHA DE PRODUCCION: DESCONOCIDO / NO CERTIFICADO. Un health 200 no demuestra identidad de despliegue.

## Siguiente paso concreto
El usuario prohibio push salvo peticion explicita. Hace falta autorizar el push normal del unico commit db3670e7 a la rama existente de PR91, codex/provider-evidence-truth-20260923, sin force, para obtener QA/Deploy Guard/Smoke del nuevo HEAD. Revalidar antes que la rama remota siga en 4043d3ce. No crear otra PR, fusionar ni desplegar.
Tras CI totalmente verde, reconciliar PR90 sobre la base actual preservando el arreglo y volver a validar su HEAD exacto; luego fijar la base del Master Control. Las fases dependientes no se declaran completas.
