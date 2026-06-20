# V836 Reference Photos To App Comparison Matrix

| Referencia | Pantalla esperada | Ruta equivalente | Gap detectado | Cambio aplicado |
|---|---|---|---|---|
| reference_1 | Admin dashboard command center | `/admin/dashboard`, `/admin/control-center` | Necesita mantener jerarquía sobria, cards compactas y rail claro | Capa V836 refuerza cards admin, oculta navegación cliente y mantiene rail admin |
| reference_2 | Telegram command center | `/admin/telegram/command-center` | Debe sentirse operativo, no página suelta | Se conservan enlaces admin y se refuerzan cards/botones responsive |
| reference_3 | Pagos y membresías | `/admin/payments`, `/admin/memberships` | Tablas y acciones deben ser usables en móvil/PC | V836 añade scroll interno seguro y botones táctiles |
| reference_4 | Automatización | `/admin/daily-automation`, `/admin/automation-os` | Necesita command center compacto y sin secretos visibles | V836 mantiene admin separado y documenta validación de health/master tick |

## Pantallas cliente revisadas

- `/`, `/cliente-login`, `/registro`
- `/app`
- `/partidos`, `/calendar`
- `/live`, `/directo`
- `/picks`
- `/match/<id>`
- `/shark`, `/shark-core`
- `/profile`, `/telegram`, `/support`
- `/favorites`, `/track-record`, `/combis`, `/mercados`, `/highlights`

## Pantallas admin revisadas

- `/admin/dashboard`
- `/admin/daily-automation`
- `/admin/automation-os`
- `/admin/telegram/command-center`
- `/admin/data-center`
- `/admin/users`
- `/admin/memberships`
- `/admin/payments`

## Pendiente honesto

La revisión visual automática no sustituye una captura real en navegador. V836 deja checks y CSS de seguridad visual, pero la igualdad exacta con fotos solo puede certificarse con screenshots reales.
