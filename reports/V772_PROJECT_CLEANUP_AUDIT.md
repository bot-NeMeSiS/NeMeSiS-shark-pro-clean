# V772 Project Cleanup Audit

## Política

El ZIP final se genera con `tools/build_clean_release.py` y se audita con `tools/audit_release_zip.py`.

## Exclusiones esperadas

- `.git`
- `.venv`
- `venv`
- caches
- bases de datos locales
- logs
- ZIPs internos
- vídeos
- temporales
- secretos reales

## Cambios de limpieza V772

- Se añadió el check `tools/check_v772_telegram_visual_cards_app_global_polish.py`.
- Se permitió incluir informes `reports/V772_*` en el ZIP.
- Se mantiene `.env.example` y `.env.render.clean` sin secretos reales.

## Pendiente manual

- Cualquier texto legacy fuera de Telegram que conserve mojibake debe tratarse en una versión lingüística global, no dentro del alcance V772.
