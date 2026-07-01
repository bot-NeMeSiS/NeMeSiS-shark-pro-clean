# V880 Full App Problem Inventory

| Área | Pantalla/Ruta | Problema | Gravedad | Evidencia | Impacto | Fix seguro | Aprobación | Corregido V880 |
|---|---|---:|---:|---|---|---|---|---|
| Render/GitHub | Producción | Render sigue en V855 | Alta | Runtime real devuelve V855 | No se ve V879/V880 en producción | Documentar deploy exacto | Sí para deploy | Documentado |
| Runtime | `/api/runtime-version` real | `last_error` histórico de header inválido | Media | Runtime Render lo expone | Confusión operacional | Mantener sanitización local y reportar | No | Documentado |
| Cliente | varias | Riesgo de huecos/cards grandes | Media | capas históricas acumuladas | Menor percepción premium | CSS V880 compacta | No | Sí |
| Móvil | varias | Riesgo de overflow horizontal | Media | app con grids/tablas | Mala UX móvil | CSS V880 overflow/table wrap | No | Sí |
| Admin | varias | Riesgo de elementos cliente en admin | Alta | múltiples capas antiguas | Command center confuso | CSS V880 oculta nav/floating cliente | No | Sí |
| Sentinel | motor | Score alto puede no explicar problemas de deploy/datos | Media | reglas previas visuales | QA menos útil | Reglas V880 de problema real | No | Sí |
| Partidos/live | `/partidos`, `/live` | Si proveedor no devuelve datos, debe explicarse | Media | no se deben inventar partidos | Producto parece vacío | Estados seguros y reporte | No | Documentado |
| Picks/Odds | `/picks` | Picks sin cuota/selección deben separarse | Media | regla de datos reales | Riesgo comercial | Check y reportes safe state | No | Documentado |
| Logos | cards | Cache 0 requiere fallback | Media | runtime real cache 0 | Imágenes rotas | CSS fallback/ocultar img vacía | No | Sí |
| Pagos | membresías | Stripe no debe figurar operativo falso | Alta | regla de producto | Riesgo comercial/legal | check bloquea frase | No | Sí |
| Seguridad | admin/cron | Admin/cron deben protegerse | Alta | smoke local | Riesgo seguridad | Smoke y check | No | Sí |
| Release | ZIP | Riesgo basura workspace | Alta | workspace contiene .venv/.git/caches | ZIP sucio | builder/audit | No | Sí |
