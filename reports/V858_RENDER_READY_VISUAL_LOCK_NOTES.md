# V858 Render Ready Visual Lock Notes

## Build
- `tools/build_clean_release.py` incluye reportes V858 y auditoría ZIP V858.
- ZIP final esperado: `NeMeSiS_SHARK_PRO_V858_VISUAL_DIRECTION_LOCK_FULL_APP_REFERENCE_FINAL_RENDER_READY.zip`.

## Seguridad
- No se tocan secretos.
- No se añaden llamadas externas.
- No se escribe SQLite durante render.
- No se incluye DB local, logs, cachés, ZIPs internos ni `.git/.venv`.

## Honestidad
- No se afirma Render real si no se prueba.
- No se afirma Telegram real si no se envía.
- No se afirma APIs reales si no hay claves.
- No se afirma pixel-perfect sin screenshots reales.
