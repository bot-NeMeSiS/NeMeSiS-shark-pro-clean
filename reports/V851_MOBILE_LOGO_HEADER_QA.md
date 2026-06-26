# V851 QA Móvil Logo/Header

## Revisado
- Header cliente.
- Marca superior.
- Badge de plan FREE/PRO/ELITE.
- Safe-area superior.
- Anchos 390px y 768px mediante CSS responsive.

## Cambios
- `.ns-brand-topbar` limita el ancho móvil para evitar cortes.
- `.ns-brand-mark` baja de 44px a 38px y 35px en pantallas pequeñas.
- `NeMeSiS` y `SHARK PRO` usan `text-overflow` para no romper layout.
- El badge de plan queda como elemento independiente y no empuja el logo fuera.

## Validación
- Check: `tools/check_v851_mobile_logo_header.py`.
- No se tocó bottom nav, floating SHARK ni datos.
