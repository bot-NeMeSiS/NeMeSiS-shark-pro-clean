# V930 Real Data Presentation QA

## Puertas de datos

- Picks visibles requieren partido, mercado, selección y cuota reales.
- ROI y winrate solo se calculan con picks cerrados evaluables.
- Marcador, minuto, resultado y eventos solo aparecen si están confirmados.
- Las rutas de cliente no realizan llamadas externas durante render.
- DB/caché/última sincronización se traducen a copy comprensible para cliente; el diagnóstico técnico queda en admin.

## Evidencia

- DB Browser QA: temporal.
- Llamadas a proveedores externos: 0.
- Telegram enviado: false.
- Pagos ejecutados: false.
- Cifras de demostración de las referencias: 0 encontradas en templates activos.
- Gráficas ROI falsas: 0.
- Partido fallback ficticio: 0.

Cuando faltan datos, la pantalla mantiene su estructura con un estado seguro y una acción útil; no rellena con ejemplos.
