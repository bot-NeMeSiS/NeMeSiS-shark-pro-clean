# V935 Match Lifecycle QA

La taxonomia canonica admite y prueba: `UPCOMING`, `LIVE`, `HALFTIME`, `FINISHED`, `RESULT_PENDING`, `POSTPONED`, `CANCELLED`, `ABANDONED`, `INCOMPLETE` y `ARCHIVED`.

Reglas verificadas:

- Pasados fuera de proximos.
- Finalizados fuera de live.
- Live limitado a `LIVE/HALFTIME`.
- Resultados limitados a `FINISHED/ARCHIVED`.
- Incidencias separadas de la agenda valida.
- Incompletos fuera de KPIs y cliente.
- IDs, fuente y hora Madrid preservados.
- Archivado clasifica sin borrar registros.

La DB local no contiene partidos reales evaluables; los contadores locales permanecen en cero de forma honesta.
