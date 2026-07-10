# V928 Canonical Reference Deep Audit

## Base e inventario

- Base usada: V927 local completa.
- `VERSION.txt`, `APP_VERSION` y runtime local: alineados en V928, sin BOM.
- Referencias: 16/16 presentes y mapeadas por categoría/ruta.
- Áreas revisadas: `app.py`, templates, componentes, CSS, service worker, engines, tools, workforce, Browser QA, runtime data, workflows y rutas.

## Clasificación inicial y cierre

| Área | Estado inicial | Estado V928 |
|---|---|---|
| `/` | Parcialmente alineada | Ya alineada, hero único |
| `/app` | Necesita reconstrucción | Ya alineada desktop/móvil |
| `/calendar`, `/live`, `/picks` | Parcial y dependiente de datos | Ya alineada con estados seguros |
| `/track-record` | Bloqueada por datos cerrados | UI alineada; métricas siguen bloqueadas sin historial real |
| `/match/<id>` | Bloqueada por datos | Template alineado; captura pendiente de partido real |
| `/memberships`, `/profile`, `/telegram`, `/shark` | Parcialmente alineada | Ya alineada |
| Admin prioritario | Necesita reconstrucción | Command center canónico |
| Workforce/Sentinel/Outbox/404 | No presente en referencias | Adaptado al sistema V928 |
| Login y registro | Funcional | Preservado, sin reglas globales agresivas |

## Hallazgos corregidos durante Browser QA

- Margen de sidebar cliente V885 heredado en desktop: neutralizado por el shell V928.
- Contenido admin bajo topbar: compensado con frame canónico.
- Estados convertidos en pills por selectores wildcard históricos: aislados.
- `/memberships` se confirmó en una única instancia limpia de QA.
- Sentinel Issues renderizaba 679 incidencias históricas completas: ahora muestra activas/revalidables y una ventana reciente sin borrar historial.
- Filtros de fecha comprimidos verticalmente: `white-space` y flex canónicos fijados.

## Fuera de alcance seguro

- No se generaron partidos, cuotas, resultados, ROI, pagos, usuarios o escudos oficiales.
- No se activó Telegram, Stripe, deploy hook ni APIs caras.
- No se declaró paridad pixel-perfect.
