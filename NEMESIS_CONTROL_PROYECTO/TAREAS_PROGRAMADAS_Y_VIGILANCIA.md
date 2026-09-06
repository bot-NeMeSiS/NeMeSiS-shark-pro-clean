# Tareas Programadas y Vigilancia

## Produccion observada en solo lectura

| Elemento | Estado | Evidencia |
|---|---|---|
| Web service NeMeSiS | LIVE | Render, deploy `fddbeea3`; disco `/data` y DB declarada `/data/database.db` |
| `telegram-auto-tick` | ACTIVE | Comando `python tools/render_cron_master_tick.py`; cadencia real `*/5 * * * *`; sin cambios |
| Ultima ejecucion observada | SUCCESS | 2026-09-05 20:55:35 UTC |
| Master runner | PASS | HTTP interno 200 y `overall=PASS`; esto acredita el job, no la cobertura deportiva |
| Continuous Evolution | PASS / NOT_DUE | HTTP 200, `SKIPPED_NOT_DUE`; politica sin cambios |
| Telegram | PASS / OLD_MATCH | HTTP 200, resultado `OLD_MATCH`; esta sesion no inicio envios |
| Sports pipeline | PARTIAL | `provider_authenticated=false`, plan `INACCESSIBLE`, deep calls 0, muestra previa PARTIAL |
| Error de proveedor | ACTIVO OBSERVADO | Runtime informa limite diario alcanzado; no se hizo llamada adicional para comprobarlo |
| Logs de error | 0 EN MUESTRA | Sin entradas level=error entre 20:30 y 21:00 UTC para web/cron |

`api_sports_provider_available=true` en runtime significa configurado/habilitado,
no acceso operativo certificado. La evidencia del mismo instante no permite
declarar cuota, autenticacion ni cobertura PASS.

## Conversaciones y tareas

- Esta tarea de Codex se renombro y verifico como
  `NeMeSiS 01 - Desarrollo con Codex (C21)`.
- Los chats historicos C20, C19, C18, C17, C16, C14, C13 y C03 fueron leidos de
  forma acotada y su mapa privado quedo fuera del repositorio.
- La herramienta actual no puede renombrar chats ni el proyecto de ChatGPT.
- Se localizaron dos conversaciones con titulo `NeMeSiS Production Watch`; solo
  la mas reciente es el monitor real. La otra trata Match Intelligence y no debe
  confundirse con una tarea programada.
- Solo se encontro una configuracion local de automatizacion:
  `certificaci-n-sports-data-live`, heartbeat ACTIVE a las 20:30 Madrid con siete
  ocurrencias. Se preservo sin cambios.
- No se localizaron IDs/configuraciones verificables de las nueve tareas
  historicas. Sus renombrados quedan `PENDIENTE_MANUAL`; no se borraron,
  recrearon ni duplicaron tareas.

## Nombres pendientes de aplicar con ID real

| Actual historico | Propuesto | Estado |
|---|---|---|
| `NeMeSiS Production Watch` | `NeMeSiS - Alertas de produccion` | PENDIENTE_MANUAL; monitor real identificado, automatizacion no accesible |
| `NeMeSiS Daily Audit` | `NeMeSiS - Resumen diario y prioridades` | PENDIENTE_MANUAL |
| `Sports Reality Watch` | `NeMeSiS - Verificacion deportiva real` | PENDIENTE_MANUAL |
| `Competitor Intelligence` | `NeMeSiS - Lunes: competencia y experiencia` | PENDIENTE_MANUAL |
| `Sports API Watch` | `NeMeSiS - Martes: APIs, cobertura y costes` | PENDIENTE_MANUAL |
| `AI Opportunity Watch` | `NeMeSiS - Miercoles: IA e innovacion util` | PENDIENTE_MANUAL |
| `Platform Security Watch` | `NeMeSiS - Jueves: seguridad y plataforma` | PENDIENTE_MANUAL |
| `Commercial Readiness` | `NeMeSiS - Viernes: clientes y lanzamiento` | PENDIENTE_MANUAL |
| `NeMeSiS Weekly Board` | `NeMeSiS - Domingo: balance y plan semanal` | PENDIENTE_MANUAL |

Los textos completos `02_TAREAS_NOMBRES_Y_PROMPTS.txt` y el ZIP
`NEMESIS_ORGANIZACION_Y_CONTINUIDAD_2026-09-05.zip` no estaban disponibles en
el workspace ni en adjuntos accesibles. No se sustituyeron por prompts inventados.

## Vigilancias permanentes

- FT/terminal nunca LIVE.
- Lecturas LIVE stale fuera de Home, Directo, Calendario y Match Center.
- Un solo score, estado, identidad y hora Madrid por `match_id`.
- Un write de DB, lectura de cache o `updated_at` generico no puede rejuvenecer
  el ultimo dato valido del proveedor.
- No minuto inferido.
- No llamadas de proveedor durante render.
- Quota/rate-limit y errores del proveedor.
- Master tick, Product Memory, Founder Brief y Prepared for Codex.
- Distinguir fallo del monitor de caida real; reintento limitado y contraste de deploy/reinicio.
- Diferenciar cuota agotada, auth, rate limit, cobertura, red y no comprobado.
- Separacion cliente/admin, secretos, 5xx y errores JavaScript.
- `/api/live` no debe usarse como monitor repetitivo mientras pueda activar
  sincronizacion; priorizar DB, cache, gateway y logs.

## Acciones automaticas permitidas

- Observar, comparar, analizar, priorizar y generar informes/propuestas.
- Ejecutar QA local y read-only de produccion.
- Persistir estado propio de Continuous Evolution dentro de su contrato aprobado.

## Aprobacion obligatoria

- Push y deploy.
- Modificar servicios, cron o variables de Render.
- Envio real de Telegram.
- Stripe live, cambios de precio o cobros.
- Gasto, campanas, publicaciones y acciones irreversibles.
