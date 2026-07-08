# V916 GitHub Actions Workflow QA

- `nemesis-ci.yml`: preparado para checks de CI sin secretos.
- `render-deploy.yml`: preparado para `workflow_dispatch` y `RENDER_DEPLOY_HOOK_URL` desde GitHub Secrets.
- `browser-qa.yml`: preparado para instalar Playwright y generar artifacts de capturas/reportes.

## Seguridad
- No se imprimen hooks ni tokens.
- No se ejecuta Telegram real.
- No se tocan pagos.
- No se declara produccion si runtime no coincide.
