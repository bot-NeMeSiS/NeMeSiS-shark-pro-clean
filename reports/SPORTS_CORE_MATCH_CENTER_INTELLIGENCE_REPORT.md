# Sports Core - Match Center Intelligence

## Estado ejecutivo

- Estado local: `PASS`
- Runtime preservado: `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL`
- Contrato reutilizado: `MATCH-CENTER-LIFECYCLE-STORY-V1`
- Produccion modificada: `false`
- Push, commit y deploy: no realizados
- Datos reales de produccion certificados: no; este sprint se ha validado con almacenamiento temporal y fixtures QA aislados

## Funcionalidad incorporada

El Match Center consume un unico `MatchContext` y presenta, cuando existen en el almacenamiento local:

- estado, marcador, competicion, jornada y hora Madrid;
- equipos, escudos y banderas disponibles;
- estadio, ciudad, arbitro y temporada extraidos del payload persistido;
- cronologia completa, ordenada y deduplicada por hecho deportivo;
- goles, tarjetas, sustituciones, penaltis, VAR, periodos, prorroga y tanda;
- estadisticas comparadas procedentes exclusivamente del tracker persistido;
- contexto SHARK construido con calidad, flujo, presion y estado de campo ya calculados;
- enlaces seguros hacia equipo, competicion y jugador.

Cuando falta evidencia se muestra `No disponible`. Las estadisticas y SHARK se ocultan si la lectura live esta stale. Los eventos confirmados pueden conservarse como historia, acompañados por la limitacion de frescura.

## Integraciones

- SQLite: el tracker del detalle abre la DB en `mode=ro` y `query_only`.
- Render: no se altera configuracion, runtime ni comando de inicio.
- SHARK: no se invoca IA ni proveedor; solo se presenta contexto deportivo cacheado y verificable.
- Telegram: no se envia ni se modifica nada.
- Membresias y pagos: sin cambios.
- Developer Center y Company Board: reciben la capacidad `Match Center Intelligence` desde el registro compartido.
- Roadmap: el hito queda completado por evidencia de archivos y tests, no por una cifra manual.
- Sentinel y AutoPilot: una mutacion del contrato abre una incidencia P1 y exige aprobacion humana.

## Rendimiento y efectos

Medicion local de 20 cargas completas de `/match/v944-ready`:

- primera carga: `107.71 ms`
- mediana: `31.14 ms`
- p95: `48.84 ms`
- minimo: `19.53 ms`
- maximo: `107.71 ms`
- respuesta: `47,567 bytes`
- respuestas: `20/20 HTTP 200`
- llamadas externas durante Browser QA: `0`
- llamadas a proveedores durante render: `0`

El hash SHA-256 de la DB temporal antes y despues de las seis cargas Browser QA fue identico:

`A5E2CFA03C7D6798D2ACFF5C65CB3533C9D7D90355E3195E0E577A5305510377`

Esto demuestra que el GET del Match Center no escribe en la DB del escenario validado.

## QA

- `py_compile`: PASS
- `compileall app.py engines tools`: PASS
- Jinja: `188` plantillas parseadas
- pytest: `92/92` PASS
- contrato V940 Calendar: PASS
- contrato V944 Match Center: PASS
- Madrid Time: PASS
- Secret/Privacy Guard: `1,001` archivos, `0` hallazgos confirmados
- imports/rutas: PASS
- Sentinel: `10.0/10`, `0` incidencias
- navegacion: `707` rutas, `956` enlaces, `0` rotos, `0` bucles

Browser QA:

- perfiles: desktop `1366x768`, tablet `834x1194`, movil `390x844`
- escenarios: contexto completo y datos parciales
- capturas: `6`
- HTTP 200: `6/6`
- overflow horizontal: `0`
- CLS: `0`
- errores de consola: `0`
- errores de pagina: `0`
- respuestas 5xx: `0`
- navegacion cliente/admin mezclada: `0`
- literales `None`, `null` o `undefined`: `0`
- capturas no vacias: `6/6`

Evidencia: `browser_qa/SPORTS_CORE_MATCH_CENTER_INTELLIGENCE/`.

## Preparacion de centros futuros

- Team Center reutiliza la ruta existente.
- Competition Center y Player Center tienen contratos de navegacion seguros.
- Mientras no exista informacion real suficiente, ambos responden con un estado honesto y nunca con un enlace roto.
- No se han creado Team Center, Competition Center ni Player Center paralelos.

## Riesgos y limitaciones

- La validacion usa fixtures QA locales; no certifica cobertura, frescura ni completitud de proveedores en produccion.
- Las rutas futuras de competicion y jugador son contratos de continuidad, no centros funcionales completos.
- Telegram, Stripe y membresias no se han probado porque permanecen fuera del alcance.
- La revision visual se apoya en Playwright, DOM, consola, CLS y analisis de pixeles; el visor interno de archivos estuvo bloqueado por ACL.
- Produccion y Render permanecen sin certificar para este cambio hasta que exista autorizacion de integracion y despliegue.

## Estado del Sports Core

`MATCH_CENTER_INTELLIGENCE_READY_LOCAL`

El Sports Core dispone ya de un Match Center factual, cache-only, responsive y protegido contra datos inventados, stale presentado como actual, duplicados de eventos, escrituras GET y llamadas externas durante el render.
