# V818 Match Lifecycle Automation QA

El job `match_lifecycle_reconciler` mantiene estados limpios:

- Futuro sin marcador: `Proximo`.
- Pasado sin marcador: `Resultado pendiente`.
- Con marcador real: `Finalizado`.
- Live conserva estados live si existen.

El cierre diario reutiliza API-Football si esta configurada y ejecuta grading de picks solo con resultados reales disponibles.
