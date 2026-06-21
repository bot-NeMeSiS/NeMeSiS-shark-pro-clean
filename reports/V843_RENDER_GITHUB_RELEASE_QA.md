@"
# V843 Render GitHub Release QA

## Fuente real
Carpeta oficial: C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro.
No se usó ningún ZIP antiguo como base.

## Render
Se conserva el flujo Render-ready existente:
- master tick protegido por secret;
- health-check protegido;
- runtime sin secretos;
- DB_PATH sin cambios;
- Telegram/Cron sin cambios funcionales.

## GitHub
No se hizo push automático ni force push. Los cambios quedan en la carpeta oficial para que el usuario decida cómo subirlos.

## ZIP
El ZIP final debe generarse con 	ools/build_clean_release.py y auditarse con 	ools/audit_release_zip.py y 	ools/check_v843_release_cleanliness.py.

## Validación ejecutada
- py_compile app.py: OK.
- compileall app.py engines tools: OK.
- Parse Jinja: 151 templates, 0 errores.
- check_madrid_times.py: OK.
- check_v842_spanish_text_no_mojibake.py: OK.
- check_v842_logos_branding_assets.py: OK.
- check_v842_links_after_text_logo_review.py: OK.
- check_v843_runtime_visibility.py: OK.
- check_v843_routes_actions.py: OK.
- check_v843_real_data_commercial_states.py: OK.
- Smoke Flask V843: OK, sin 500/404 en rutas revisadas.
- Master tick sin secret: 403 OK.
- Master tick con secret dry_run=1: 200 OK.
- Health-check con secret: 200 OK.
- build_clean_release.py: OK.
- audit_release_zip.py: OK, forbidden_count=0.
- check_v843_release_cleanliness.py: OK, forbidden_count=0.

## ZIP final
`release_output/NeMeSiS_SHARK_PRO_V843_PRODUCT_TEAM_COMMERCIAL_READY_FINAL_REVIEW_RENDER_READY.zip`
