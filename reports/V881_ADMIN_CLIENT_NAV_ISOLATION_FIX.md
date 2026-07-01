# V881 Admin Client Nav Isolation Fix

## Flags centralizados

Se añadieron en `base.html`:

- `is_admin_area`
- `is_client_area`
- `show_client_nav`
- `show_admin_nav`
- `show_mobile_bottom_nav`
- `show_floating_shark`

## Cliente

Puede ver topbar/bottom nav/floating SHARK. No ve rail admin, dock admin ni command strip.

## Admin

Puede ver admin rail. No ve bottom nav cliente, floating SHARK cliente ni sidebar cliente.
