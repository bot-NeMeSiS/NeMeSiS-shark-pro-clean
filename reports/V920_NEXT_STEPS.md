# V920 Next Steps

## Accion principal

Desplegar V920 y ejecutar Browser QA real.

## Ruta recomendada

1. Subir `release_output/V920_DEPLOY_ROOT_CONTENTS` a GitHub main.
2. Desplegar en Render.
3. Confirmar `/api/runtime-version` en V920.
4. Ejecutar GitHub Action `Browser QA` con:
   `base_url=https://bot-apuestas-crgf.onrender.com`
5. Descargar artifacts.
6. Colocar artifacts en `reports/browser_qa_render/`.
7. Ejecutar:
   `python tools/import_browser_qa_results.py --input reports/browser_qa_render --update-runtime-data`
8. Confirmar que visual queue solo se desbloquea si hay screenshots validos.

## Mantener bloqueado

Si screenshots validos = 0:

- `v920_pixel_perfect_claim_allowed=false`
- visual queue lista = 0
- next action = `run_github_action_browser_qa_or_upload_artifacts`
