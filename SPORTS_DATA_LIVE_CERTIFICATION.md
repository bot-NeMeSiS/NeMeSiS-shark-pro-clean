# NeMeSiS SHARK PRO - Sports Data Quality + LIVE Certification

## Estado ejecutivo

**CERTIFICATION: REAL_SPORTS_CERTIFICATION_IN_PROGRESS**

- Gate: observación real de 3-7 días naturales.
- Inicio: 2026-08-28.
- Evidencia registrada: DAY 1 baseline + DAY 2 + DAY 3 (dos ventanas) + DAY 4 (2026-09-07) + DAY 5 (2026-09-08). No se afirma que sean fechas consecutivas ni dias certificados PASS.
- Producción observada: `https://bot-apuestas-crgf.onrender.com`.
- Último SHA de producción observado: `c6eaa003e6ae0e9d4af7d98198ec6eefafc97b04` (DAY 5, 2026-09-08 22:33:49 y 22:37:56 Madrid, demostrado por `/api/runtime-version`).
- Compras/gasto iniciados por el monitor: **0**. Coste total real: **UNKNOWN**.
- Cambios de producción: **0**.
- Ranking modificado durante el gate: **NO**.
- Resultado provisional: catálogo y sincronización operativos. El seguimiento DAY 3 observó un candidato Tier S marcado LIVE por el proveedor y priorizado por Home, además de su exclusión automática al quedar stale. La coherencia temporal real del partido no quedó suficientemente demostrada para cerrar LIVE.
- La contradicción histórica `Desactualizado` frente a `100/100 Alta` no se reprodujo en el SHA actual: Match Center mostró confianza no probabilística y degradó el estado a `Actualización pendiente` durante la ventana stale. El fallo histórico se conserva como evidencia y no se reescribe como PASS retroactivo.
- DAY 4 repite la transicion de evidencia reciente a stale: el candidato Udinese-Lazio deja de publicarse como LIVE y el indice del detalle baja de 93/100 a 49/100. No certifica que el partido estuviera realmente en curso: faltan minuto y coherencia temporal independiente. Home autenticada no comprobada sin sesion.

No se declarará PASS por el mero transcurso de tres días. Debe existir una muestra real de partidos Tier S/A en directo con coherencia verificable entre estado, tiempo, proveedor, Home, Directo y Match Center.

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

## DAY 3 - Observación real 2026-09-06

- **Ventana observada:** 00:10-00:17 Europe/Madrid.
- **Origen:** `REAL_PRODUCTION_OBSERVATION`, lectura pública y cache-only.
- **SHA servido:** `fddbeea3b1205e2f05e62bcf95630a7a4c85a4cd`.
- **Referencia antigua de la automatización:** `354453071b0ca1b76c6263c1f1818182fd088e12`; queda superada para observaciones futuras.
- **Health:** PASS; `active_errors_count=0`.
- **Logs Render:** no reconsultados porque no existe workspace seleccionado en la integración y no se eligió uno sin confirmación.
- **Endpoint con coste potencial `/api/live`:** NO CONSULTADO.
- **Cambios de producción:** 0.

### Estado cache-only

| Señal | DAY 3 | Evidencia |
|---|---:|---|
| synchronized | 800 | `/api/realtime/sports` |
| realtime matches | 222 | contrato cache hit |
| today | 187 | contrato realtime |
| confirmed live | 0 | `live=[]` |
| stale live | 0 | agregado realtime |
| no external calls | true | contrato realtime |
| last safe sync | 2026-09-06 00:10 Madrid | contrato realtime |
| calendar visible | 193 | `/api/calendar` |
| Tier S / Tier A | 13 / 4 | IDs y aliases canónicos del calendario |
| UNKNOWN | 176 | calendario; degradados fuera de Tier S/A |
| status conflicts | 0 | calendario |
| duplicate ID/tuple groups | 0 / 0 | calendario |
| missing crests | 0 | 193 partidos |
| live-state | 0 live, 233 upcoming, 56 finished, 6 suspended | `/api/live/state` |
| highlights stored/authorized | 0 / 0 | `/api/client/highlights` |

Los universos realtime, calendar y live-state tienen filtros y momentos distintos; sus
totales no se comparan como si fueran el mismo contador.

### Superficies públicas

- Home: HTTP 200, `0 en directo`, 186 hoy y 79 destacados.
- El primer bloque deportivo mostró Arsenal-Chelsea, Juventus-AC Milan,
  Everton-Manchester United y Valencia-Barcelona: la muestra sí prioriza Tier S/A.
- Directo: HTTP 200, estado vacío seguro y 0 partidos LIVE; no mostró próximos como directos.
- Partidos: HTTP 200, 193 visibles, catálogo amplio y enlaces Match Center.
- Match Center muestreado: Arsenal-Chelsea, misma identidad, competición, estado
  `Próximo` y horario Madrid `15:30`; no inventó marcador ni minuto.
- Navegación pública: Home/Directo/Partidos enlazan al mismo Match Center muestreado.

### Hallazgo de confianza

El Match Center muestreado declara simultáneamente:

- frescura `Desactualizado`;
- evidencia `Datos insuficientes`;
- y un `Índice de Confianza NeMeSiS 100/100 Alta`.

Esto es una contradicción real de presentación de confianza. No implica un falso LIVE,
pero bloquea el cierre de calidad: evidencia obsoleta o insuficiente no debe recibir
`100/Alta`. El candidato local Sports Truth contiene un endurecimiento específico para
este caso; esta observación no lo certifica en producción porque el SHA servido sigue
siendo `fddbeea3...`.

### Cobertura deportiva

- Important Tier S/A LIVE observed: 0.
- Minute/events/lineups/stats LIVE: `INSUFFICIENT_SAMPLE`.
- El único hecho del Match Center fue el estado `PROGRAMADO`; no certifica eventos deportivos.
- Alineaciones, H2H, clasificación y estadísticas del partido muestreado: no disponibles.
- Player IDs desde alineación: `INSUFFICIENT_REAL_DATA`.
- Highlights encontrados/autorizados: 0/0; no hay media visible sin derechos.
- Match start, goal, minute, halftime y fulltime P50/P95: `INSUFFICIENT_SAMPLE`.
- Requests, quota y remaining reales: `UNKNOWN`.
- Coste actual real: `UNKNOWN`; no se consultó facturación.
- Acciones nuevas con coste iniciadas: 0.

**Resultado DAY 3:** `REAL_SPORTS_CERTIFICATION_IN_PROGRESS`.

No hubo partido Tier S/A realmente LIVE, por lo que DAY 3 no cierra el gate. La verdad
LIVE fue coherente en la muestra (`0` en realtime, Home, Directo, calendario y Match
Center), Home mostró prioridad deportiva correcta y no se reprodujo un falso directo.
Queda abierta la contradicción de confianza `Desactualizado` frente a `100/Alta`.

**Pregunta DAY 3:** si hay un partido importante en directo ahora mismo, ¿NeMeSiS lo
muestra automáticamente?

**Respuesta:** `NOT_ENOUGH_EVIDENCE`. No existía una muestra Tier S/A LIVE confirmada
durante la ventana.

Próxima observación: mantener el gate hasta obtener un Tier S/A LIVE real. Usar como
baseline de producción `fddbeea3...` o el SHA que el runtime demuestre en ese momento,
no la referencia histórica `354453...`.

### Seguimiento DAY 3 - 2026-09-06 22:34-22:42 Madrid

Esta ventana pertenece a la misma fecha natural que DAY 3 y **no crea un DAY 4**.

- **Origen:** `REAL_PRODUCTION_OBSERVATION`, endpoints públicos cache-only y HTML servido.
- **SHA servido:** `8ab59a16b6dd0ae69727547c78709d012b4d3fb7`.
- **Health:** HTTP 200, `ok=true`, `active_errors_count=0`.
- **Render MCP/logs:** no utilizados; la integración no tenía workspace previamente seleccionado.
- **Endpoint `/api/live`:** NO CONSULTADO.
- **Llamadas nuevas a proveedor:** 0; `/api/realtime/sports` declaró `no_external_calls=true`.
- **Cambios de producción, ranking, cron o datos:** 0.

Fotografía consolidada de las 22:42 Madrid:

| Señal | Resultado | Evidencia |
|---|---:|---|
| synchronized | 800 | `/api/realtime/sports` |
| realtime matches / today | 26 / 26 | snapshot cache-only |
| confirmed live / stale live | 22 / 0 | snapshot posterior a sync 22:40:35 |
| finished | 139 | agregado realtime |
| calendar visible | 181 | `/api/calendar` |
| Tier S / Tier A | 4 / 0 | contrato `sports-relevance-v2` |
| UNKNOWN | 177 | siguen degradados respecto a Tier S/A |
| status conflicts | 0 | calendario |
| duplicate IDs | 0 | calendario |
| missing crests | 0 | calendario |
| live-state visible | 12 | colección pública resumida; no se equipara al universo realtime |
| important LIVE candidate | 1 | Juventus-AC Milan, Italian Serie A, Tier S |
| minute | no disponible | no se inventó minuto |
| highlights returned | 1 | existencia observada; autorización no inferida solo por el contador |

#### Transición de frescura observada

1. Con evidencia recién sincronizada, Juventus-AC Milan apareció como LIVE con marcador
   `0-1`, sin minuto inventado. Home y Directo lo colocaron primero, por delante de
   competiciones UNKNOWN; Partidos conservó el enlace al mismo Match Center.
2. Al expirar la evidencia, realtime pasó temporalmente a `0 live / 22 stale` y
   `/api/live/state` a `0`. Home y Directo retiraron el fixture del catálogo LIVE.
   Match Center mostró `Actualización pendiente`, frescura `Desactualizado`, confianza
   no probabilística y ninguna etiqueta `En directo`.
3. Tras la siguiente sincronización cacheada, el fixture reapareció de forma coherente
   en Home, Directo, Partidos y Match Center. No se observó FT como LIVE ni un minuto
   derivado del horario.

Esta transición aporta evidencia positiva para los dos contratos obligatorios:

- un LIVE confirmado por el proveedor y reciente se publica;
- el mismo LIVE deja de publicarse cuando su evidencia queda stale.

No obstante, el fixture no cierra todavía la certificación real: a las 22:42 Madrid el
proveedor seguía informando `2H` para un kickoff mostrado a las 18:45 y no entregaba
minuto. El gate no infiere FT por horario, pero tampoco convierte esa señal temporalmente
anómala en prueba independiente de un partido realmente en curso. Minute, events,
lineups, stats y latencias de gol/descanso/final siguen en `INSUFFICIENT_SAMPLE`.

**Resultado del seguimiento:** `REAL_SPORTS_CERTIFICATION_IN_PROGRESS`.

**Respuesta operativa:** cuando el proveedor presentó el candidato Tier S como LIVE y
reciente, NeMeSiS lo puso automáticamente primero. **Respuesta de certificación real:**
`NOT_ENOUGH_EVIDENCE` hasta observar un Tier S/A LIVE con contexto temporal coherente y
profundidad deportiva suficiente en una fecha natural posterior.

Próxima observación: DAY 4 solo puede comenzar en otra fecha natural. Mantener lectura
cache-first y comprobar de nuevo Tier S/A, minuto real, eventos, lineups, stats,
frescura y coherencia entre Home, Directo, Partidos y Match Center.

## DAY 4 - 2026-09-07: observacion real cache-first

**Origen: REAL_PRODUCTION_OBSERVATION. Estado: REAL_SPORTS_CERTIFICATION_IN_PROGRESS.**

Ventana: 22:33:12-22:38:33 Europe/Madrid (20:33:12-20:38:33 UTC).
Nueva fecha natural respecto a DAY 3; no se reinicia la certificacion ni se
rellenan fechas intermedias sin observacion. No es un DAY 4 PASS.

### Identidad y limites de acceso

- Runtime servido a las 22:34:28 y al cierre: `4df7fc20e3de9cbe84d2098f3d6b3a74577631f5`.
  Version `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL`;
  `version_files_match=true`, `active_errors_count=0`.
- `/api/health`: HTTP 200 y `ok=true`. No se equipara liveness a calidad deportiva.
- `deployment_alignment_status=aligned_local_files` no demuestra por si solo
  alineacion con GitHub. No se consulto remoto ni se publico nada en esta ventana.
- Render MCP: `get_selected_workspace` no tiene workspace seleccionado.
  No se eligio uno ni se consultaron recursos/logs: `EXTERNAL_BLOCKER_RENDER_LOG_ACCESS`.
- `/app`: HTTP 302 a `/cliente-login?next=/app`; sin sesion autorizada,
  **HOME AUTENTICADA NO COMPROBADA**. No hubo login, bypass ni creacion de usuarios.
- `/`, `/partidos`, `/live` y el Match Center se leyeron como HTML publico.
  No se ejecutaron JS, clicks, capturas de navegador ni pruebas visuales.
- `/api/live`, sync, cron, test-send, pagos y endpoints de accion: NO CONSULTADOS.
  Los endpoints deportivos utilizados declaran `no_external_calls=true` o
  `external_calls=0`/`no_render_api_call=true`. No se llamo a un proveedor.

### Fotografias de cache, sin equiparar universos diferentes

| Instante Madrid | Superficie y universo | Evidencia |
| --- | --- | --- |
| 22:34:02 | Realtime cache | 800 sincronizados; 41 matches; 5 today; 91 finished; LIVE 0; stale_live 0; picks 0. Ultimo safe sync 22:30:34. |
| 22:34:03 | Calendar | 124 matches visibles; primer resultado prioritario Cagliari-Lecce 1-0 Final y despues Getafe-Celta 1-1 Final. |
| 22:36:29 | Calendar tras actualizacion automatica existente | 145 visibles; 26 today; 21 LIVE; 91 finished; 102 incidents; 84 leagues. Snapshot `7de48919b79740e6`, sync 22:35:12. |
| 22:36:29 | Tier de los 145 visibles | S=4, A=2, B=3, UNKNOWN=136; IDs duplicados=0; filas sin alguna URL de escudo=0. URL presente no demuestra descarga/render del escudo. |
| 22:36:29 | Sports quality, universo operativo | 47 Tier S/A available; 16 surfaced; UNKNOWN=531; live_conflicts=0; stale=0. No son denominadores del catalogo de 145. |
| 22:37:22 | Realtime al caducar la evidencia | LIVE 0; stale_live 21 excluidos; 41 matches y 5 today; 800 sincronizados. Mismo ultimo sync 22:35:12. |

La diferencia 124 -> 145 coincide con la entrada de 21 lecturas LIVE recientes;
la posterior exclusion no se interpreta como 21 partidos finalizados. El monitor
no provoco sincronizacion ni altero la frecuencia del sistema.

### Candidatos importantes y coherencia entre superficies

| Fixture persistido | Tier | Kickoff Madrid | Marcador y senal reciente, 22:36 |
| --- | --- | --- | --- |
| `sportsdb-de83edbe35bff4534c`, Udinese-Lazio | S | 18:45 | LIVE, 1-0, minuto no disponible |
| `sportsdb-3923bfceb3bc7633cb`, Elche-Real Sociedad | S | 19:30 | LIVE, 0-1, minuto no disponible |
| `sportsdb-8bc71a11a5cf17ff0a`, Sabadell-Cordoba | A | 18:30 | LIVE, 2-1, minuto no disponible |
| `sportsdb-a985a1c92e44c1ff40`, Estoril Praia-Arouca | A | 19:15 | LIVE, 0-0, minuto no disponible |

Los cuatro usan `MATCH-STATUS-TRUTH-V2`: edad LIVE 77 s, reloj
`last_synced_at`, `status_conflict=false`, sin inferir LIVE desde minuto,
marcador u horario. Esa frescura demuestra recepcion reciente, no que la
actividad deportiva descrita sea actual. Los kickoffs llevan mas de tres horas
sin minuto que contraste el estado: **CONTEXTO TEMPORAL NO CERTIFICADO**.
No se infiere FT ni se inventa una correccion de marcador.

- `/live` a las 22:36:32 muestra primero esos cuatro candidatos S/A, con sus
  marcadores y enlaces canonicos, antes del ejemplo Tier B Palermo. Hay evidencia
  positiva de orden importante en Directo, no una certificacion de Home autenticada.
- `/partidos` contiene los mismos IDs y conserva el catalogo amplio. Los dos
  resultados S observados (Cagliari-Lecce y Getafe-Celta) siguen Final, no LIVE.
- Match Center de Udinese-Lazio a las 22:36:33: mismo ID/equipos/competicion,
  score 1-0, LIVE, 18:45 Madrid; minuto ausente. Ningun minuto estimado observado.
- A las 22:37:21 ese detalle muestra `Actualizacion pendiente` y `Desactualizado`;
  el indice pasa de 93/100 Alta a 49/100, sin 100/100 ni 93/100 residuales.
  El bloque de calidad mantiene confianza no probabilistica.
- A las 22:38:31 `/live` ya no enlaza ese candidato. No se equiparan otros enlaces
  de la pagina a partidos LIVE sin comprobar su seccion/estado.
- `/` publico se leyo solo despues de la caducidad; sus enlaces a proximos no
  demuestran ni descartan como ordenaba un LIVE reciente. `/app` queda pendiente.

**CONFIDENCE STALE CHECK:** la contradiccion 100/Alta frente a stale no se
reprodujo en el detalle muestreado. La marca Alta 93 durante la recepcion fresca
no certifica minutos, eventos o cobertura completa; el propio desglose concede
solo 8/15 a evidencia de estado. Queda por contrastar esa etiqueta global cuando
el proveedor vuelve a entregar un estado deportivamente dudoso pero recien recibido.

### Sports Knowledge, SHARK y Media

- Match observado: no alineacion confirmada, sin Player IDs desde alineacion,
  sin estadisticas, H2H ni clasificacion confirmados. Es carencia de muestra,
  no ausencia de esas capacidades en todo el producto.
- Cronologia: un registro `LIVE - marcador 1-0`, con `Minuto no disponible`.
  Es una instantanea de estado, **no** prueba de un gol/evento deportivo ni de
  latencia de eventos. No se cuenta como cobertura de goles/tarjetas/sustituciones.
- Resumen servido afirma partido en curso desde esa senal. Su concordancia con
  el estado cacheado no verifica independientemente la realidad del encuentro.
- SHARK: contenido insuficiente/no disponible, sin completar senales deportivas
  ausentes. No se ha certificado analisis LIVE real.
- `/api/client/highlights`, HTTP 200: stored_media_total=0, highlights_total=0,
  authorized=0, blocked=0, with_video=0; centro available=0, embedded=0,
  pending_matches=14. No hay muestra autorizada visible que certificar.
- El contador de highlight del seguimiento DAY 3 no se reescribe: hoy los
  contadores explicitos son cero. No se deduce borrado, perdida ni fallo de derechos.
- Fotos/jugadores, cuotas/mercados actuales y cuota/remaining de proveedores:
  **NO COMPROBADO / INSUFFICIENT_REAL_DATA**. API-Sports declara disponible y
  sincronizacion conocida en runtime; no acredita cobertura de alineaciones/eventos.

### Comparacion, coste y siguiente observacion

Se repite el patron DAY 3: las senales recientes se publican y se retiran al
quedar stale. La muestra cambia de un candidato S a cuatro candidatos S/A,
pero sigue faltando contexto independiente de un partido realmente LIVE.
No se convierte el mero cambio de SHA ni esta transicion en SPORTS LIVE PASS.

P50/P95 de start, goal, minute, halftime/fulltime y porcentajes de cobertura:
**INSUFFICIENT_SAMPLE**. La respuesta aislada de highlights tardo 17.166 s;
es una advertencia de consulta, no P95 ni regresion confirmada. No hubo sondeos
intensivos para reproducirla. Todas las respuestas obtenidas fueron 200 salvo
la redireccion esperada de `/app` (302); esto no certifica todo el servicio.

Coste real actual y facturacion: **UNKNOWN**. Gasto/contrataciones iniciados por
este monitor: 0. Sin cambios de codigo, rankings, produccion, cron, usuarios,
membresias, proveedores, Telegram, Stripe o pagos. Solo se actualiza este informe.

**Siguiente observacion:** conservar DAY 1-4; continuar en una fecha posterior
o ventana deportiva util con el SHA que demuestre runtime. Buscar evidencia
coherente Tier S/A, minuto/eventos/lineups/stats; mantener Home autenticada y
logs como limites de acceso. No cerrar por transcurso del tiempo.

**Si existe un partido importante LIVE, Home lo muestra automaticamente?**
`NOT_ENOUGH_EVIDENCE`: Directo lo priorizo bajo senal reciente; Home autenticada
no se pudo observar y la realidad LIVE independiente sigue sin certificarse.

## DAY 5 - 2026-09-08: recepcion reciente, caducidad y confianza

**REAL_PRODUCTION_OBSERVATION. REAL_SPORTS_CERTIFICATION_IN_PROGRESS.**

Ventana: 22:32:13-22:37:56 Europe/Madrid (20:32:13-20:37:56 UTC).
Nueva fecha natural; se conservan DAY 1-4, sin reinicio ni PASS por tiempo.
SHA servido verificado a las 22:33:49 y 22:37:56:
`c6eaa003e6ae0e9d4af7d98198ec6eefafc97b04`. Las lecturas de las 22:32 preceden
a la primera extraccion registrada del SHA; no se afirma un deploy observado.
Runtime: V940, version_files_match=true, active_errors_count=0.
Health: 200 / ok=true a las 22:32:14; no equivale a calidad deportiva.
Render MCP: sin workspace seleccionado; no se eligio uno ni se leyeron logs.
Se mantiene EXTERNAL_BLOCKER_RENDER_LOG_ACCESS.

Solo HTML publico y GET cache-first permitidos. `/app`: 302 a login,
HOME AUTENTICADA NO OBSERVADA. Sin sesiones, JS, clicks, screenshots ni
descargas de escudos. La preparacion inicial del lector fallo por dependencia
local ausente antes de hacer peticiones; se uso el parser estandar sin instalar.
No se consultaron `/api/live`, refresh, sync, cron, test-send, pagos ni proveedores.
Realtime declara no_external_calls=true; Calendar external_calls=0,
database_written=false y no_render_api_call=true. Son declaraciones del contrato,
no una auditoria interna de todas las escrituras de las paginas.

### Muestras y universos

| Hora Madrid | Superficie | Evidencia |
| --- | --- | --- |
| 22:32:55 | Realtime | 800 sincronizados; 41 matches; 5 today; 68 finished; LIVE 0; stale_live 72; picks 0; sync 22:30:20. |
| 22:33:01 | Live/state | live=0, with_odds=0, with_picks=0. Finished=149 pertenece a otro universo que los 68 de hoy. |
| 22:33:57 | Calendar, 110 visibles | S=2, A=2, B=1, UNKNOWN=105; 46 ligas; IDs duplicados=0; ausencia de URL de algun escudo=0. No se verifico render de imagenes. |
| 22:33:57 | Snapshot ea57fe5153affa0f, metricas operativas | 48 Tier S/A available; 14 surfaced; UNKNOWN=509; live_conflicts=0; stale=72. No son denominadores del catalogo visible. |
| 22:35:54-57 | Home publica, Directo, Partidos | Tras sync existente: LIVE=72, hoy=77; Partidos conserva 182 visibles; cuatro candidatos S primero. |
| 22:36:43 | Realtime | LIVE=72; stale_live=0; matches=113; today=77; sync 22:35:26. Cuatro primeros: edad 80 s, last_synced_at 22:35:23. |
| 22:37:52-55 | Detalle, Directo, Home publica y realtime | Detalle degradado; Home/Directo sin nodos canonical LIVE; realtime LIVE=0/stale_live=72, mismo sync 22:35:26. |

El monitor no provoco la sincronizacion. 0 -> 72 -> 0 NO equivale a inicios o
finales de 72 partidos. Recepcion reciente no demuestra actualidad deportiva.
UNKNOWN 509 frente a 531 DAY 4 no prueba mappings: cambian fecha y muestra.

### Identidad, relevancia, LIVE y minuto

| ID canonico | Partido | Tier/senal | Score | Kickoff Madrid |
| --- | --- | --- | --- | --- |
| sportsdb-2493c5ae907fbde626 | Porto-Manchester City | S, HALFTIME | 0-0 | 19:00 |
| sportsdb-beb6ca5e2d9c975562 | Borussia Dortmund-Villarreal | S, HALFTIME | 0-0 | 19:00 |
| sportsdb-ca847aa0254b6311f2 | Real Madrid-Inter de Milan | S, HALFTIME | 2-0 | 19:00 |
| sportsdb-c49c85fb56868252da | Lille-Real Betis | S, HALFTIME | 2-1 | 19:00 |
| sportsdb-8b9f47662e66fc1eea | AEK Athens-LASK | S, FT | 1-0 | 16:45 |
| sportsdb-a766c8b19ddefee728 | Club Brugge-Aston Villa | S, FT | 2-3 | 16:45 |
| sportsdb-80e218ea207dbca1fa | Platense-Fluminense | A, RESULT_PENDING | Ausente | 22:00 |
| sportsdb-bf432a2d0eec1f65f3 | Santa Fe-Vasco da Gama | A, RESULT_PENDING | Ausente | 22:00 |

Los cuatro en descanso aparecen primero en Home publica y Directo, antes de
Blackburn-Sheffield United, y conservan enlaces en Partidos. Minuto=null en
los cuatro, sin minuto inventado observado. Decision MATCH-STATUS-TRUTH-V2,
sin inferir LIVE por horario/score/minuto. Los ceros recibidos se conservan;
Platense/Santa Fe conservan score ausente. HALFTIME a las 22:36 con kickoff
19:00 necesita contraste independiente; no prueba futbol en juego ni permite
inferir FT. IMPORTANT LIVE REAL: NOT_ENOUGH_EVIDENCE.

AEK-LASK detalle: Finalizado 1-0, misma competicion/hora que Calendar,
canonical LIVE=false. No se observa FT como LIVE en esa muestra.
Porto detalle 22:37:14: Descanso 0-0, canonical LIVE=true. A las 22:37:52:
mismo ID/score, Actualizacion pendiente, Desactualizado, canonical LIVE=false.
A las 22:37:53-54 su enlace desaparece de Home publica/Directo. Exclusion
agregada=72; trazado individual de detalle=1, NO 72/72 detalles certificados.

### Hallazgos productivos; no autocorreccion

1. RELATO_STALE_AMBIGUO: Porto conserva en resumen "tienen un partido
   programado" al caducar la senal de descanso, pese al header Actualizacion
   pendiente. No prueba reprogramacion. El pendiente local A/B ahora tiene
   reproduccion productiva concreta; no se modifico Summary Truth ni la UI.
2. CONFIANZA_GLOBAL_REQUIERE_REVISION: Home publica y Directo muestran
   100 / Alta para los cuatro candidatos recientes. Porto detalle muestra
   100/100 Alta pese a contexto deportivo insuficiente y ausencia de minuto,
   lineup/stats/H2H/forma confirmados. El indice mide calidad, no probabilidad;
   esa aclaracion no demuestra actualidad deportiva independiente. El gate
   de confianza suficiente NO queda certificado. Al quedar stale baja a
   49/100 Insuficiente: NO se reproduce 100/Alta en el detalle ya stale.
   Platense sin marcador confirmado muestra 93/100 Alta, otro limite semantico.
3. PROCEDENCIA_POR_CONTRASTAR: payload y resumen citan TheSportsDB; el pie
   de los detalles dice Fuente Api Football. No demuestra llamadas a ambos
   ni segunda verificacion. Falta trazar la atribucion por campo.

Son evidencias para revision, no autorizaciones de cambio. No se atribuyen
automaticamente al ultimo commit ni se declara regresion funcional global.

### Knowledge, media, cuota y continuidad

- Detalles AEK, Platense y Porto: sin lineup confirmada, sin Player IDs
  enlazados desde alineacion, stats/H2H/clasificacion no confirmados.
  Hay enlaces a equipos, sin clicks ni certificacion del journey completo.
- Timeline llama "Evento confirmado" a una instantanea de estado/resultado;
  no acredita gol, tarjeta, sustitucion ni latencia de eventos deportivos.
- SHARK declara falta de senales suficientes/frescas. No se certifica analisis
  LIVE real ni se transforma preparado/conectado en cobertura.
- Highlights, 22:33:18, 200: almacenados=0, encontrados=0, autorizados=0,
  bloqueados=0, videos=0; pendientes=24. INSUFFICIENT_REAL_DATA para derechos
  y video autorizado, no fallo global de rights. Ningun iframe en los detalles.
- Odds: no cuotas reales en realtime, with_odds/with_picks=0 en estado leido.
  Cuota/remaining, errores por proveedor y coste real: UNKNOWN. Los flags
  provider_available/last_sync_known no acreditan plan ni peticion exitosa.
- Highlights tardo 17,031 s (17,166 s DAY 4): advertencia repetida de consulta,
  no P95 ni causa determinada. Respuestas obtenidas 200 salvo 302 de `/app`;
  no se audito todo el servicio ni se hicieron sondeos intensivos.

DAY 4 -> DAY 5: mismo patron de recepcion y caducidad; 72 senales frente a 21
no demuestran empeoramiento por contar universos distintos. Home PUBLICA
tiene nueva evidencia de prioridad; autenticada sin acceso. El relato stale
ya se reproduce en produccion. Sigue faltando Tier S/A LIVE independiente.
P50/P95 de inicio, gol, minuto, descanso/final y cobertura porcentual:
INSUFFICIENT_SAMPLE. No hay muestra de transiciones deportivas para medirlos.
Coste real total UNKNOWN; compras/cobros/planes iniciados 0. Solo se actualiza
este documento; sin codigo, rankings, produccion, cron, tareas, proveedores,
Telegram, Stripe, secretos ni datos reales modificados por el monitor.

Siguiente observacion: DAY 6 en fecha natural posterior con SHA comprobado;
preservar DAY 1-5 y priorizar minuto/fase coherentes, procedencia y confianza.
La revision del relato requiere el encargo separado; este monitor no la aplica.
Home ante futbol importante LIVE REAL: NOT_ENOUGH_EVIDENCE. Bajo la senal
reciente del feed, Home publica SI priorizo los cuatro y SI los retiro al
caducar. No se declara LIVE PASS ni cierre de la certificacion.

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
