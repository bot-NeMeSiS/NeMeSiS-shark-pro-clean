# Data

DATA-001 BLOCKED por evidencia/acceso, CX-DATA-01 BACKLOG. No nuevo proveedor.

## Cadena existente

Origen -> adaptador/Gateway -> almacen -> Sports Truth -> entidad -> contexto -> vista.
`services/sports_service.py` contiene observador interno SE-01 mode=ro.
`engines/historical_warehouse_engine.py`, `engines/football_data_warehouse_engine.py`
y `engines/shark_historical_intelligence_engine.py` ya existen; no son tres
integraciones nuevas autorizadas. Sus conexiones deben probarse por consumidor.

| Fuente | Evidencia actual | Lo que NO demuestra |
|---|---|---|
| TheSportsDB | Adaptador/almacen observados historicamente y SIMULATED_QA SE | Plan/cuota/derechos actuales ni cobertura LIVE completa |
| API-Sports/API-Football | Tracker/facade existentes; metadata no disponible corregida SE | Clave configurada != autenticacion; cuota agotada previa no prueba estado actual |
| The Odds API | Integracion de cuotas existente | Relevancia deportiva no depende de ella; presupuesto actual no consultado |

Observado, recibido y persistido son relojes distintos; leer no rejuvenece.
NULL conservado; 0-0 confirmado real. Resultado historico confirmado no hereda
automaticamente TTL LIVE. No cambios de estado ni certificacion por inferencia;
sin acceso a DB real.

## Piloto pendiente

Propuesta historica, NO aprobada: extracto saneado de TheSportsDB, LaLiga 4335,
temporada 2026-2027, maximo 10 fixtures; doble importacion futura en QA para
identidad/dedupe/correcciones, solo tras autorizacion y derechos establecidos.
Si no hay derechos/retencion establecidos, NO ejecutar ni etiquetar como REAL.
Fuente, terminos, atribucion, limites y presupuesto deben quedar fechados.

## Retencion e higiene

Los 317 tracked bajo data/ se retienen como RUNTIME/configuracion persistida
pendiente de distinguir por consumidor. No son 317 archivos borrables.
No leer DB de usuarios/pagos, secretos ni ampliar retencion real.
[Backup existente](../../DATA_BACKUP_RUNBOOK_V743.md) no prueba un restore nuevo.
Inventario privado por ruta/hash; no nuevo datastore.
