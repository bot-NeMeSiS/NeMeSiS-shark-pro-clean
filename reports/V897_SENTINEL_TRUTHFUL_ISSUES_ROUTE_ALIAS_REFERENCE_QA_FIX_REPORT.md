# V897 Sentinel Truthful Issues Route Alias Reference QA Fix

Version final local:

`V897_SENTINEL_TRUTHFUL_ISSUES_ROUTE_ALIAS_REFERENCE_QA_FIX_FINAL`

## Realidad Render

Runtime real consultado:

`https://bot-apuestas-crgf.onrender.com/api/runtime-version`

Resultado observado: producción sigue en `V894_AUTONOMOUS_COMPANY_SENTINEL_REFERENCE_CODEX_WORKFORCE_FINAL`.

Conclusión: producción no sirve aún V896/V897. No se declara V897 desplegada.

## ZIP limpio previo

El ZIP V896 sigue siendo un paquete Render Ready válido como base limpia previa:

`release_output/NeMeSiS_SHARK_PRO_V896_PRODUCTION_NOT_FOUND_ROUTE_RECOVERY_FULL_APP_SMOKE_FINAL_RENDER_READY.zip`

No se debe subir la carpeta grande de trabajo a Render/GitHub porque contiene `.git`, `.venv`, `release_output`, memorias runtime y basura local excluida por el builder.

## Correcciones V897

- Versión local actualizada a V897.
- `admin-login` tratado como superficie admin.
- Bottom nav, sidebar cliente y floating SHARK público ocultos en `/admin-login` y rutas admin.
- Alias legacy registrados solo si la ruta no existe realmente.
- `/dashboard` redirige a `/app` sin depender de sesión.
- Sentinel Issues reconcilia incidencias antiguas no reproducidas.
- Sentinel visible text ignora `script`, `style`, `template`, SVG, comentarios y HTML técnico antes de buscar `None/null/undefined`.
- Carpeta oficial `reference_images/` creada.
- Browser QA opcional creado en `tools/run_browser_reference_qa.py`.

## Seguridad

No se tocaron secretos, DB real, usuarios, pagos ni Telegram real.

