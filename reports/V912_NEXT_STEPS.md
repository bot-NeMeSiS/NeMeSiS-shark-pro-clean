# V912 Next Steps

## Deploy manual

1. Subir el contenido interno de `release_output/V912_DEPLOY_ROOT_CONTENTS` a la raíz del repo GitHub.
2. Confirmar en GitHub raíz:
   - `app.py`
   - `VERSION.txt`
   - `APP_VERSION`
   - `requirements.txt`
   - `templates/`
   - `static/`
   - `engines/`
   - `tools/`
   - `reports/`
   - `reference_images/`
   - `browser_qa/`
3. En Render: `Manual Deploy -> Clear build cache & deploy`.
4. Abrir `/api/runtime-version`.
5. Confirmar que devuelve `V912_VIDEO_ADMIN_UI_COPY_POLISH_BROWSER_QA_QUEUE_FINAL`.

## Pruebas después de deploy

- Abrir portada y revisar copy.
- Revisar `/admin/shark-sentinel`.
- Revisar `/admin/autonomous-company-sentinel`.
- Revisar `/admin/sentinel-issues`.
- Revisar `/admin/sentinel-codex-outbox`.
- Confirmar que no aparece navegación cliente dentro de admin.
- Confirmar que KPI cards no concatenan textos.
- Ejecutar Browser QA real cuando Playwright esté disponible.

## Recordatorio

No declarar V912 en producción hasta que Render lo confirme.
