# SCALABILITY REPORT

Fecha Madrid: 2026-07-29

Alcance: preparar NeMeSiS para decenas de miles de usuarios sin construir modulos nuevos.

Produccion modificada: false

Commit/push/deploy: no ejecutados

## Executive Summary

- **La escalabilidad actual es suficiente para beta controlada, no para trafico masivo.** La configuracion declarada usa un servicio Flask en Render con gunicorn `--workers 1 --threads 3`, SQLite persistente y cron cada 15 minutos. Esto simplifica operacion, pero concentra CPU, memoria, DB y jobs en un modelo que no debe asumir decenas de miles de usuarios.
- **El primer cuello de botella probable es SQLite por concurrencia y escrituras, seguido por el unico worker web.** Lecturas cacheadas pueden aguantar mucho mas que escrituras, pero pagos, sesiones, eventos, analytics, picks, Telegram y cron generan puntos de bloqueo.
- **El crecimiento debe hacerse por etapas, con presupuestos de rendimiento y limites de operacion.** Antes de migrar arquitectura, hay que medir p50/p95, locks, writes por GET, cache hit rate, errores 5xx y coste de proveedores.

## Configuracion Observada

| Elemento | Valor | Estado |
| --- | --- | --- |
| Runtime local | V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL | LOCAL_ONLY |
| Web server declarado | gunicorn gthread | LOCAL_ONLY |
| Workers | 1 | CONFIRMED_LOCAL_CONFIG |
| Threads | 3 | CONFIRMED_LOCAL_CONFIG |
| Timeout | 90s | CONFIRMED_LOCAL_CONFIG |
| DB | SQLite via `DB_PATH` | CONFIRMED_LOCAL_CONFIG |
| Render DB path | `/data/database.db` | CONFIRMED_LOCAL_CONFIG |
| Cron | `*/15 * * * *` | CONFIRMED_LOCAL_CONFIG |
| Engines locales | 153 archivos | LOCAL_ONLY |
| Tools locales | 610 archivos | LOCAL_ONLY |
| Tests locales | 31 archivos | LOCAL_ONLY |

## Hipotesis De Carga

Estas cifras no son mediciones reales. Son rangos de trabajo para disenar pruebas.

| Escenario | Usuarios | Riesgo dominante | Decision |
| --- | ---: | --- | --- |
| Beta cerrada | 10-50 | UX, soporte, Stripe/Telegram test | Permitido con vigilancia. |
| Beta ampliada | 100-500 | DB locks, latencia, soporte | Requiere metricas y backup/restore. |
| Lanzamiento pequeno | 1k-5k | p95, cache, cron, pagos | Requiere load test y alertas. |
| Escala media | 10k-50k | SQLite, single worker, jobs, proveedores | Requiere redisenar persistencia/colas. |
| Escala alta | 50k+ | multi-region, DB, cache, observabilidad | Fuera de arquitectura actual. |

## Que Romperia Primero

### 1. Base de datos

SQLite es excelente para simplicidad y durabilidad local, pero bajo decenas de miles de usuarios el problema es la escritura concurrente. Los patrones de riesgo son:

- sesiones y preferencias de usuario;
- eventos de User Intelligence;
- pagos y webhooks;
- pick grading;
- Telegram queue/dedupe;
- cron de datos;
- backups mientras hay trafico;
- acciones admin.

Impacto esperado: locks, latencia alta, fallos intermitentes, cron en PARTIAL o respuestas lentas.

### 2. Web service

Un worker con tres threads puede bloquearse si tres requests lentos coinciden. Las rutas con riesgo son:

- Match Center si agrega demasiados contratos;
- Team/Competition/Player Center con datasets amplios;
- SHARK si construye contexto pesado;
- Operations/Developer Center si calcula snapshots grandes;
- admin reports con DB o filesystem.

Impacto esperado: p95 alto, timeouts, 502/503 en picos y peor experiencia movil.

### 3. Jobs y cron

El cron cada 15 minutos es correcto, pero a escala necesita:

- estado de ejecucion atomico;
- dedupe;
- duracion maxima;
- backoff;
- separacion entre sync, Telegram y mantenimiento;
- alerta si no registra tick.

### 4. APIs y fuentes deportivas

La arquitectura ya tiene guards, pero la escala aumenta:

- coste de proveedor;
- riesgo de rate limit;
- stale data si se reduce sincronizacion;
- necesidad de cache multi-capa;
- trazabilidad de licencia y atribucion.

## Presupuestos De Rendimiento Recomendados

| Ruta/flujo | p50 objetivo | p95 objetivo | Error budget |
| --- | ---: | ---: | --- |
| Home | <300 ms cacheado | <1000 ms | 5xx <0.1% |
| Calendar | <500 ms | <1500 ms | 5xx <0.1% |
| Match Center | <700 ms | <2000 ms | 5xx <0.1% |
| Team Center | <700 ms | <2000 ms | 5xx <0.1% |
| Competition Center | <800 ms | <2500 ms | 5xx <0.1% |
| SHARK Intelligence | <800 ms | <2500 ms | 5xx <0.1% |
| Runtime/health | <150 ms | <500 ms | 5xx = 0 |
| Admin Operations | <1000 ms | <3000 ms | 5xx <0.1% |

## Evolucion Tecnica Por Etapas

### Etapa 1 - Sin cambiar arquitectura

- Medir latencia real por ruta.
- Medir writes por request.
- Asegurar 0 escrituras por GET en rutas publicas.
- Activar cache de snapshots para Sports Core.
- Separar jobs lentos de requests.
- Reducir calculos en Operations Center a snapshots.

### Etapa 2 - Endurecer SQLite

- WAL controlado si procede.
- Timeouts y retry seguros.
- Una sola cola de escrituras para eventos no criticos.
- Snapshot read model para pantallas deportivas.
- Backups con checksum y restore drill.

### Etapa 3 - Preparar salida a PostgreSQL

- Definir repositorios de datos por dominio.
- Aislar SQL directo en engines de persistencia.
- Inventariar tablas criticas.
- Crear migracion reversible.
- Mantener SQLite para dev/test si conviene.

### Etapa 4 - Escala web

- Aumentar workers/instances solo tras medir DB.
- Cache externo si la plataforma lo justifica.
- Separar cron/worker del web service.
- Alertas externas.
- Load test en staging.

## Pruebas De Escala Necesarias

| Prueba | Objetivo | Criterio PASS |
| --- | --- | --- |
| Load test read-only | Ver p95 de rutas criticas | p95 dentro de presupuesto, 0 5xx. |
| DB lock simulation | Ver contencion de SQLite | Sin corrupcion, degradacion controlada. |
| Cron overlap simulation | Evitar ejecuciones solapadas | Dedupe y estado correcto. |
| Backup under load | Confirmar copia sin romper app | Backup valido y app responde. |
| Restore drill aislado | Probar recuperacion | RPO/RTO medidos, checksum OK. |
| Provider guard test | No gastar creditos por renders | 0 llamadas externas en paginas. |
| Telegram queue test | Evitar duplicados | Dedupe, limites y skips correctos. |
| Stripe webhook test | Idempotencia y membresia | Un pago test produce una activacion, no duplicados. |

## Decisiones Arquitectonicas Recomendadas

1. Mantener V940 sin nuevas funciones hasta cerrar evidencia de escala.
2. No migrar a PostgreSQL antes de medir, pero preparar el camino.
3. No aumentar workers sin probar locks de DB.
4. No activar pagos reales sin webhook test y soporte.
5. No activar Telegram masivo sin dedupe y limites observados.
6. Separar "dato deportivo fresco" de "pantalla rapida" mediante snapshots.

## Decision

SCALABILITY READINESS: PARTIAL

El producto puede crecer hacia beta, pero no debe asumir decenas de miles de usuarios hasta que existan pruebas de carga, backup/restore y observabilidad externa.
