# Current Truth

## Consolidacion activa - 2026-10-02

Esta seccion prevalece sobre los cierres historicos inferiores. Antes de editar,
verificar Git actual y los pendientes; no reanudar ramas antiguas ni repetir
encargos porque un chat o informe los describa como abiertos.

- Repositorio oficial: `bot-NeMeSiS/NeMeSiS-shark-pro-clean`.
- Main observado: `cc1481c0a29f91be49f92abaaea48e3dde345356`; incluye #141.
  #92 ya esta fusionada: su antigua descripcion OPEN/DRAFT no manda.
- Unica candidata de esta mision: `codex/consolidation-20261001`, worktree
  independiente registrado en el mismo repositorio. La carpeta oficial y los
  otros worktrees siguen preservados; no son candidatas de publicacion adicionales.
- Coordinadora: **NeMeSiS — Consolidación y continuidad**, fijada en Codex.
  Un solo escritor conocido sobre la candidata. Otras cuentas, dispositivos y
  sesiones no accesibles no estan certificados. Inventario y recuperacion privados.
- Estado al registrar este cierre: **CANDIDATA PENDIENTE DE VALIDACION REMOTA**.
  Codigo consolidado en `df813446` y `fd13abd2`: merge controlado de #139,
  reparaciones editoriales, guards de publicacion de picks, cache privada
  Founder, PWA, navegacion administrativa y compatibilidad LOCAL SAFE.
  La unica PR corresponde a `codex/consolidation-20261001`; consultar sus
  checks para el ultimo HEAD, no inferir un PASS remoto de esta documentacion.
- #141 y sus contratos POST -> 303 -> GET se conservan. #139 no activa feeds:
  pausa, fuentes permitidas, derechos, revision humana, expiracion y limites siguen.
- De #135 se recupera solo el guard que impide publicar WAIT/NO_BET y cuotas
  invalidas. Su modelo experimental NO se integra ni se aprueba.
- El inventario de #134 se reutiliza; el inspector local ignora reemplazos Git
  que falsearian la ascendencia. No se borran ramas, worktrees ni stashes.
- Pendientes preservados: #136 (presupuesto cooperativo SportsDB), modelo #135,
  fiabilidad/copiloto/RC locales no validados y recuperacion Design historica.
  No se importan sus eliminaciones masivas ni workflows anteriores.
- Pruebas: entorno completo nuevo con requisitos declarados, SQLite temporal,
  credenciales externas ausentes y bloqueo de red exterior. Primera suite:
  3834 = 3822 PASS + 12 FAIL, cero errores/omitidos. Diez fallos reparados
  y revalidados; dos Gunicorn/fcntl no certificables en Windows, exigidos en CI Linux.
  198 focales + 71 navegacion/guards PASS (no sumar como suite unica);
  diez procesos LOCAL SAFE/fresh: 334 PASS. HTTP editorial: 36 casos;
  feed: 12; pospartido #141: 9. Smoke/Madrid/Jinja/privacidad/enlaces PASS.
  Sentinel static: cero incidencias, diagnostico local, no certificacion global.
- Produccion: **NO OBSERVADA en esta mision**. Sin merge, deploy, proveedores,
  cobros, Telegram real ni certificacion Sports Data/LIVE Day 3-7.
- El workflow declara Auto-Deploy desde main. Un eventual merge necesita
  aprobacion separada del SHA y de sus efectos productivos.

Decisiones, procedencia y resultados de esta misma candidata se mantienen en
`docs/NEMESIS_RECONCILIATION_AUDIT.md`. No crear otra cola ni otro informe por
cada reanudacion; comprobar primero esos dos documentos y las refs actuales.

## Punto operativo remoto y cierre Sentinel · 2026-09-23

- GitHub `main` vigente: `228369d42447f37f3023a7f09216205057e4655c` (PR #82).
- Render Web `nemesissharkpro` y Cron `telegram-auto-tick` observados **LIVE**
  en ese SHA. Auto Deploy desde `main` sigue siendo el mecanismo de publicación.
- PR #78 entregó salud de proveedores de solo lectura: abrir Centro de datos hace
  0 llamadas externas y separa configuración, evidencia de plan/pago y estado operativo.
- PR #80 entregó instalación PWA visible sobre la PWA existente: prompt nativo,
  guía iOS, ocultación standalone, iconos versionados y separación respecto a nav/SHARK.
  Instalación física real en iPhone/Android/PC sigue **NO_VERIFICADA**.
- PR #82 añadió comprobación directa de proveedor únicamente por acción explícita
  del admin: sesión admin + CSRF, cooldown 300 s y evidencia saneada. En este cierre
  no se ejecutó ninguna llamada real de proveedor; acceso/plan directo permanece
  **NO_VERIFICADO** hasta que el fundador/admin decida pulsar el control.
- El HEAD exacto de PR #82 `d445c380aa24482e4b30e0d5c7375444a838435c`
  pasó QA, Preflight y Smoke completos, incluidos LOCAL SAFE y las fronteras Sentinel.
- El guard post-merge de `main@228369d4` puede seguir con observaciones programadas;
  no se convierte en PASS por esta documentación. Consultar el run actual antes de
  cualquier merge posterior.
- **OPS-001 Sentinel queda cerrado en alcance PASS_LOCAL_SAFE.** El executor durable
  es deliberadamente local: `sentinel_job_context` exige admin identificado,
  `local_safe_mode_enabled()`, `SENTINEL_JOBS_ENABLED` y una DB contenida en
  `data/local_dev`. Producción debe responder indisponible para ese executor.
- Cada Smoke ejecuta en procesos separados `test_project_control_http.py`,
  `test_sentinel_jobs_http.py` y `test_sentinel_operational_browser.py`. Cubren
  idempotencia, concurrencia, owner scope, CSRF, revisión de fuente, lifecycle
  QUEUED→RUNNING→COMPLETED, fallo saneado/no-retry y guard fuera de LOCAL SAFE.
- Esto **no** convierte Sentinel en servicio productivo, no recertifica los 12
  `LOCAL_SAFE_BLOCKED` históricos ni los bloqueos ambientales conservados.
- Directos y Design siguen siendo frentes preservados con sus propios gaps.
  El candidato acumulado del 19/09 tampoco se declara publicado como una unidad.
- El siguiente bloque interno pasa a **OPS-002 Hygiene / reconciliación remota**:
  ordenar verdad actual, extraer trabajo único antes de cerrar PRs supersedidas y
  no borrar ramas/worktrees/evidencia desconocida. ChatGPT dirige; Codex no se inicia
  automáticamente.

## Punto operativo remoto y entrega cliente · 2026-09-21

- Base remota comprobada: `main@63cd3d9a1d70d839bd0f91d78fb4875931fa635e`.
- PR #56 integrada tras QA, preflight y Smoke completos. Web y Cron fueron
  verificados LIVE en ese SHA; la certificación posterior es el run `35626750137`.
  Consultar su estado real: este documento no lo convierte en PASS por anticipado.
- PR #56 contiene cuatro archivos: listas de Founder OS, gate del icono oficial y
  sus regresiones. NO publicó el candidato cliente/móvil completo.
- Entrega cliente actual: búsqueda de Calendario siempre visible, selecciones
  conservadas fuera de las opciones actuales, cambios sin aplicar, contexto
  visible y restauración prudente de la posición. Rama de revisión prevista:
  `chatgpt/publicacion-calendario-cliente-20260921`.
- Prueba local de este subconjunto: 183 casos PASS, 0 fallos/errores/omitidos;
  incluye 54 casos nuevos, de ellos 39 de componentes Chromium. Datos SIMULATED_QA.
  Los cambios del historial del navegador se simulan, no certifican un iPhone.
- No cambia `app.py`, Sports Truth, tarjetas compartidas, proveedores, DB, usuarios,
  pagos, membresías, Telegram, cron ni configuración Render. No nuevas llamadas
  deportivas. La selección de partidos sigue siendo del servidor.
- Estado al preparar esta entrega: pendiente de QA/preflight/Smoke remotos e
  integración. El cierre verificable se registra en la PR, no se infiere aquí.
- Siguen pendientes los demás bloques acumulados: identidad/historial/temporada,
  metadatos y banderas, LIVE animado, favoritos, diagnóstico completo y PWA.
  No sobrescribir main con un ZIP anterior. Reconciliar por archivo desde su SHA.
- La presentación aislada usa `static/calendar-discovery.css` solo en Calendario.
  Al consolidar el candidato completo, reconciliar su CSS y la copia de estado
  localizada de la plantilla, sin duplicar autoridades ni perder la entrega.

Las secciones inferiores son evidencia histórica, no el estado remoto actual.
Después de cualquier integración, consultar main y Render exact-SHA.

## Producción y remoto verificados · 2026-09-20

Esta sección sustituye como verdad actual al snapshot local del 2026-09-19 que se
mantiene debajo únicamente como procedencia histórica.

- Baseline de `main` verificado antes del candidato STALE: `c7237c4669f7f5c5e0ceefe4150fd71039b49507`. Después de un merge, consultar GitHub `main` y Render exact-SHA para obtener la identidad vigente.
- Render Web y Cron estaban LIVE exactamente en ese baseline al abrir el candidato; un SHA posterior solo se considera producción cuando Render lo marque LIVE.
- Auto Deploy activo desde `main`; Cron cada 5 minutos.
- PR #48/#50/#51/#52 integradas. PR #49 cerrada como supersedida por #51.
- #51 pasó CI QA + preflight + Smoke; el primer cron posterior fue PASS y no gastó
  llamadas de Odds ni API-Football en esa ronda.
- #52 pasó CI QA + preflight + Smoke y conecta Founder OS a la frescura deportiva
  persistida sin consultar proveedores.
- Última evidencia deportiva real observada: SportsDB fallback 180; muestra
  canónica 200 = 18 FRESH, 179 OBSERVED, 3 STALE, 0 NOT_ESTABLISHED; estado PARTIAL.
- El estado PARTIAL es evidencia, no un error inventado ni una garantía universal.
- Pendiente inmediato: identificar los 3 STALE desde el snapshot canónico y llevar
  esa evidencia a diagnóstico/Founder OS con límite de muestra y sanitización.
- No se afirma que el fail-fast sistémico de Odds haya recibido un 429 real en
  producción post-merge; la ronda observada usó caché y realizó 0 llamadas Odds.

## Snapshot local histórico · 2026-09-19


Actualizacion: 2026-09-19. Alcance: copia local Sentinel. No PII ni secretos.

## Identidades observadas

- Rama efectiva: codex/sentinel-operaciones-local.
- HEAD/base: c4a81003de1b5ccdb3036831583e9c1eb65e4417; cambios SIN COMMIT.
- Main local y origin/main local: c4a81003de1b5ccdb3036831583e9c1eb65e4417, main limpio.
- GitHub/Render actuales: NOT_TESTED en este cierre local. Una referencia local no prueba el remoto.
- PR14: ultimo cierre local registra borrador ef759cb88d46463424342598a765a68a0a057a7a; no nueva consulta ni merge.
- Design: 317ac8c37c3c74f39b736a207f55079c7d454856, PRESERVE; 4401 registros dirty en la observacion anterior. No ejecutado ni editado.
- Worktree documental: ad297cf56b7ab302a86b16ae261634549c5a68a4; 6131 registros dirty en la observacion anterior, PRESERVE.
- Inventario anterior: data/local_dev/organization-20260919/inventory.json. Cuatro worktrees, siete ramas locales. No reinventariados ni retirados en este cierre.

## Evidencia y alcance

Ultimo cierre: preview reproducible y FINAL_OVERRIDES_STALE_LIVE_V1.
380 casos distintos de seleccion pertinente: 358 PASS mas bloque Sentinel
22/22 PASS tras corregir el main guard del runner Windows. Primer pase 379 PASS
y un fallo de arnes, conservado en el informe. No suite global certificada.
Replay 10/10: mismo final 5-0 en cinco superficies, navegador desktop/mobile,
sin recarga en Directo ni revival por T2 antiguo. REAL_WORLD_REPLAY_QA, no produccion.
45/45 vistas finales en 1366/390/430, recorrido Home/detalle/retorno/Calendario
y formulario de idioma real. Cero fallos de shell, overflow, JS o requests externas.
203 Jinja y compilacion PASS. Secret/Privacy: 1174 archivos, cero hallazgos.

Huella de producto/pruebas/herramientas, excluye documentos:
`8e3475faa56656546f4a9535163ca1ed48722afc3e3371df0d27abc128197326`.
Manifest acumulado: `data/local_dev/final-source-manifest.json`; 129 rutas,
indice vacio. Detalle, procedencia y XML en
[LOCAL_CONTINUITY](../reports/LOCAL_CONTINUITY_20260919.md).
La clasificacion documental anterior conserva sus UNKNOWN; no autoriza retiradas.

- Sentinel: motor aceptado sin nueva capacidad; runner LOCAL SAFE con inicio/parada/reuso de instancia. Preview 54910 activa al cierre, no servicio productivo.
- R8: diferencias versionadas integradas selectivamente y conservadas; /historico vuelve al handler canonico. R9 NOT_CERTIFIED; arte y conformidad global pendientes.
- Directo/Match Center: HTTP y navegador reales, minuto 0/descuento y periodos observados preservados; fixtures SIMULATED_QA no prueban feed real ni cobertura universal.
- SHARK/apuestas: flujo activo de recomendaciones sin confianza/seleccion inventadas. Hechos, contexto, analisis y cuotas observadas separados; WAIT/NO_BET no se publican como pick.
- Soporte: persistencia y bandeja admin locales; no email externo ni respuesta humana certificados.
- Membresias: concesion manual, ADMIN, suscripcion vigente, cancelacion y expiracion probadas localmente; corregida degradacion del rol ADMIN por expiracion generica. Stripe externo no probado; ELITE+ sin contrato.
- /app: 603 partidos, mismo hash; A/B sin perfilador 5.730/2.084/2.095 -> 5.737/2.085/2.040 s. Menos SQL por lote, sin mejora significativa de latencia. Timeout productivo no resuelto. Aislamiento de usuarios preservado.

## Contratos y pendientes

SE-01 sigue PASS_LOCAL_SCOPE; los 12 LOCAL_SAFE_BLOCKED historicos siguen
NOT_CERTIFIED. Los 43 bloqueos ambientales posteriores tampoco se reetiquetan.
DAY 3/4/5 y SPORTS_DATA_LIVE_CERTIFICATION.md preservados; no nueva observacion
productiva. Madrid, Sports Truth, App Icon y fallback no se alteran por organizar.
No se afirma P0/P1 global cero sin revisar produccion.

[Cola](CODEX_QUEUE.md), [bloqueos](BLOCKERS.md), [versiones](RELEASE_STATE.md).
Los SHA/CI/PR9 abiertos citados en documentos de septiembre 9 son historia,
no incidentes actuales. No se inventa una recertificacion de produccion.
