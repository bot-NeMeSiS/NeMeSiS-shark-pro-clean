# Memoria deportiva histórica y entidades

Base: `main` después de #159 (`a2946691`). Los cinco workflows del head de #159 terminaron con éxito; la PR ya estaba fusionada al iniciar esta fase.

## Comportamiento

- Tablas aditivas `sports_history_*` en la conexión seleccionada por el código existente. No cambia `DB_PATH`, secretos ni configuración de proveedores. Ningún histórico se elimina por ausencia en una respuesta.
- Guardado desde la frontera de escritura del cron diario existente y el warehouse. Reejecutar una importación actualiza el mismo partido. Un resultado final confirmado sobrevive a respuestas programadas o sin marcador; una corrección final completa puede actualizarlo.
- IDs tipados y delimitados por proveedor. Competiciones enlazadas mediante el registro existente `IMPORTANT_COMPETITIONS`. Equipos/jugadores requieren enlaces explícitos para compartir identidad entre proveedores; los nombres de Odds sin IDs quedan como identidades pendientes. No hay coincidencia difusa ni fusiones por parecido.
- El partido se deduplica entre fuentes cuando competición, temporada, equipos con IDs enlazados y kickoff UTC exacto coinciden. Cambios de horario se resuelven por el ID del proveedor. Conflictos requieren revisión, no se fusionan automáticamente.
- Métricas por temporada/competición: resultados confirmados, V/E/D, GF/GC, ventanas 5/10/20, casa/fuera, racha y H2H. `jugados = V+E+D` siempre en la muestra contabilizada. Finales sin marcador se registran como faltantes de resultado, nunca como 0–0.
- Cobertura completa exige evidencia explícita, total esperado compatible y todos los resultados contabilizables. La ausencia de evidencia se muestra como parcial; los faltantes desconocidos siguen siendo desconocidos. Se muestran discrepancias cuando el total esperado es inferior al conocido.
- Match Center usa resultados estrictamente anteriores al kickoff; ofrece temporadas anteriores. Admin Memoria expone cobertura, faltantes, fuentes, enlaces, sincronización, estados de backfill y consumo persistente. Ambos usan el mismo componente Jinja y los filtros Madrid existentes.
- Entidades de competición/temporada/equipo/jugador/estadio/árbitro/partido y fichas `entity_card` con procedencia. Detalles relacionados: alineaciones, eventos, estadísticas, picks/resultados, cuotas y highlights. Alineaciones sin confirmación no salen del contrato de presentación. Cuotas/media nuevos requieren permiso explícito de retención; no se descarga vídeo.
- El campo de alineaciones, sistema táctico y timeline profesionales existentes se reutilizan. Esta fase no infiere goles, tarjetas, faltas, cambios, VAR ni penaltis; conserva los eventos suministrados y prepara contratos locales para estas superficies.

## Backfill y recuperación

`backfill_page` ejecuta una página a través de un callback de transporte autorizado, con caché persistente, transacción por página y presupuesto diario por fuente. Una reserva se registra antes de llamar; errores consumen presupuesto y quedan en Admin sin mensajes del proveedor que puedan contener secretos. El registro de consumo no desaparece al cambiar de día. El callback debe efectuar exactamente una llamada y desactivar reintentos automáticos. El TTL permite reintentar una reserva abandonada después de expirar.

Los adaptadores puros normalizan respuestas reales TheSportsDB y The Odds API. Odds no aporta temporada ni IDs de equipos: no se inventan. Para backfill de una temporada se debe aportar una temporada y enlaces verificados al adaptador; no se afirma cobertura completa a partir de una ventana reciente.

Importar cachés disponibles, sin red:

```text
python tools/import_sports_history.py --database <base-seleccionada> --input <cache.json> --provider sportsdb
python tools/import_sports_history.py --database <base-seleccionada> --input <normalizados.json> --provider normalized
python tools/import_sports_history.py --database <base-seleccionada> --import-existing
```

La recuperación local recorre el warehouse anterior y `matches`; relaciona detalles existentes solo cuando el ID corresponde inequívocamente a un partido. Devuelve las filas que necesitan revisión. No se ha ejecutado contra la base de producción.

## Límites operativos explícitos

No se activa un nuevo cron ni se amplían planes o endpoints. El transporte de backfill queda en la frontera de trabajo autorizado, nunca en render. Las temporadas no disponibles según la licencia o el acceso actual siguen parciales. Los IDs de equipos de Odds sin evidencia necesitan reconciliación explícita; se conserva el dato separado mientras tanto. Las fichas y detalles son contratos reutilizables, no nuevas rutas públicas para estadios/árbitros. Admin muestra muestras de hasta 100 scopes/IDs y 30 trabajos/días; no representa una auditoría exhaustiva de toda la base.

Usuarios, sesiones, membresías, pagos, Stripe, Telegram y planes de proveedores no se modifican.

## Validación

Pruebas nuevas: conteos y ventanas, cero real frente a marcador desconocido, terminal protegido y correcciones, dedupe con enlaces, homónimos separados, temporadas y corte temporal, cobertura 5 esperados/2 disponibles, detalle confirmado y permisos de retención, caché/presupuesto durable, rollback de páginas fallidas, lectura sin escritura, integración warehouse y frontera de snapshot, adaptadores sin inferencias y componente parcial.

Además se ejecutan regresiones existentes de Match Center, Sports Core y Resultados/Calendario. No se consulta ningún proveedor deportivo en las pruebas.
