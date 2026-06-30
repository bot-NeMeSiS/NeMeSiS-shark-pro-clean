# V866 Sentinel copy visual review

## Objetivo
Cerrar o corregir los avisos low de copy detectados por Sentinel sin ocultar problemas reales.

## Resultado
- Los 19 avisos low eran candidatos genéricos por `None/null/undefined`.
- Tras revisar la regla, se corrigió el detector para diferenciar HTML visible de tokens internos.
- No se detectan incidencias abiertas en el run V866.

## Copy reforzado
- Picks sin cuota: `Cuota pendiente`.
- Picks sin selección: `Selección pendiente`.
- Picks incompletos: `Pick en revisión`.
- Proveedor sin respuesta: `Proveedor sin datos ahora mismo`.

## No realizado
- No se hizo deploy.
- No se enviaron Telegram reales.
- No se probaron pagos reales.
