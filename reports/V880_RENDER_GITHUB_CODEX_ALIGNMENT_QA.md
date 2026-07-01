# V880 Render GitHub Codex Alignment QA

## Render real

Endpoint: `https://bot-apuestas-crgf.onrender.com/api/runtime-version`

Resultado observado:

- Producción: `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`
- Local: `V880_FULL_APP_PROBLEM_SWEEP_AND_FIX_ALL_SAFE_FINAL`
- Mismatch: Sí.
- `last_error`: `Invalid header value ...`
- `openai_configured`: `false`
- logos cache: `0`.

## Git/Codex

No se hizo push automático. El paquete V880 debe subirse manualmente a raíz GitHub y desplegarse con cache limpio.

## Acción exacta

1. Descomprimir ZIP V880.
2. Copiar contenido interno a la raíz GitHub.
3. Confirmar `VERSION.txt` y `app.py` en raíz.
4. Render: `Clear build cache & deploy`.
5. Verificar `/api/runtime-version = V880`.
