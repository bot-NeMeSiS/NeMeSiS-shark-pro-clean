# Next Deployment Actions

## P0 - Confirmar GitHub real

El conector GitHub no tiene cuentas accesibles y `gh` no existe en PATH. Ademas, el Git empaquetado no puede hacer `ls-remote` por falta de `remote-https`.

Accion humana:

1. Abrir GitHub Desktop.
2. Seleccionar `bot-NeMeSiS/NeMeSiS-shark-pro-clean`.
3. Confirmar rama `main`.
4. Pulsar `Fetch origin`.
5. Confirmar si hay `Push origin` pendiente.
6. Abrir el repo en GitHub web.
7. Confirmar que en la raiz existen:
   - `app.py`
   - `VERSION.txt`
   - `APP_VERSION`
   - `requirements.txt`
   - `templates/`
   - `static/`
   - `engines/`
   - `tools/`
8. Confirmar que `VERSION.txt` en GitHub dice:

```text
V886_REAL_BROWSER_NAV_VISUAL_QA_AFTER_V885_FINAL
```

## P0 - Alinear Render

Render real esta en:

```text
V883_VISUAL_COMPANY_WORKER_BOT_CONTINUOUS_IMPROVEMENT_FINAL
```

Local esta en:

```text
V886_REAL_BROWSER_NAV_VISUAL_QA_AFTER_V885_FINAL
```

Accion humana:

1. Si GitHub Desktop muestra cambios locales, hacer commit claro.
2. Hacer push a `main`.
3. Entrar en Render.
4. Abrir servicio `bot-apuestas-crgf`.
5. Confirmar repo conectado:
   `https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean`
6. Confirmar rama: `main`.
7. Confirmar Root Directory: vacio o raiz correcta.
8. Confirmar Start Command: `gunicorn app:app`.
9. Ejecutar `Manual Deploy -> Clear build cache & deploy`.
10. Esperar servicio live.
11. Abrir:
    `https://bot-apuestas-crgf.onrender.com/api/runtime-version`
12. Confirmar que devuelve V886.

## Si Render sigue en V883

Revisar:

- Render apunta a otro repo.
- Render apunta a otra rama.
- Root Directory incorrecto.
- GitHub no tiene V886 en raiz.
- Se subio ZIP como archivo en vez de contenido.
- Auto deploy desactivado.
- Build cache no se limpio.
- Otro servicio Render esta asociado a la URL.

## No hacer

- No inventar PRs/issues.
- No usar datos sinteticos.
- No tocar secretos.
- No borrar DB.
- No deploy automatico desde Codex.
- No push automatico sin orden explicita.

## Siguiente verificacion Codex

Despues del deploy manual, volver a ejecutar:

1. `/api/runtime-version` Render.
2. Comparar `app_version`, `version_txt`, `static_app_css_hash`.
3. Ejecutar Browser QA real si Render ya sirve V886.
