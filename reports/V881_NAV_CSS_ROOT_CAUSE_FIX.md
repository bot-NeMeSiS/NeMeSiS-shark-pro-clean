# V881 Nav CSS Root Cause Fix

## CSS aplicado

Bloque nuevo:

`V881 SIDEBAR NAV DUPLICATION ROOT FIX`

## Qué corrige

- Oculta rails cliente legacy.
- Oculta quick links y session pills legacy.
- Oculta nav cliente/floating/bottom nav en admin.
- Oculta nav admin/dock/command strip en cliente.
- Desktop oculta bottom nav.
- Móvil oculta topbar cliente y muestra bottom nav.

## Nota

Se usa `!important` solo para neutralizar capas históricas que ya venían con posiciones/fixed/z-index propios.
