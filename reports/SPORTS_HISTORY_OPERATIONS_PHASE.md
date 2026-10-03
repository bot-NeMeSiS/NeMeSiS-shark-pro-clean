# Continuación de memoria deportiva: reconciliación y recuperación operativa

Parte de `main` después de las PR #161 y #162. #161 ya estaba fusionada y sus siete workflows terminaron con éxito. Esta continuación reutiliza la navegación contextual de #162.

## Qué cambia

- Enlaces con evidencia entre entidades ya importadas, mediante `reconcile_identity`. Se conservan entidades originales, filas de partidos y detalles. Los redirects permiten que los IDs y enlaces antiguos sigan llegando al registro activo.
- Los partidos equivalentes se cuentan una vez tras reconciliar las identidades. Solo se agrupan con competición, temporada, equipos y kickoff UTC exactos. Diferentes IDs del mismo proveedor, equipos que fueron rivales y resultados finales contradictorios detienen la operación. Toda la reconciliación revierte si hay conflicto.
- Cada enlace conserva fuente, ID externo, destino, referencia de evidencia y snapshot anterior en la auditoría. Es idempotente. No hay coincidencia difusa ni unificación automática de homónimos.
- Backfill ejecutable de una temporada TheSportsDB mediante el transporte ya configurado; exactamente una invocación de transporte por intento. Reutiliza presupuesto, caché y rollback. No añade cron, cambia planes ni ejecuta consultas al renderizar.
- El presupuesto y el resumen de consumo usan días de **Europe/Madrid**, también durante cambios de horario. Las reservas tienen identificador: un trabajo vencido no puede sobrescribir a su sucesor.
- Se rechazan respuestas con competición/temporada distinta y respuestas que no contienen una lista de eventos. Una respuesta de temporada no certifica cobertura completa: puede estar limitada por el acceso del proveedor.
- La importación de clasificaciones existentes vincula el total esperado con su competición, temporada y equipo. V+E+D debe coincidir con jugados, y la muestra debe cuadrar en resultados y en GF/GC cuando están suministrados. Las discrepancias se ven como cobertura parcial.
- El Team Center muestra métricas históricas por competición/temporada mediante relaciones persistidas de partidos. Si apuntan a varias identidades sin reconciliar, no suma los conteos.
- El Match Center recupera eventos reales, alineaciones confirmadas y estadísticas archivadas a través de los componentes existentes. No mezcla capturas estadísticas ni combina proveedores en una alineación. Las cachés actuales tienen prioridad. No restaura picks privados ni permisos de media desde el histórico.
- Rachas y ventanas cronológicas excluyen partidos sin zona horaria confirmada; siguen contando resultados finales reales en los totales por temporada y explican la limitación temporal.
- Admin muestra nombres deportivos, evidencia de reconciliación y errores cerrados sin mensajes del proveedor que puedan exponer credenciales.

## Operación explícita

Vista previa (sin abrir la base, modificar archivos o llamar a proveedores):

```text
python tools/backfill_sports_history.py --database <base-existente> --league-id 4335 --season 2025-2026 --max-calls-per-day 1
python tools/reconcile_sports_history.py --database <base-existente> --kind team --source the_odds_api --external-id <id-revisado> --canonical-id <id-destino> --evidence <referencia-verificada>
```

`--execute` ejecuta el trabajo seleccionado contra la base explícita, que debe existir. La reconciliación no obtiene evidencia de nombres: la referencia tiene que proceder de una revisión real de los IDs. La importación local existente también reconstruye cobertura a partir de clasificaciones y enlaza detalles mediante todos los aliases internos conservados.

El endpoint de temporada y sus parámetros se verificaron en la [documentación oficial TheSportsDB](https://www.thesportsdb.com/docs_api_guide) y la [referencia del endpoint](https://thesportsdb.readme.io/reference/geteventsbyseason). No se asume que un plan concreto permita recuperar toda la temporada.

## Límites

No se han ejecutado reconciliaciones ni llamadas deportivas contra producción. No se modifica `DB_PATH`, secretos, usuarios, sesiones, membresías, pagos, Stripe, Telegram ni configuración de planes. El transporte sigue usando la configuración existente. Esta PR no se fusiona automáticamente.

Estadios y árbitros mantienen sus contratos preparados y la navegación contextual existente; esta continuación no crea rutas públicas nuevas. Cuotas y highlights siguen sujetos al permiso de retención y a las superficies autorizadas existentes.

## Validación

70 pruebas locales pasan: memoria histórica, operaciones nuevas, Match Center, Sports Core, Resultados/Calendario y navegación contextual. Las 34 pruebas específicas de memoria/operaciones se incluyen en CI mediante `unittest`.

Casos nuevos cubiertos: reconciliación posterior a la importación, rollback de conflictos, homónimos y tipos, datos originales conservados, aliases de URLs, reinicios y relevo de workers, medianoche de Madrid, caché de temporada, respuestas fuera de scope, preview sin efectos, clasificación incoherente, GF/GC discordantes, recuperación de eventos/alineaciones/stats, capturas separadas, ausencia de publicación de picks y fechas sin zona horaria.
