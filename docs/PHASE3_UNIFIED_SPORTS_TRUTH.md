# Fase 3 — Unified Sports Truth

**BLOQUEADA POR GATE DE ESTABILIDAD — NO MERGE / NO DEPLOY HASTA CERTIFICAR #186 + CRON + BACKUP /data.**

Alcance: Fase 3 exclusivamente. Rama `codex/phase3-unified-sports-truth`, worktree aislada. Base verificada: `9fa64ac2be2374e3c55c5a48e8ef54f4d1417088`, que ya incorpora #186. No se ha certificado el SHA actualmente desplegado ni la estabilidad de producción desde esta rama. Ninguna operación sobre Render, secrets, planes, Stripe o Telegram real; ninguna Fase 4–11.

## 1. Arquitectura

Los ingestors existentes conservan sus llamadas autorizadas. Guardan además receipts en la misma transacción SQLite. El repositorio `unified_sports_truth_store` carga evidencia y mappings en lotes. El resolver puro `unified_sports_truth_engine` selecciona campos y produce `NEMESIS-UNIFIED-SPORTS-TRUTH-V1`. Los adaptadores conservan los contratos de presentación y rutas actuales.

Flujo: proveedor → ingestor existente → receipts/mappings SQLite → resolver determinista → proyección compatible → consumidores. Ningún template añade consultas a proveedores. El modelo de dominio sigue sin SQLite, red, credenciales ni generación IA.

Las tablas son aditivas, creadas sólo durante escrituras autorizadas: `sports_truth_receipts` (último receipt por partido/proveedor con relojes independientes por grupo), `sports_truth_mappings` (mapping único conservador y prueba), `sports_truth_generation` (invalidación entre workers). No se cambian DB_PATH, tablas de negocio ni datos existentes en bloque. Una lectura de una DB antigua funciona sin migrarla.

## 2. Archivos

- `engines/unified_sports_truth_engine.py`: resolver, frescura, evidencia, contratos y adaptadores puros.
- `engines/unified_sports_truth_store.py`: persistencia, mapping, lecturas por lotes e invalidación.
- `app.py`: límites de lectura, Home/Calendar/Live/Match Center/SHARK, odds e ingesta SportsDB, dedupe y compatibilidad.
- `engines/api_football_live_tracker_engine.py`: receipts de fixture/eventos/stats e ID canónico persistente.
- `engines/api_exploitation_engine.py`: receipts de profundidad y distinción ausencia/restricción/error.
- `engines/v935_launch_trust_engine.py`: consumo de lifecycle canónico con caducidad.
- `engines/sports_domain_model_engine.py`: entidades, ID estable y provenance compartida.
- `engines/match_context_engine.py`: contexto de inteligencia y estadísticas seleccionadas.
- `services/sports_service.py`: observador de sólo lectura y enlaces antiguos tras dedupe.
- `tests/test_unified_sports_truth_phase3.py`: conflictos, frescura, mappings, reloj, odds, derechos, caché y consistencia HTTP.
- `tests/test_sports_core_unified_domain_model.py`: garantía de resolver puro.
- `tests/test_v940_calendar_sports_experience.py`: caché con SQLite real y escrituras de negocio ajenas.
- `tools/benchmark_unified_sports_truth.py`: benchmark reproducible de cinco rutas.
- `tools/qa_unified_sports_truth_browser.py`: QA real HTTP, escritorio/móvil y capturas.
- `.github/workflows/nemesis-ci.yml`: regresiones de Fase 3 añadidas a CI.
- Este documento.

## 3. Contrato y entidades

El match contiene `contract`, `canonical_match_id`, `phase`, `teams`, `competition`, `players`, `values`, `resolved`, `status_truth`, `kickoff_madrid`, `timezone`, `evaluated_at`, `valid_until`, `odds_snapshot` y `provider_evidence`.

`provider_evidence` mantiene values del receipt, raw redactado, proveedor/ID y clocks por grupo; `resolved` guarda la decisión separada: value, receipt_id, provider/source, observed_at/fetched_at, stale_reason, availability, TTL, regla ganadora, alternativas y conflicto. No se asigna confidence inventada.

Team, competition y player reutilizan los contratos existentes del dominio. Sin mapping explícito, sus IDs mantienen namespace de proveedor. No se unifican equipos por parecido del nombre. El match conserva su ID interno aun si cambia la fuente ganadora. Un mapping incompatible se rechaza, nunca se sobrescribe.

`phase`: scheduled/live/halftime/finished/postponed/cancelled/suspended/stale/unknown. Próximos vencidos no se convierten en live por hora, minuto o score. Resultados pendientes sin marcador confirmado permanecen unknown. Se conservan los estados de período y reglas fail-closed existentes para señales contradictorias dentro del mismo receipt.

Odds snapshot incluye ID, mercados H2H adquiridos por la integración existente, provider_timestamp, usable y provenance. No amplía el catálogo de mercados ni cambia lógica editorial.

## 4. Reglas de resolución y frescura

Selección por campo: evidencia fresca, dato real antes de ausencia confirmada, precedencia de campo, observación más reciente dentro del mismo rango y hash estable como desempate. Los estados de acceso restringido/error no son ganadores. Si sólo queda evidencia caducada se conserva su hecho y causa; no se certifica como live ni como odds utilizable.

| Grupo | Preferencia de campo | TTL |
|---|---|---|
| Identidad, logos, estadio, media | TheSportsDB → API-Football → local | 30 días |
| Kickoff | API-Football → TheSportsDB → local | 24 horas |
| Estado/marcador/minuto | API-Football → TheSportsDB → local | live 120 s; scheduled 24 h; terminal 30 días |
| Stats/eventos | API-Football → TheSportsDB → local | 120 s; captura terminal 30 días |
| Lineups, players, injuries, standings | API-Football → TheSportsDB → local | 24 horas |
| H2H | API-Football → TheSportsDB → local | 7 días |
| Odds | The Odds API con provenance real | 900 s |

Estado, goles y minuto pertenecen a una sola observación ganadora: nunca se mezclan goles de receipts distintos. Ausencia mantiene `None`; el adaptador antiguo conserva `score=""` cuando lo necesita. No se fabrican ceros. El minuto se vacía fuera de live/halftime.

`updated_at` genérico no rejuvenece evidencia. Un refresco de fixture no rejuvenece stats/eventos antiguos ni sus raw originales. Se distinguen `NO_STATISTICS`, `NO_VIDEO`, `NO_LINEUPS`, `EMPTY_CONFIRMED`, `PLAN_RESTRICTED`, `BLOCKED_BY_ACCESS`, `TECHNICAL_ERROR`, `UNRESOLVED_IDENTITY` y stale explícito. Odds necesita timestamp del proveedor, fetched_at real y precio finito mayor que uno; sin provenance completa o tras TTL no es utilizable y no se entrega a consumidores legacy.

Kickoff se interpreta con las reglas existentes y se presenta con `ZoneInfo("Europe/Madrid")`, incluidos invierno/verano. Los relojes de evidencia quedan normalizados como instantes UTC.

El motor aporta provenance de video; los componentes media conservan la política existente de derechos/acceso. Un URL raw no habilita un highlight sin revisión.

## 5. Consumidores y rendimiento

Migrados Home `/app`, Calendar/Partidos `/calendario`, Live `/directo`, Match Center `/match/<id>` y contexto SHARK `/shark`. La lectura común de records y el modelo de dominio dan contexto canónico a Picks sin cambiar la lógica editorial. También se adaptan live cache legado, live tracker, dedupe y observador interno.

La caché resuelve a lo sumo hasta el próximo deadline real, kickoff o 60 s. LRU de 256 snapshots, copia independiente por consumidor, memo por request y lecturas por bloques de 400 IDs. El caché de resumen conserva su clave y se invalida por generación de receipts confirmada entre workers. Reconciliar caducidad no consulta proveedores ni SQLite. Los grupos de detalle distintos no se confunden aunque compartan partido y evaluation time.

## 6. Verificación

- 333 pruebas relevantes aprobadas en la revisión final: Fase 3, dominio/contexto, evidencia, odds, Calendar, single-source, identidad SportsDB, backoff API-Football, #186/Cron, backup, highlights y postmatch/entrega Telegram con transports simulados.
- Después de los refuerzos finales (raw independiente, memo por evidence hash y dedupe por grupo), 50 pruebas del resolver/dominio/identidad SportsDB aprobadas. El preflight remoto detectó después una incompatibilidad con stats de la caché live legacy; se incorporaron sus rows ya adquiridas con captured_at independiente. Tras esa corrección, 71 pruebas del resolver/dominio/contexto/identidad aprobadas, incluido el rechazo de clocks rejuvenecidos.
- Suite amplia inicial: 4.267 aprobadas, 36 fallos. Contraste exacto de esos 36 nodos en main base: 26 fallos reproducidos y 10 aprobados. Los diez correspondientes a compatibilidad de Fase 3 fueron corregidos y están incluidos en la revisión relevante verde. La suite amplia completa no se declara certificada sobre el SHA final.
- Los 26 fallos de base incluyen encoding cp1252, login/token local, autorización/guardas de endpoints administrativos, aislamiento Stripe en el harness y Gunicorn/fcntl no disponible en Windows. No se modifican esas guardas para hacer pasar pruebas.
- QA real Flask HTTP/Chrome: cinco rutas × 1366×900 y 390×844; diez respuestas 200, sin overflow de documento, pageerror, raw technical copy comprobado ni duplicación de main. Conflicto sintético AF live 1–0 / TSDB FT 3–2; el mismo match queda live 1–0 en las cinco superficies. No sustituye una observación de producción ni una prueba de todos los estados posibles.
- QA adicional V944: seis capturas (PC/tablet/móvil × datos disponibles/parciales), PASS tras corregir el preflight; sin errores JS/console/HTTP ni llamadas externas y con navegación real de vuelta al calendario.
- Se comprueban expresamente ausencia, restricción/error, score desconocido, odds stale/sin fetch timestamp, Madrid invierno/verano, mapping ambiguo rechazado, redacción de secretos, derechos de media y vencimiento de caché.

## 7. Benchmark antes/después

Windows, SQLite local desechable, 30 fixtures sintéticos, siete requests calientes por ruta, misma herramienta y base. Cuenta SELECT/PRAGMA en todas las conexiones Python. Cero llamadas de proveedor. Estos resultados miden server rendering con test client, no red/Render ni p95 de producción.

| Ruta | Mediana antes → después | Consultas antes → después |
|---|---|---|
| Home | 51,22 → 77,48 ms | 30 → 31 |
| Calendar | 93,77 → 105,38 ms | 32 → 33 |
| Live | 68,68 → 82,47 ms | 31 → 32 |
| Match Center | 64,74 → 97,13 ms | 58 → 59 |
| SHARK | 77,69 → 113,27 ms | 46 → 48 |

La trazabilidad añade coste: no es una mejora neta de latencia. Las pruebas de bulk read y memo verifican coste acotado, sin una consulta por partido. El benchmark de rutas utiliza fixtures legacy; volumen real de receipts, múltiples workers y carga simultánea deben medirse después del gate. JSON conserva tiempos fríos, máximos y status codes.

## 8. Riesgos/gaps

- Producción, Cron y backup automático siguen sin certificación en esta ejecución. #186 mergeada no equivale a LIVE estable.
- SQLite antiguo no recupera evidencia histórica que ya fue sobrescrita antes de esta fase. Los receipts se pueblan incrementalmente con ingesta autorizada; sin clocks o sección real, se devuelve limitación trazable.
- Mappings cross-provider ambiguos quedan separados. El engine consume mapeos verificados y el dedupe exacto existente; no añade fuzzy matching ni backfill remoto.
- La profundidad depende del plan/cobertura real. Un contrato admite players/injuries/standings/H2H cuando ya existe evidencia; no promete nuevas capturas de todos esos grupos.
- Se conserva sólo el último receipt/grupo por proveedor, no un event log ilimitado. La decisión audita las alternativas retenidas, no todas las versiones históricas.
- El incremento de latencia y los 26 fallos reproducidos de base exigen revisión y CI Linux antes de autorizar merge. La compatibilidad se verificó con SQLite local y transports simulados; no se probaron pagos/sesiones reales en LIVE.

## 9. Revisión

Crear PR DRAFT de esta rama, con el bloqueo en título y descripción. No activar auto-merge ni deploy manual. La PR enlaza esta arquitectura; SHA final y número de PR se registran en el informe de entrega externo al commit. Antes de cerrar, comprobar que origin/main sigue siendo la base incorporada; si cambia, rebase y repetir las pruebas afectadas.

## 10. Checklist exacto de autorización

Todos los puntos deben quedar respaldados por evidencia fechada y revisada; ninguna casilla se marca por inferencia:

- [ ] #186 integrada en main y SHA LIVE observado que incorpora ese fix; health, rutas y DB_PATH `/data/database.db` correctos.
- [ ] Certificación operativa del Cron: al menos 12 ticks consecutivos de cinco minutos y la ventana nocturna siguiente, sin el incidente intermitente, jobs_failed/error/timeout inexplicado ni ejecuciones solapadas. Revisar job results y logs, no sólo HTTP 200.
- [ ] Telegram/postmatch sin envíos duplicados y sin pérdida de trabajos; backoff/cuota de proveedores y tiempos de tick razonables.
- [ ] Backup creado por la ejecución **automática** de la ventana 04:30–06:30 Madrid siguiente (5 de octubre de 2026 o la próxima ventana real), con resultado de ejecución documentado. Un backup manual o `DISABLED` no certifica este punto.
- [ ] Archivo y manifiesto nuevos en `/data/backups` (o directorio efectivo configurado), fecha Madrid, tamaño no nulo, hash y validación correcta; copia SQLite íntegra y espacio/retención comprobados conforme a `DATA_BACKUP_RUNBOOK_V743.md`.
- [ ] Restauración de esa copia ensayada en ubicación aislada, sin reemplazar LIVE; SQLite integrity y tablas/usuarios/picks/memberships/highlights representativos verificados.
- [ ] Rama rebasada sobre el main certificado actual; CI Linux verde en el SHA candidato. Los 26 fallos de base se resuelven o se triagan explícitamente, sin rebajar guardas ni ocultar una regresión de esta fase.
- [ ] Tests relevantes y QA PC/móvil repetidos si hubo cambios/rebase; revisión del coste de provenance y benchmark con receipts representativos aceptada.
- [ ] Revisión humana del contrato, mappings conservadores y ausencia de regresiones de rutas/sesiones/highlights/postmatch/Telegram/Stripe test.
- [ ] Autorización explícita del responsable para merge y, separadamente, para cualquier paso de deploy. Esta PR permanece DRAFT/bloqueada mientras falte cualquiera de los requisitos anteriores.

Los números de ticks son criterios de aceptación propuestos para este cierre; no una afirmación de que producción los haya cumplido. No se inicia ninguna fase posterior.
