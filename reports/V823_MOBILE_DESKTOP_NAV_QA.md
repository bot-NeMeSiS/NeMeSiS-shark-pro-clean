# V823 Mobile Desktop Navigation QA

## Verificaciones

- Topbar cliente unica.
- Bottom nav movil unica.
- SHARK flotante unico.
- SHARK flotante oculto en `/shark` para evitar duplicado.
- Menu admin separado del cliente.
- Cuenta/perfil visible.
- Soporte visible.
- Salir visible.

## CSS

La capa V823 mantiene el control en:

- `body[data-v823-shell="true"].ns-authenticated:not(.ns-admin)`
- `body[data-v823-shell="true"].ns-admin`
- media queries `max-width:960px` y `max-width:560px`

## Resultado

`tools/check_v823_navigation_mobile_dedup.py` paso correctamente.
