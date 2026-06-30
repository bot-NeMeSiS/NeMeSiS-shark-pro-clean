# V871 Buttons Copy Duplication Audit

## Hallazgos
| Área | Defecto detectado | Acción |
|---|---|---|
| Rail cliente | `Partidos / Partidos`, `Picks / Picks`, `SHARK / SHARK`, `Telegram / Telegram` | Segundo texto cambiado a descriptor útil: `Calendario`, `Premium`, `IA`, `Canal`. |
| Rail admin | `Panel / Panel`, `Mapa / Mapa`, `Clientes / Clientes`, `Datos / Datos` | Segundo texto cambiado a función: `Control`, `Rutas`, `Usuarios`, `Centro`. |
| Soporte rail | `span` vacío antes de `Soporte` | Se sustituye por `Ayuda`. |
| Macros | Labels podían duplicarse si se combinaban con texto externo | Se añade `aria-label` opcional y clase `v871-action-clean`. |
| Telegram | Textos rotos en conexión/vinculación/código | Corregidos a español limpio. |

## Resultado
Los CTAs base quedan con una sola intención visual. Los labels accesibles quedan en `aria-label`, no como texto duplicado.
