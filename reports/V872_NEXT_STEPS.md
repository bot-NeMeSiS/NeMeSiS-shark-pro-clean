# V872 next steps

1. Desplegar manualmente el ZIP V872 en Render.
2. Confirmar `/api/runtime-version` en producción con `V872_REAL_RENDER_SCREEN_CAPTURE_REFERENCE_FINAL_PASS`.
3. Capturar PC y móvil reales con navegador autorizado.
4. Comparar contra referencias pantalla a pantalla.
5. Si quedan capas visuales antiguas pisando V872, preparar V873 design-system purge.
6. Revisar sync/cache de logos por cron/dry-run, sin llamadas por render.
7. Validar Telegram real solo con autorización explícita.
8. Validar pagos solo en modo test controlado.
