# V915 Render Deploy Pipeline QA

- Render deploy automatico queda preparado, no ejecutado.
- `ENABLE_AUTOMATED_RENDER_DEPLOY` queda desactivado por defecto.
- Secret esperado en GitHub Actions: `RENDER_DEPLOY_HOOK_URL`.
- Secret opcional local/entorno: `RENDER_API_KEY` + `RENDER_SERVICE_ID`.
- El workflow no imprime el deploy hook ni tokens.

## Activacion segura

1. Configurar `RENDER_DEPLOY_HOOK_URL` como secret de GitHub.
2. Ejecutar workflow manual `Render Deploy Guard`.
3. El workflow dispara el hook sin imprimirlo.
4. Espera y consulta `/api/runtime-version`.
5. Falla si la version real no coincide con `VERSION.txt`.

