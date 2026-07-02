# V884 Render Deploy Runbook

Produccion sigue en V855, por tanto V884 no puede certificarse en Render hasta desplegar manualmente.

## Pasos exactos
1. Descomprimir el ZIP V884.
2. Entrar en la carpeta descomprimida.
3. Copiar el contenido interno, no la carpeta padre.
4. Pegar en la raiz del repo GitHub correcto.
5. Confirmar en GitHub raiz:
   - `app.py`
   - `VERSION.txt`
   - `requirements.txt`
   - `templates/`
   - `static/`
   - `engines/`
   - `tools/`
6. Confirmar que `VERSION.txt` dice `V884_REAL_RENDER_VISUAL_WORKER_MATCHES_QA_AND_FIX_FINAL`.
7. Confirmar que `app.py` contiene `APP_VERSION = 'V884_REAL_RENDER_VISUAL_WORKER_MATCHES_QA_AND_FIX_FINAL'`.
8. No subir `release_output/`, `.venv/`, `.git/`, DB local, logs, ZIPs internos, caches ni backups.
9. En Render abrir servicio `bot-apuestas-crgf`.
10. Confirmar repo/rama/root directory correctos.
11. Ejecutar `Manual Deploy -> Clear build cache & deploy`.
12. Esperar servicio live.
13. Revisar `/api/runtime-version`.

## Exito esperado
`app_version` y `version_txt` deben devolver V884.
