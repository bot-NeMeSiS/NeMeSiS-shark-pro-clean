# V929 Route Alias Compatibility

| Alias | Destino canonico | Estado |
|---|---|---|
| `/clientes` | `rol: /cliente-login, /app o /admin/users` | V929 |
| `/clients` | `rol: /cliente-login, /app o /admin/users` | V929 |
| `/calendar, /calendario` | `/calendar` | compatible |
| `/live, /directo` | `/live` | compatible |
| `/login, /cliente-login, /entrar` | `/cliente-login` | compatible |
| `/historico, /historial` | `/track-record` | compatible |
| `/perfil, /mi-cuenta` | `/profile` | compatible |
| `/admin/routes, /admin/route-health` | `/admin/navigation-integrity` | V929 |

Los aliases no ejecutan acciones de negocio, no llaman proveedores y respetan la sesion activa.
