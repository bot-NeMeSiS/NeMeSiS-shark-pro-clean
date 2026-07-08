# V915 Next Steps

1. Validar localmente V915 con `tools/check_v915_automated_company_workforce.py`.
2. Generar ZIP limpio y deploy root.
3. Subir contenido del deploy root a GitHub main cuando Damian autorice.
4. Configurar en GitHub secret `RENDER_DEPLOY_HOOK_URL` si se quiere activar deploy automático manual.
5. Ejecutar CI.
6. Ejecutar workflow Render Deploy Guard solo cuando corresponda.
7. Confirmar producción en `/api/runtime-version`.

V915 no debe declararse en produccion hasta que Render devuelva `V915_AUTOMATED_COMPANY_WORKFORCE_RENDER_DEPLOY_PIPELINE_FINAL`.
