# V898 Reference Images Release QA

## Carpeta oficial

`reference_images/`

Subcarpetas creadas:

- `reference_images/admin/`
- `reference_images/client/`
- `reference_images/mobile/`
- `reference_images/telegram/`
- `reference_images/picks/`
- `reference_images/live/`

Manifest:

`reference_images/reference_manifest.json`

## Build limpio

`tools/build_clean_release.py` ahora incluye `reference_images` como carpeta raíz permitida.

Si se añaden imágenes oficiales, podrán entrar en el ZIP limpio sin usar ZIPs externos.

## Honestidad visual

Si no hay capturas reales de browser, no se declara pixel-perfect.

