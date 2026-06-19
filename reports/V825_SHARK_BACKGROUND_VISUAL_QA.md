# V825 Shark Background Visual QA

## Implementacion

- `templates/base.html` incluye una capa global `v825-shark-background`.
- La capa contiene:
  - `shark-dot-watermark`
  - `shark-grid-texture`
  - `shark-glow-orb one`
  - `shark-glow-orb two`

## Seguridad visual

- `pointer-events: none`.
- `z-index` negativo.
- SVG local `/static/img/shark-logo.svg`.
- Sin imagen externa.
- Sin descarga runtime.
- Sin SQLite.
- Admin no muestra fondo SHARK gigante.

## Resultado

`tools/check_v825_shark_background.py` paso correctamente.
