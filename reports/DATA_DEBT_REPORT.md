# Data Debt Report

Estado: `AUDITED_READ_ONLY`. No se ha eliminado ninguna tabla, fila, base, memoria ni evidencia.

## Fuente de verdad

- Producción: `DB_PATH=/data/database.db`, disco persistente del web service.
- Local Safe: base exclusiva bajo `data/local_dev/`.
- Continuous Evolution producción: `/data/continuous_evolution_os`.
- Configuración: variables de entorno son autoridad para rutas runtime; `render.yaml` documenta el contrato y no sustituye la realidad de Render.

## SQLite local auditada

La inspección se abrió con URI SQLite `mode=ro`.

| Métrica | Resultado |
|---|---:|
| Tamaño de `data/database.db` local | 3.481.600 bytes |
| Tablas de aplicación | 61 |
| Índices | 116 |
| Tablas sin referencia textual en código | 0 |
| Tablas con dos referencias textuales | 3 |

Candidatas de baja referencia, no candidatas de borrado: `automation_health_events`, `data_memory_retention_runs`, `shark_context_snapshots`. Pueden tener SQL dinámico, tareas programadas o consumidores externos; requieren trazado de lecturas/escrituras y backup/restore aislado antes de cualquier decisión.

## Deuda de runtime versionado

Git contiene 316 archivos bajo `data/runtime`: 193 Markdown y 123 JSON, aproximadamente 149,6 MB. Incluyen workers, Sentinel, historiales y snapshots. No se han desversionado en este cierre porque parte de la UI y varios engines los consumen como evidencia, y no existe aún una prueba de release limpio que demuestre comportamiento equivalente sin ellos.

Clasificación:

- `ACTIVE_REQUIRED`: últimos estados y memorias leídos por Founder/Operations/Sentinel.
- `RUNTIME`: historiales de ejecuciones que deberían vivir en storage persistente, no en el paquete.
- `HISTORICAL`: evidencia antigua que debe conservarse fuera de caminos críticos.
- `UNKNOWN`: cualquier fichero sin trazado completo; no se elimina.

## Hallazgos

1. Código, runtime y evidencia histórica comparten `data/runtime`; esto dificulta distinguir seed, memoria y salida regenerable.
2. La base real está correctamente separada por `DB_PATH`, pero no todas las memorias auxiliares usan todavía `/data` en producción.
3. El repositorio ignora DB/WAL/SHM y `data/local_dev`, evitando subir usuarios QA o datos locales nuevos.
4. La Product Memory de Continuous Evolution ya dispone de raíz separada y persistente en producción.
5. No hay evidencia suficiente para declarar tablas obsoletas; borrar por nombre sería inseguro.

## Plan no destructivo

1. Inventariar caller y writer de cada fichero de `data/runtime`.
2. Definir por contrato `SEED`, `PERSISTENT_RUNTIME`, `QA_ONLY` o `HISTORICAL`.
3. Migrar solo `PERSISTENT_RUNTIME` a `/data/<namespace>` con lectura dual temporal y test de restart.
4. Exportar históricos fuera del release con manifiesto e integridad.
5. Certificar un paquete limpio sin `data/runtime` en un entorno aislado.
6. Tratar cualquier limpieza de tablas como sprint separado con backup, restore aislado, métricas e aprobación explícita.

## Decisión

`NO_DESTRUCTIVE_DATA_CHANGE`. La deuda está identificada; la capacidad y el historial prevalecen sobre una reducción estética del árbol.
