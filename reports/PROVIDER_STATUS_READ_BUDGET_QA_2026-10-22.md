# Lectura acotada del estado API-Sports — candidato de revisión

Fecha: 22 de octubre de 2026, Europe/Madrid.

Base: `30f638d262bb89d45cfb2aa38cd98bf6988a19b5` (V978).
Rama: `fix/provider-status-read-budget`.
Alcance: mejora aislada para revisión. Este informe no certifica un despliegue.

## Problema y resultado

El lector de estado reutilizaba conexiones SQLite con la espera predeterminada
y absorbía errores de consultas individuales. Una base bloqueada o ilegible podía
terminar representada como una caché vacía y válida. Una ruta inexistente podía
crear una base vacía. Además, varias consultas sin una transacción compartida
podían observar versiones diferentes de los datos.

El candidato consulta el estado local con un presupuesto cooperativo compartido
de 300 ms, apertura de solo lectura y una única instantánea. Solo publica los
contadores y metadatos si termina toda la lectura. Un fallo conserva valores
desconocidos y un código de diagnóstico seguro; un cero comprobado sigue siendo
cero. La explicación, el JSON de administración, SHARK y el diagnóstico runtime
consumen esta distinción.

## Contrato de lectura

| Estado | Significado | Contadores y tablas | `ok` |
|---|---|---|---|
| `READY` | Lectura completa y comprobada | Enteros y lista; una tabla opcional ausente aporta cero | `true` |
| `NOT_REQUESTED` | Consulta de configuración sin leer almacenamiento | `null` | `true`, por compatibilidad con el uso de configuración |
| `NOT_INITIALIZED` | El archivo de almacenamiento no existe | `null`; el lector no lo crea | `false` |
| `READ_UNAVAILABLE` | Bloqueo, agotamiento del presupuesto o fallo local | `null`; se descarta cualquier resultado parcial | `false` |

- `read_error` contiene exclusivamente un código estable: `storage_busy`,
  `read_budget_exhausted`, `storage_unavailable` o `storage_not_initialized`.
- `last_error` sigue siendo el error histórico del proveedor leído de la base.
  No se rellena con una excepción local, rutas o credenciales.
- La configuración del proveedor permanece independiente de la disponibilidad
  de la lectura local.
- Se conservan `max(fixtures_index, live)`, la precedencia de metadatos y los
  contadores conocidos del contrato anterior.
- El endpoint de administración mantiene la autorización antes de consultar y
  usa una sola instantánea para datos y explicación.
- El runtime completo muestra «Estado local sin comprobar» cuando corresponde;
  no anuncia «Sin errores registrados» a partir de una lectura que falló.

## Implementación y alcance

El motor usa URI SQLite `mode=ro`, `query_only`, `BEGIN`, un catálogo de tablas
leído una vez y un plazo basado en reloj monotónico. Las esperas de bloqueo
reciben únicamente el tiempo restante; el manejador de progreso interrumpe SQL
costoso. La conexión se cierra también si una consulta falla.

Archivos funcionales: `engines/api_sports_provider_engine.py`, cambios puntuales
en `app.py` y `templates/admin_api_sports_audit.html`. Se añaden dos módulos de
pruebas y este informe. No se cambian los lectores de partidos cacheados ni las
operaciones de sincronización del proveedor.

## Validación del candidato

Resultado total de los módulos seleccionados: **162 pruebas aprobadas**, en dos
ejecuciones aisladas con el harness adecuado a cada módulo.

Corrida principal: **151 pruebas aprobadas, cero fallos, errores u omisiones**, en
71,124 s. Python 3.12.14, pytest 9.1.1, dependencias de `requirements.txt`,
Playwright 1.56.0 y Chromium 141. Datos SQLite sintéticos y desechables,
con el límite de aislamiento LOCAL SAFE activo. `BOUNDARY_EVENTS []`.

| Módulo | Pruebas aprobadas |
|---|---:|
| `test_api_sports_status_read_truth.py` | 24 |
| `test_api_sports_status_consumers.py` | 20 |
| `test_api_usage_read_truth.py` | 34 |
| `test_admin_realtime_stats_coverage.py` | 2 |
| `test_realtime_cache_performance_safety.py` | 24 |
| `test_directo_realtime_http.py` | 35 |
| `test_shark_safe_mode_notice.py` | 1 |
| `test_shark_membership_limits_v941.py` | 11 |

Las 35 pruebas de Directo incluyen navegación y actualización en Chromium real,
con servidor de localhost y datos de prueba; no son una prueba de producción.
Las pruebas nuevas cubren archivos ausentes/corruptos, rutas con espacios y `#`,
ceros comprobados, fallo parcial, cierre de conexión, instantánea WAL coherente,
presupuesto compartido, permisos, reutilización de lectura y estados visibles.

El caso de bloqueo usa otro hilo con un bloqueo `EXCLUSIVE` real: el lector debe
terminar antes de liberar ese bloqueo. La tolerancia de dos segundos permite
variaciones del entorno de prueba; no constituye una medición de latencia de una
página ni sustituye el presupuesto cooperativo de 300 ms.

Comando reproducible desde la raíz del repositorio, con `NEMESIS_QA_CHROMIUM`
apuntando al ejecutable de Chromium disponible en el entorno:

```bash
python -B tools/check_local_candidate.py \
  tests/test_api_sports_status_read_truth.py \
  tests/test_api_sports_status_consumers.py \
  tests/test_api_usage_read_truth.py \
  tests/test_admin_realtime_stats_coverage.py \
  tests/test_realtime_cache_performance_safety.py \
  tests/test_directo_realtime_http.py \
  tests/test_shark_safe_mode_notice.py \
  tests/test_shark_membership_limits_v941.py
```

Evidencia de la corrida principal:
`data/local_dev/candidate-13f2f19908e2404d834b237e301e560b/result.xml`.
SHA-256: `5f7792c127503a92b671ca0f76e4117aec90ceb94ee0e72ada90633af501796f`.
Los artefactos temporales de ejecución no se añaden al repositorio.

### Reproducción del defecto en la base

Se cargó el motor original de `30f638d` en un módulo temporal, sin modificar el
candidato. **Los nueve casos de regresión seleccionados fallaron en la base**.
Entre los resultados observados: creación de una base inexistente, base corrupta
marcada como válida, publicación de resultados parciales, ausencia de `mode=ro`,
instantánea mezclada `(6, 3, 3, 5)` frente a `(5, 3, 2, 4)`, presupuesto ignorado
y espera hasta la liberación del bloqueo. Los casos correspondientes pasan con
el candidato.

Selector de regresión sobre `tests/test_api_sports_status_read_truth.py`:

```text
missing_database or unreadable_storage or partial_query_failure or success_uses_read_only or reader_keeps_one_snapshot or total_read_budget or exclusive_lock
```

La reproducción carga el archivo original mediante `git show
30f638d:engines/api_sports_provider_engine.py`, lo importa como módulo temporal y
lo sustituye únicamente en el proceso de prueba. No reemplaza el archivo del
candidato. Resultado observado: nueve fallos esperados, salida 1.

### Incidencias del entorno de prueba

Una corrida preliminar no fue verde y no se usa como certificación. Cuatro
fallos de la plantilla provenían de una fixture nueva que omitía `usage_guard`;
se completó la fixture sin rebajar las aserciones. Ocho casos de navegador no
pudieron abrir sockets en el sandbox; se ejecutaron correctamente con permiso
para el navegador y localhost, manteniendo el aislamiento de LOCAL SAFE.

La prueba existente del endpoint programado de deportes usa pytest directo, como
el patrón de `tests/conftest.py` y la copia disponible de `nemesis-smoke.yml`:
LOCAL SAFE bloquea intencionadamente `/api/automation/` antes de entrar al handler.
No se modifica ni desactiva ese bloqueo en el producto. El módulo
`tests/test_sports_data_pipeline_reality.py` se ejecutó por separado con un
entorno explícito sin credenciales heredadas, `DB_PATH` temporal, jobs y Telegram
desactivados, y una barrera adicional de auditoría: **11/11 aprobadas**, cero
fallos, errores u omisiones, en 2,432 s. Incluye el endpoint cron con su respuesta
200 y evidencia saneada. Se observaron cero intentos de red, subprocesos,
conexiones SQLite o escrituras fuera del temporal; las cinco bases usadas eran
sintéticas. La primera preparación del harness rechazó el log por defecto de
pytest en `/dev/null` antes de ejecutar pruebas; se ubicó el log en el temporal.

Evidencia auxiliar: `/tmp/nemesis-pipeline-ci-od4rknvl/`, con `result.xml`,
`summary.json`, el harness aislado y la reproducción del rojo. SHA-256 del JUnit:
`c2e351a10345d490eb207394b0eba4733ee3806dbd38845d8d5b66f64175c914`.

## Revisión y convivencia con otros cambios

Una revisión independiente del código detectó una inconsistencia del diagnóstico
runtime superior. Se corrigió y se añadieron cuatro casos sobre el endpoint
completo; la revisión posterior dio el hallazgo por cerrado. No se identificó
otra regresión concreta en esa revisión estática.

Se revisaron los parches de 14 PR abiertos. Ninguno cambiaba este motor ni sus
funciones de estado. Hay propuestas relacionadas con sincronización y Sports
Truth en otros bloques de `app.py`, por lo que la futura integración debe
compararse con el `main` vigente. El trabajo local no publicado de otro entorno
no es observable desde este candidato.

## Límites y siguiente paso

- Los 300 ms son un presupuesto cooperativo de SQLite, no un límite estricto de
  tiempo de I/O, planificación del sistema o duración de toda una página.
- No se ha demostrado que este lector causara el timeout histórico de `/directo`;
  este candidato no declara resuelto aquel episodio ni cuantifica una mejora de
  rendimiento en producción.
- La evaluación cubre las pruebas seleccionadas y la revisión descritas; no es
  una certificación global de toda la plataforma.
- La rama queda preparada para un PR en borrador. Integrar requiere revisar el
  candidato contra la base vigente y sus checks. Este trabajo no modifica
  `main`, la versión, despliegues, horarios, secretos, pagos ni datos reales.
