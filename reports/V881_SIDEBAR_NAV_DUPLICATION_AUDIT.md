# V881 Sidebar Nav Duplication Audit

| Archivo | Bloque | Tipo | Condición | Posible duplicado | Acción V881 |
|---|---|---|---|---|---|
| `templates/base.html` | `nav-clean` | cliente/público | no admin | Sí, competía con client rail | Conservado como fuente cliente desktop |
| `templates/base.html` | `v828-client-rail` | cliente desktop | cliente | Sí, botones laterales repetidos | Retirado del markup |
| `templates/base.html` | `v829-mobile-quick` | cliente móvil/secundario | cliente | Sí, competía con bottom nav | Retirado del markup; token compat en comentario |
| `templates/base.html` | `v797-session-pills` | cliente | cliente | Sí, acciones duplicadas | Retirado del markup |
| `templates/base.html` | `v808-admin-rail` | admin | admin | Fuente válida | Conservado como única nav admin |
| `templates/base.html` | `v808-admin-dock` | admin | admin | Sí, duplicaba rail | Retirado del markup; token compat en comentario |
| `templates/base.html` | `v853-admin-command-strip` | admin | admin | Sí, duplicaba rail/dock | Retirado del markup; token compat en comentario |
| `templates/base.html` | `bottom-nav-clean` | móvil cliente | no admin | Válido | Conservado solo para cliente/público |
| `templates/base.html` | `shark-widget` | cliente | cliente fuera de SHARK | Válido | Conservado con flag `show_floating_shark` |
| `static/app.css` | múltiples capas antiguas | CSS | global | Podía mostrar duplicados | V881 fuerza scopes admin/cliente |
