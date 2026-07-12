# V935 Pick Lifecycle And Historical QA

Estados probados: `DRAFT`, `INCOMPLETE`, `REVIEW`, `APPROVED`, `PUBLISHED`, `LIVE`, `WON`, `LOST`, `VOID`, `CANCELLED`, `EXPIRED` y `ARCHIVED`.

Un pick cliente exige partido completo, mercado, seleccion, cuota mayor que 1, timestamp, fuente y lifecycle compatible. Picks vencidos, placeholders y cuotas invalidas quedan bloqueados.

El historico solo considera evaluables `WON/LOST/VOID` con cuota y stake validos. Los no evaluables se cuentan por separado y no contaminan ROI, winrate ni picks cerrados. La lectura del resumen es SQLite read-only y no crea tablas durante GET.

La DB local segura contiene 0 picks publicables, 0 evaluables y 0 no evaluables; no se generaron ejemplos visibles.
