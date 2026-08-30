# NeMeSiS SHARK PRO - Sports Data Quality + LIVE Certification

## Estado ejecutivo

**CERTIFICATION: REAL_SPORTS_CERTIFICATION_IN_PROGRESS**

- Gate: observación real de 3-7 días naturales.
- Inicio: 2026-08-28.
- Evidencia completada: DAY 1 baseline + DAY 2 observación real.
- Producción observada: `https://bot-apuestas-crgf.onrender.com`.
- SHA local/origin/Render observado: `4098d1c73921458b863b0ea50eb7812780202745` (commit de informe únicamente; código deportivo heredado de la base desplegada anterior).
- Gasto nuevo: **0**.
- Cambios de producción: **0**.
- Ranking modificado durante el gate: **NO**.
- Resultado provisional: catálogo y sincronización operativos; LIVE y relevancia Home aún no certificados.
- Corrección P0 posterior a Day 1: desplegada, pero **NO RECERTIFICADA**. DAY 2 demuestra una inconsistencia real entre la verdad cache-only de Directo y la presentación de Home/Match Center.

No se declarará PASS por el mero transcurso de tres días. Debe existir una muestra real de partidos Tier S/A, idealmente en directo, y coherencia verificable entre proveedor, Home, Directo y Match Center.

## Política de evidencia

| Origen | Uso |
|---|---|
| `REAL_PRODUCTION_OBSERVATION` | Render MCP, endpoints de producción cache-only y HTML realmente servido. Válido para este gate. |
| `LOCAL_QA` | Código, tests y contratos locales. Explica capacidad, pero no certifica producción. |
| `SIMULATED_TEST` | Fixtures controladas. No se usa como evidencia de cobertura real. |

Reglas activas:

- No se inventan partidos, cuotas, minutos, eventos, consumo ni coste.
- No se llama a proveedores para rellenar una muestra.
- No se mezcla QA con observación real.
- Las anomalías generan `OBSERVATION -> EVIDENCE -> RECOMMENDATION`.
- No se autocorrigen rankings ni datos en producción durante el gate. La corrección P0 autorizada se mantiene exclusivamente local hasta una aprobación posterior.

## Stack deportivo realmente observado

| Proveedor/capa | Estado real | Evidencia Day 1 | Capacidades observadas |
|---|---|---|---|
| TheSportsDB | `REALTIME/CACHED`, activo en catálogo | 800 registros sincronizados; 180 tarjetas en `/partidos`; fuente visible `TheSportsDB API`; última actualización 06:25-06:31 Madrid | Fixtures, resultados, equipos y escudos. Estados live presentes pero con contradicciones. |
| API-Football / API-Sports | `PARTIAL`, configurado y activo | Runtime `configured=true`; tracker habilitado; última sincronización conocida; 0 fixtures live devueltos en la muestra | Ventana de fixtures y consulta live implementadas. Minuto, eventos y stats no observados hoy. |
| The Odds API | `PARTIAL`, configurado sin dato actual | `the_odds_configured=true`, `with_odds=0`, `odds_freshness_status=no_real_odds` | Cuotas/mercados preparados; no hay evidencia real Day 1. |
| Sportmonks | `UNAVAILABLE` | Registro de código únicamente; sin actividad real observada | No certifica ninguna capacidad. |
| Sportradar | `UNAVAILABLE` | Registro de código únicamente; sin actividad real observada | No certifica ninguna capacidad. |

### Matriz de capacidad

| Capability | Required | Current | Gap | Impact |
|---|---|---|---|---|
| Fixtures | Sí | `REALTIME/CACHED` | Sin gap de presencia en Day 1 | Base de catálogo operativa. |
| Results | Sí | `PARTIAL` | 4-5 finalizados según contrato consultado; falta reconciliación estable | Riesgo de estados distintos entre superficies. |
| Live score | Sí | `PARTIAL` | Dos registros se publican como LIVE en una capa y FT en otra | Bloquea certificación LIVE. |
| Minute | Sí | `UNAVAILABLE` en muestra | Los dos registros conflictivos no tienen minuto | No se puede afirmar experiencia live de primer nivel. |
| Events | Deseable | `UNAVAILABLE` en muestra | Cero eventos API-Football; el único timeline visible es un hecho de estado, no un evento deportivo profundo | SHARK carece de contexto live. |
| Lineups | Deseable | `UNAVAILABLE` en muestra | Sin evidencia real | Match Center incompleto para partidos importantes. |
| Stats | Deseable | `UNAVAILABLE` en muestra | Cero stats observadas | Limita SHARK y comparación deportiva. |
| Standings | Sí para Competition Center | `CACHED/PARTIAL` por arquitectura | No observadas en este baseline | Requiere muestra específica. |
| Teams | Sí | `CACHED` | Nombres y entidades presentes | Operativo en la muestra. |
| Players | Deseable | `PARTIAL/NOT_OBSERVED` | Sin evidencia Day 1 | No certificable. |
| Logos | Sí | `CACHED` | 180/180 partidos del catálogo consultado tenían ambos escudos | PASS Day 1. |
| Odds | Betting, no Sports relevance | `UNAVAILABLE` en muestra | 0 partidos con cuota | No afecta la presencia deportiva; sí limita betting intelligence. |
| Historical | Deseable | `PARTIAL/NOT_OBSERVED` | Sin prueba específica Day 1 | Pendiente. |

## DAY 1 - Baseline real

- **Fecha:** 2026-08-28
- **Ventana observada:** 06:26-06:35 Europe/Madrid
- **Origen:** `REAL_PRODUCTION_OBSERVATION`

### Producción y sincronización

| Métrica | Resultado |
|---|---:|
| Render health | PASS |
| Active error logs en ventana consultada | 0 |
| Provider activo declarado | `api-sports/api-football` |
| Último sync runtime | 2026-08-28 06:30 Madrid aprox. |
| Sports cron | `PARTIAL`, trigger `shared_telegram_cron` |
| Próxima ejecución declarada | 15 minutos después del último tick |
| Catálogo sincronizado | 800 |
| Partidos disponibles en contrato realtime | 230 |
| Partidos de hoy en contrato realtime | 175 |
| Tarjetas en `/partidos` | 180 |
| Directos canónicos | 0 |
| Finalizados | 4-5 según contrato/instante |
| Picks | 0 |
| Partidos con odds | 0 |
| Duplicados por ID en calendario | 0 |
| Duplicados por fecha/hora/equipos | 0 |
| Escudos ausentes en 180 partidos | 0 |
| Stale live canónico | 0 |
| Bad status cross-contract | 2 |
| Minutos ausentes en registros presentados como LIVE | 2 |

### Métricas canónicas de observación

| Campo | DAY 1 | Alcance de la evidencia |
|---|---:|---|
| `matches_received` | 230 | Contrato cache-only `/api/realtime/sports`. |
| `matches_live` | 0 | Directos canónicos; existen 2 estados LIVE/FT contradictorios fuera de esta cuenta. |
| `important_matches_live` | 0 | No hubo Tier S/A claramente live en la ventana. |
| `Tier_S_matches` | 26 | Coincidencias de etiqueta, no 26 élite fiables. |
| `Tier_A_matches` | 12 | Coincidencias de etiqueta. |
| `unknown_competitions` | 130 | Partidos sin mapear por el registry local actual. |
| `duplicates` | 0 | Por ID y por fecha/hora/equipos en 180 tarjetas. |
| `stale_matches` | 0 | Métrica canónica; los 2 LIVE/FT se registran como `bad_status`. |
| `missing_scores` | 0 | En la muestra canónica live; no se interpreta el marcador vacío de próximos como score ausente. |
| `missing_minutes` | 2 | Registros presentados como LIVE sin minuto. |
| `missing_crests` | 0 | 180/180 tarjetas con ambos escudos. |
| `bad_status` | 2 | Conflictos LIVE frente a FT/is_finished. |
| `broken_match_links` | 0 | 180 enlaces de Match Center presentes; muestra de élite navegable. |
| `provider_errors` | 0 | Logs de error activos en la ventana consultada. |
| `last_sync` | 2026-08-28 06:30 Madrid aprox. | Runtime de producción. |
| `next_sync` | 2026-08-28 06:45 Madrid aprox. | Derivado del siguiente tick declarado de 15 minutos. |

La diferencia 175/180 no se interpreta como duplicación: `/partidos` incluye estados adicionales y la observación cruzó instantes de sincronización diferentes.

### Tier S/A y calidad del registry

Aplicando el registry oficial local actual al catálogo real de producción:

| Resultado | Valor |
|---|---:|
| Coincidencias etiqueta Tier S | 26 |
| Coincidencias etiqueta Tier A | 12 |
| Tier B | 7 |
| Tier C | 5 |
| Sin mapear | 130 |
| Falsos positivos Tier S demostrados por nombre genérico + país | al menos 16 |

Ejemplos confirmados de falsa elevación a Tier S:

- `Premier League` de Ucrania, Rusia, Malta, Islas Feroe, Gales y Canadá.
- `Bundesliga austríaca`, capturada antes de la regla Tier B.
- `Serie A` de Ecuador.

Conclusión: **38 coincidencias S/A no equivalen a 38 partidos prioritarios fiables**. El registry debe desambiguar competición por país/ID antes de utilizarse como evidencia de élite. Durante este gate no se modifica el ranking; se registra el defecto.

Partidos de alto interés claramente presentes en el catálogo Day 1:

- Bayern de Múnich - Stuttgart, 18:30 Madrid.
- Lille - Paris Saint-Germain, 18:45 Madrid.
- AC Milan - Venezia, 18:45 Madrid.

Los tres existían en `/partidos` y sus enlaces llevaban a Match Center.

### LIVE: contradicción bloqueante

Dos partidos de CONCACAF Central American Cup se observaron con el siguiente conflicto:

| Partido | Capa realtime | Estado canónico anidado | Match Center | Minuto | Score |
|---|---|---|---|---|---|
| Mixco - Alianza | `LIVE` | `FT`, `is_finished=true` | “En directo”, “Fresco”, “Partido en curso” | ausente | 2-0 |
| CD Olimpia - Deportivo Saprissa | `LIVE` | `FT`, `is_finished=true` | “En directo”, “Fresco”, “Partido en curso” | ausente | 2-1 |

Los encuentros habían comenzado a las 02:30 Madrid y seguían presentándose como activos alrededor de las 06:30. La pantalla `/live` canónica no los mostró como directos, pero Match Center sí. También se observó atribución visible `Api Football` mientras el payload de la entidad indicaba fuente TheSportsDB.

**Estado LIVE Day 1: FAIL CANDIDATE.** Falta confirmar si el defecto reaparece en una ventana Tier S/A real antes de cerrar el gate, pero la incoherencia actual ya es un fallo de calidad.

### Home relevance

La primera vista de Home mostró, por este orden útil deduplicado:

1. Ansan Greeners - Daegu FC, South Korean K League 2.
2. Jeonnam Dragons - Cheonan City, South Korean K League 2.
3. Dalian Yingbo - Beijing Guoan, Chinese Super League.

En el mismo catálogo existían partidos claramente más relevantes para el día, como Bayern-Stuttgart, Lille-PSG y Milan-Venezia. Producción sirve el SHA `50bac5b0`; el ranking Sports Relevance observado en el árbol local está todavía sin publicar dentro de cambios locales, y además contiene ambigüedades de país.

**HOME RELEVANCE Day 1: FAIL CANDIDATE.** Home está priorizando proximidad/orden de feed por encima de importancia deportiva demostrable.

### Partidos, Directo y navegación

- `/partidos`: PASS Day 1 como catálogo amplio; 180 enlaces Match Center y 0 placeholders vacíos detectados.
- `/live`: PASS parcial como estado vacío/fallback; no mostró los dos falsos directos del contrato secundario.
- Home -> Match Center: PASS en muestra.
- Partidos -> Match Center: PASS en muestra.
- Match Center: FAIL en los dos casos de estado contradictorio; PASS para una previa Tier S muestreada (Bayern-Stuttgart), sin marcador inventado.
- Broken match links: 0 en la muestra auditada; no equivale todavía a auditoría exhaustiva de las 180 entidades.

### SHARK

- `sports_data_available`: YES para catálogo y entidad.
- `shark_evidence_available`: NO/INSUFFICIENT en las muestras.
- `shark_status`: la pantalla mantiene el partido visible y declara evidencia insuficiente.
- Riesgo: el contexto SHARK no bloquea el producto, pero una entidad con estado LIVE incorrecto contamina cualquier razonamiento posterior.

### Frescura

| Señal | Resultado |
|---|---|
| Última actualización del catálogo | 2-3 minutos de edad durante la muestra |
| API-Football live cache | aproximadamente 0-53 segundos en consultas observadas |
| Match start latency | `INSUFFICIENT_SAMPLE` |
| Goal latency P50/P95 | `INSUFFICIENT_SAMPLE` |
| Minute latency P50/P95 | `INSUFFICIENT_SAMPLE` |
| Halftime latency P50/P95 | `INSUFFICIENT_SAMPLE` |
| Fulltime latency P50/P95 | `INSUFFICIENT_SAMPLE` |

Una actualización reciente no prueba corrección: los dos estados LIVE/FT demuestran que frescura de escritura y calidad semántica son métricas distintas.

### API usage y coste

- API-Football daily budget configurado: 100 llamadas.
- Cache-first: activo.
- Match window cache: 6 horas en código.
- Live cache: 55 segundos en código.
- Requests acumuladas/remaining reales: `UNKNOWN`; no se exponen de forma fiable en la evidencia disponible.
- TheSportsDB requests/quota/remaining: `UNKNOWN`.
- The Odds API usage/remaining: `UNKNOWN`.
- Coste deportivo actual real: `UNKNOWN`; no se consultó facturación.
- Gasto nuevo autorizado/ejecutado: **0**.

Hallazgo de control de coste: `GET /api/live` ejecuta `sync_api_football_live_tracker()` y puede consumir proveedor cuando expira el TTL. Durante la auditoría se realizaron dos lecturas de esa ruta antes de confirmar este comportamiento; ambas registraron `external_calls=1`. No se volverá a usar esa ruta para observación cache-only. El resto del gate utilizará `/api/realtime/sports`, `/api/calendar`, `/api/live/state`, logs, DB/caché y HTML público.

Además, los dos estados falsos LIVE mantienen `live_refresh_required=true` en el ciclo deportivo y pueden provocar una llamada live cada tick de cron de cinco minutos. El tracker no aplica por sí mismo el `daily_call_budget` del facade. Esto es un **riesgo de cuota** demostrado por código y estado, aunque el consumo diario acumulado siga siendo desconocido.

## Alertas internas Day 1

| Alerta | Estado | Evidencia | Acción permitida |
|---|---|---|---|
| `BAD_LIVE_STATUS` | ACTIVE | 2 entidades LIVE/FT contradictorias | Preparar corrección para aprobación; no mutar datos durante el gate. |
| `HOME_RELEVANCE_DISTORTION` | ACTIVE | Home muestra ligas menores antes que partidos élite presentes | Observar ventana nocturna y comparar; no cambiar ranking automáticamente. |
| `TIER_REGISTRY_AMBIGUITY` | ACTIVE | al menos 16 falsos Tier S por nombres genéricos | Proponer desambiguación por país/competition_id. |
| `QUOTA_RISK` | ACTIVE | falso LIVE puede disparar tracker cada 5 min; consumo acumulado desconocido | Medir consumo real; no aumentar frecuencia. |
| `PROVIDER_DOWN` | INACTIVE | health PASS, datos y sync recientes | Mantener observación. |
| `DUPLICATE_EXPLOSION` | INACTIVE | 0 duplicados en 180 partidos | Mantener observación. |
| `TIER_S_LIVE_MISSING` | NOT_EVALUABLE | no había Tier S/A claramente live en la ventana | Reintentar durante un partido importante real. |

## Memoria de observación

| Día | Observaciones reales | Tier S/A live evaluable | Resultado |
|---|---:|---:|---|
| 2026-08-28 | 1 baseline + comprobaciones de superficie | 0 | IN_PROGRESS; LIVE y Home con fallos candidatos |
| 2026-08-30 | 1 observación cache-only + Home/Partidos/Directo/Match Center | 0 | IN_PROGRESS; Directo excluye lecturas retrasadas, pero Home y Match Center aún muestran al menos una como LIVE |

Próximas observaciones:

1. DAY 3, 2026-08-31 a las 20:30 Europe/Madrid: repetir cache-only y buscar una muestra Tier S/A realmente en directo.
2. Verificar si Home y Match Center dejan de presentar como LIVE los registros que `/api/realtime/sports` excluye por retraso.
3. DAY 3 será candidato mínimo solo si existe muestra Tier S/A suficiente y coherencia entre superficies.
4. DAY 4-7: continuar si no hubo live importante o la muestra de transiciones sigue siendo insuficiente.

La observación recurrente `Certificación Sports Data LIVE` está activa en este hilo, con una ejecución diaria a las 20:30 Europe/Madrid y un máximo de siete observaciones. No modifica Render ni producción y prohíbe expresamente consultar `/api/live`.

## Corrección P0 local posterior a DAY 1

- **Fecha:** 2026-08-28.
- **Origen:** `LOCAL_QA` y fixtures de regresión `SIMULATED_TEST`.
- **Producción modificada:** NO.
- **Proveedor nuevo:** NO.
- **Llamadas adicionales a proveedor:** 0.
- **Gasto nuevo:** 0.
- **Estado:** corrección local certificada; resolución en producción todavía no observada.

### Causas raíz corregidas

1. Distintas superficies interpretaban por separado señales `LIVE`, estado terminal, minuto y horario.
2. Una señal terminal anidada podía perder frente a una etiqueta `LIVE` superficial.
3. La pertenencia a la tabla/cache live y el minuto podían actuar como evidencia implícita de directo.
4. Tier S/A utilizaba coincidencias parciales con nombres ambiguos.
5. Home heredaba prioridad del feed y señales de betting por encima de importancia deportiva.
6. Match Center podía conservar un tracker live obsoleto aunque la entidad canónica ya estuviera finalizada.
7. UNKNOWN no tenía desglose operativo por frecuencia, país, proveedor y visibilidad en Home.

La solución define una única verdad `MATCH-STATUS-TRUTH-V1`: un estado terminal gana siempre; horario, marcador, minuto o cache no crean LIVE; una fase activa explícita puede ser LIVE aunque no incluya minuto. El minuto solo se muestra cuando está persistido por proveedor y el partido sigue siendo canónicamente live.

### Evidencia antes/después

| Señal | Antes, producción Day 1 | Después, LOCAL_QA | Estado de producción |
|---|---:|---:|---|
| Contradicciones LIVE/FT | 2 | 0/2 fixtures reproducibles renderizados como LIVE | `NOT_REMEASURED`; no deploy |
| Falsos Tier S por nombres genéricos | al menos 16 | 0/16 permanecen en Tier S; 2 quedan Tier B y 14 UNKNOWN | `NOT_REMEASURED`; no deploy |
| UNKNOWN | 130 | 130/130 clasificados en el corpus controlado por frecuencia, país y proveedor; 0 mappings automáticos | El valor real posterior sigue pendiente |
| Minuto inventado | riesgo presente | 0; ausencia de minuto muestra “En directo” | Pendiente de observación real |
| Prioridad Home de los tres casos élite | 0/3 por encima de las ligas menores observadas | 3/3 | Pendiente de observación real |
| Consistencia Home/Directo/Partidos/Match Center | FAIL en 2 entidades | PASS sobre el mismo contrato de estado, score, equipos, kickoff y competición | Pendiente de observación real |

No se han mapeado a ciegas las 130 entidades UNKNOWN. Siguen disponibles en Partidos, se degradan en Home y se exponen de forma compacta en Operations/Founder para priorizar únicamente mappings relevantes.

### Ranking Home local

Orden determinista aplicado:

1. valid live important;
2. favorite important;
3. Tier S/A today;
4. important upcoming;
5. recent important results;
6. standard;
7. low priority;
8. unknown.

La disponibilidad de pick/cuota queda como señal secundaria y no adelanta una competición menor.

| Caso Day 1 | Resultado local |
|---|---|
| Bayern de Múnich - Stuttgart frente a K League 2/Chinese Super League | PASS |
| Lille - Paris Saint-Germain frente a K League 2/Chinese Super League | PASS |
| AC Milan - Venezia frente a K League 2/Chinese Super League | PASS |
| K League 2 y Chinese Super League preservadas en Partidos | PASS; no se borran, solo se relegan en Home |

### QA de la corrección

| Control | Resultado |
|---|---|
| Matriz P0 | 37/37 PASS |
| Pytest completo | 303/303 PASS |
| Py compile / compileall | PASS |
| Jinja | PASS |
| Imports, routes y static | 744 rutas GET; 0 templates/static faltantes |
| Route/link audit | 804 rutas; 0 enlaces rotos; 0 unsafe smoke |
| Flask smoke | 29/29 rutas PASS |
| Sentinel | 39 rutas, 1116 enlaces, 0 incidencias |
| Privacy/Secret Guard | 1089 archivos; 0 findings |
| Browser QA | 111/111 checks; desktop/tablet/mobile |
| Home/Partidos/Directo/Match Center | HTTP 200, 0 JS errors, 0 provider requests, 0 overflow, 0 imágenes rotas |
| Local Safe Browser QA | 22/22 checks; 0 external requests; Telegram/Stripe 0 |
| Mobile LAN Safe | 7/7 PASS |
| `git diff --check` | PASS |

La observación Day 2-7 permanece activa. No se declarará LIVE PASS hasta observar un partido Tier S/A realmente en directo y comprobar la coherencia en producción.

## DAY 2 - Observacion real 2026-08-30

- **Ventana observada:** 22:33-22:40 Europe/Madrid.
- **Origen:** `REAL_PRODUCTION_OBSERVATION`.
- **Produccion modificada:** NO.
- **Endpoint con coste potencial `/api/live`:** NO CONSULTADO.
- **Llamadas adicionales a proveedor:** 0; `/api/realtime/sports` confirmó `no_external_calls=true`.
- **SHA servido:** `4098d1c73921458b863b0ea50eb7812780202745`; el commit solo añade el informe de cierre del día y no cambia la lógica deportiva.
- **Health:** PASS.
- **Errores activos/logs de error:** 0.
- **Resultado:** `REAL_SPORTS_CERTIFICATION_IN_PROGRESS`.

### Estado cache-only

| Señal | DAY 2 | Evidencia |
|---|---:|---|
| synchronized | 800 | `/api/realtime/sports` |
| matches | 62 | contrato realtime cache hit |
| today | 27 | contrato realtime |
| finished | 133 | contrato realtime |
| raw live count | 19 | contratos calendar/live-state |
| confirmed live returned | 0 | array `live=[]` en realtime |
| stale live aggregate | 56 | contador realtime |
| delayed live readings excluded | 19 | mensaje seguro del contrato realtime |
| upcoming | 56 | live-state/calendar |
| with odds | 0 | live-state |
| with picks | 0 | live-state |
| last safe sync | 2026-08-30 22:35 Madrid | runtime/realtime |
| provider errors | 0 | runtime y logs Render |
| highlights stored/videos/embeddable | 0/0/0 | `/api/client/highlights` |
| highlights pending | 18 | contrato de highlights |
| new spend | 0 | ninguna alta ni cambio de plan |

### LIVE truth y consistencia

El contrato cache-only correcto declaró: “No hay directo confirmado; 19 lecturas retrasadas quedan excluidas”. `/live` mostró board vacío, `En directo = 0` y no inventó minuto.

Sin embargo, Home siguió mostrando `19 en directo` y elevó como partido principal a Portland Timbers II - Austin FC II, kickoff 20:00, marcador 0-0 y estado `En directo` a las 22:33-22:35. Match Center para `sportsdb-9c185a90a281810876` mantuvo el mismo estado, “Partido en curso” y un hecho `LIVE - marcador 0-0`, aunque también declaró que la última lectura estaba desactualizada y no tenía minuto.

Resultado DAY 2:

- Directo / contrato cache-only: **PASS seguro**; excluye lecturas retrasadas.
- Home: **FAIL de coherencia**; presenta como LIVE una lectura que el contrato canónico excluye.
- Match Center: **FAIL de coherencia**; conserva LIVE y un evento de estado sobre evidencia desactualizada.
- Match navigation: **PASS**; Home llevó a la misma entidad y marcador.
- Fake minute: **0**; se mostró “En directo” sin minuto.
- FT-as-LIVE reproducido: **0 en esta muestra**; el defecto observado es stale-as-LIVE entre superficies.
- Cross-surface status consistency: **FAIL**.

### Relevancia, cobertura y conocimiento

No hubo un partido Tier S/A confirmado en directo. Los registros raw LIVE visibles correspondían principalmente a MLS Next Pro y competiciones menores; ninguno certifica cobertura live de élite. Home dejó que esas lecturas retrasadas dominaran el primer bloque deportivo.

`/partidos-hoy` conservó catálogo amplio y navegable: 195 partidos y 47 ligas en el HTML observado. El contrato calendar, consultado en otro instante, devolvió 187 visibles, 45 ligas y `database_written=false`; la diferencia temporal no se clasifica como duplicado sin evidencia adicional.

- Tier S/A fixtures: presentes en catálogo (Bundesliga, LaLiga, Ligue 1, Premier League y Serie A), pero no live confirmado.
- Important live observed: 0.
- Home relevance: **FAIL condicionado por live stale**, no por disponibilidad de picks.
- Unknown total: `NOT_EXPOSED` por los contratos consultados; Home mostró al menos tres cards live con “Competición pendiente”.
- Duplicates: `INSUFFICIENT_SAMPLE` en DAY 2.
- Lineups confirmed: 0 en el Match Center muestreado.
- Player IDs from lineup: `INSUFFICIENT_REAL_DATA`.
- Sports events: 0 eventos deportivos profundos; el único hecho fue la etiqueta de estado LIVE.
- Stats: 0 confirmadas.
- Highlights authorized/found: 0; 18 pendientes y 0 almacenados.
- Media rights: sin muestra autorizada nueva; no se infiere derecho de uso.

### Frescura, cuota y coste

- Catálogo/sync: reciente, aproximadamente 0-5 minutos durante la ventana.
- Las 19 lecturas raw LIVE eran semánticamente retrasadas; frescura de sync no equivale a frescura de partido.
- Match start, goal, minute, halftime y fulltime P50/P95: `INSUFFICIENT_SAMPLE`.
- Requests/quota/remaining reales: `UNKNOWN`; no están expuestos de forma fiable.
- Odds disponibles: 0.
- Coste actual real: `UNKNOWN`.
- Gasto nuevo: **0**.

### Comparacion DAY 1 -> DAY 2

| Señal | DAY 1 | DAY 2 |
|---|---|---|
| canonical confirmed live | 0 | 0 |
| important Tier S/A live | 0 | 0 |
| LIVE contradiction | 2 LIVE/FT | 1 stale-as-LIVE reproducido entre Directo y Home/Match |
| fake minute | 0 confirmado | 0 |
| Home relevance | ligas menores sobre élite disponible | live stale domina el primer bloque |
| provider errors | 0 | 0 |
| odds | 0 | 0 |
| highlights/videos | no observados | 0/0 |
| certification | IN_PROGRESS | IN_PROGRESS |

**Pregunta DAY 2:** si hay un partido importante en directo ahora mismo, ¿NeMeSiS lo muestra automáticamente?

**Respuesta:** `NOT_ENOUGH_EVIDENCE`. No hubo Tier S/A confirmado live. Además, Home y Match Center aún presentan como LIVE al menos una lectura que el contrato canónico de Directo excluye por retraso.

## Provider gap matrix provisional

| Capability | Required | Current | Gap | Impact |
|---|---|---|---|---|
| Live score | Alto | PARTIAL | Estados cruzados no reconciliados | Crítico para producto live. |
| Minute | Alto | UNAVAILABLE en muestra | Sin minuto en supuestos directos | Crítico. |
| Events | Medio/alto | UNAVAILABLE en muestra | Sin eventos deportivos observados | Alto para Match Center/SHARK. |
| Fixtures | Alto | OBSERVED | Cobertura amplia; relevancia no fiable | Medio. |
| Results | Alto | PARTIAL | 4/5 y LIVE/FT divergente | Alto. |
| Standings | Medio | NOT_OBSERVED | Falta muestra | Medio. |
| Teams | Alto | OBSERVED | Sin gap en muestra | Bajo. |
| Players | Medio | NOT_OBSERVED | Falta muestra | Medio. |
| Lineups | Medio | NOT_OBSERVED | Falta muestra | Medio/alto en elite. |
| Stats | Alto para SHARK | UNAVAILABLE en muestra | 0 stats live | Alto. |
| Logos | Medio | OBSERVED 180/180 | Sin gap en muestra | Bajo. |
| Odds | Separado | UNAVAILABLE en muestra | 0 cuotas | No bloquea Sports; bloquea Betting. |

## Decisión de inversión provisional

**DO WE NEED TO SPEND MORE: INSUFFICIENT_EVIDENCE**

No se recomienda contratar un proveedor ni cambiar plan antes de:

1. eliminar la contradicción de estados y medir el stack actual;
2. obtener consumo real acumulado y remaining;
3. observar al menos una ventana Tier S/A live;
4. separar necesidad deportiva de necesidad de cuotas.

El problema Day 1 es primero de reconciliación, clasificación y observabilidad. Comprar más datos no garantiza corregirlo.

## Criterio final pendiente

Para cerrar el gate se exige evidencia real de:

- detección y presencia de partido Tier S/A;
- estado/minuto/score coherentes entre proveedor, Home, Directo y Match Center;
- transiciones start/goal/minute/HT/FT cuando el proveedor las soporte;
- Home sports-first sin falsos Tier;
- catálogo completo preservado;
- consumo y riesgo de cuota observables;
- cero datos inventados y cero gasto nuevo no autorizado.

**Pregunta Day 1:** si hay un partido importante en directo ahora mismo, ¿NeMeSiS lo muestra automáticamente?

**Respuesta:** `NOT_ENOUGH_EVIDENCE`. No había un Tier S/A claramente live durante la ventana observada, y los dos registros live disponibles eran inconsistentes y no prioritarios.

## Sports Media + Knowledge Convergence - 2026-08-30

### Production observation

- Evidence origin: `REAL_PRODUCTION_OBSERVATION`, read-only/cache-only.
- Runtime observed: provider stack active, API-Sports configured, The Odds API
  configured and provider cache enabled.
- TheSportsDB highlights surface: active configuration, but 0 persisted
  highlights and 0 videos available in the inspected cache.
- Current TheSportsDB paid plan/capability: `INACCESSIBLE` from the available
  runtime and repository evidence.
- Real Tier S/A highlight sample: 0 events checked with an authenticated provider
  request; no call was added because credential and quota evidence were not
  safely available to this process.
- Current result: `NO_AUTHORIZED_SAMPLE`, not a provider or rights PASS.

### Local convergence certification

| Capability | LOCAL_QA | REAL_PRODUCTION_OBSERVATION |
|---|---|---|
| Lineups -> persisted Player ID | PASS | INSUFFICIENT_REAL_DATA |
| Player -> Team -> Competition -> Match | PASS | INSUFFICIENT_REAL_DATA |
| Events and statistics | PASS with isolated fixture | INSUFFICIENT_REAL_DATA |
| Deterministic summary | PASS, 0 AI calls / 0 unsupported claims | INSUFFICIENT_REAL_DATA |
| Official/authorized video surface | PASS with rights-labelled `SIMULATED_QA` fallback | NO_AUTHORIZED_SAMPLE |
| Unknown-rights video/photo | BLOCKED | Rights gate deployed locally; real sample pending |
| Required attribution missing | FAIL CLOSED | Real sample pending |
| Geo-restricted embed | Authorized-link fallback PASS | Real sample pending |

Browser evidence: 14/14 sports Golden Journey steps, 57 captures, 18 navigation
clicks, 8/8 journeys, 0 console errors, 0 page errors, 0 provider calls and 0
unsafe media visible across desktop/tablet/mobile.

The Sports DAY 2-7 gate remains `REAL_SPORTS_CERTIFICATION_IN_PROGRESS`. No
future day is simulated and no LIVE, lineup, player, event, statistics or
highlight production PASS is inferred from local fixtures.
