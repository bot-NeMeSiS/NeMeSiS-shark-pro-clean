# V824 Mobile Topbar Nav QA

## Verificaciones

- Topbar unica.
- Bottom nav unica.
- SHARK flotante unico.
- `/shark` sin SHARK flotante duplicado.
- Admin separado del cliente.
- Perfil, soporte y salir visibles.
- Media queries V824 para mobile 560px.

## Resultado

`tools/check_v824_navigation_mobile_dedup.py` paso correctamente.

## Nota

No se pudo verificar overflow real con captura a 390px porque no hubo navegador disponible.
