# V867 repo root and ZIP structure QA

## Revisión raíz local
- `app.py` existe en raíz.
- `VERSION.txt` existe en raíz.
- `templates/base.html` existe en raíz.
- `static/app.css` existe en raíz.
- `engines/` existe en raíz.
- `tools/` existe en raíz.
- `render.yaml` contiene `gunicorn app:app --bind 0.0.0.0:$PORT`.
- `Procfile` contiene `web: gunicorn app:app`.

## ZIP V866 revisado
ZIP revisado:
`release_output/NeMeSiS_SHARK_PRO_V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL_RENDER_READY.zip`.

Estructura:
- `app.py` en raíz: sí.
- `VERSION.txt` en raíz: sí.
- `templates/base.html` en raíz: sí.
- `static/app.css` en raíz: sí.
- `engines/shark_sentinel_engine.py`: sí.
- `tools/check_v866_real_render_visual_telegram_picks_payments.py`: sí.
- Carpetas anidadas con `app.py`: no detectadas.
- ZIPs internos: no detectados.

## Causa probable del desfase anterior
El desfase V862/V866 era compatible con un deploy anterior no actualizado o una publicación que todavía no había recibido el paquete local V866. La comprobación real de V867 ya muestra V866 en producción.

## Recomendación
Para V867, subir la raíz del repo, no el ZIP como código fuente, y mantener root directory vacío o apuntando a la raíz real del repo.
