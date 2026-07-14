# V937 Diamond Components CSS JS

## Inventario activo

- 8 hojas CSS en `static/`.
- 4 scripts JS en `static/`.
- 182 plantillas Jinja.
- 24 archivos de referencia conservados.

## Decisiones

- `app.css` queda como `ACTIVE_COMPATIBILITY`; su tamaño requiere una reducción futura basada en cobertura, no una purga masiva.
- V933/V936/V937 siguen siendo superficies activas.
- No se creó una hoja adicional ni un componente decorativo.
- Se retiraron nodos DOM duplicados, no contratos históricos.
- Browser QA amplió sus viewports y rutas reales sin cambiar la aplicación.
- Cache busting: `?v=V937&r=diamond-1`, con runtime local en `true`.

Los 12 workers marcaron `performance` como atención por deuda CSS histórica; producción y rutas locales permanecen dentro de presupuesto.
