# V927 Desktop Reference Audit

## Entradas revisadas

- `reference_images/reference_manifest.json` y 16 capturas de referencia.
- Reportes V925/V926 y reportes visuales existentes.
- `visual_fix_queue.json` y `reference_gap_report.json`.
- Plantillas y CSS de home, cliente, deportes y admin.

## Hallazgos

Las referencias comparten una cabecera corta, una unica fila de KPIs, filtros pegados al contenido, grids densos de dos o tres columnas, tablas compactas y un panel lateral con la siguiente accion. La app V926 ya tenia la base correcta, pero varias pantallas seguian acumulando capas historicas, cards altas y filtros separados del estado del proveedor.

## PC_DESKTOP_REFERENCE_RULES_V927

1. El contenido principal empieza en el primer viewport de escritorio.
2. La zona superior conocida queda limitada por el guard V927.
3. Cada KPI tiene label, valor, hint y accion cuando procede.
4. Admin presenta KPIs, operaciones, siguiente accion y tablas compactas.
5. Cliente presenta resumen deportivo, accesos y siguiente accion.
6. Deportes presenta filtros, fuente, sync, cache y empty state seguro arriba.
7. Las acciones criticas no quedan escondidas tras espacio muerto.
8. Cliente y admin mantienen navegaciones separadas.
9. Todo dato deportivo usa fuente real o estado pendiente explicito.
10. Pixel-perfect exige screenshots reales.

## Limite

La comparacion final V927 requiere Browser QA. El pase actual esta validado por referencias, HTML renderizado, contratos de rutas y checks estaticos; no se presenta como pixel-perfect.
