# V829 Mobile SHARK Background And Floating QA

## Fondo SHARK

- Se mantiene la silueta SHARK como asset local.
- No hay descargas runtime.
- No se escribe SQLite durante render.
- En móvil baja opacidad para no tapar texto.
- Puntos/brillo/glow quedan activos con `pointer-events: none`.

## Floating SHARK

- Visible para cliente.
- Oculto en admin.
- Oculto en `/shark`, `/shark-ai` y `/shark-core`.
- Posición móvil: sobre bottom nav y safe-area.
- Panel de chat queda por encima del bottom nav.
- No se crea un segundo widget.

## Validación

`tools/check_v829_mobile_floating_shark.py` verifica widget único, ocultación por rutas SHARK, ocultación admin y posición mobile segura.
