# V871 Screen by Screen Visible Fix QA

## Cliente
- `/`: se compacta hero/cabecera y se mantiene marca premium sin aumentar datos falsos.
- `/app`: en sesión no autenticada redirige a login; la shell conserva cache V871 y sin overflow horizontal.
- `/partidos` y `/calendar`: Sentinel ya no confunde filas de partidos con botones duplicados; los estados se mantienen seguros.
- `/partidos` y `/calendar`: se corrigió mojibake visible en mensajes de día/calendario.
- `/live`: filas y cards más densas; sin scroll horizontal en captura móvil.
- `/picks`: CTA y estados `Cuotas pendientes`, `Selección pendiente` y `Pick en revisión` quedan separados.
- `/shark`: card móvil más compacta, sin duplicar SHARK flotante en admin.
- `/telegram`: copy corregido de conexión/vinculación/código; sin envío real.
- `/support`: se validó que no quede mojibake visible tras la normalización.
- `/profile`, `/track-record`, `/support`: se benefician de la compactación global de cards, empty states y acciones.

## Admin
- `/admin/dashboard`: se oculta navegación cliente y se compactan cards/tablas.
- `/admin/company-os` y `/admin/company-audit`: se preservan workers/board y se reduce aire visual por capa V871.
- `/admin/continuous-sentinel`, `/admin/sentinel-workflow`, `/admin/fix-pipeline`: acciones más limpias y Sentinel sin falsos positivos de filas deportivas.
- `/admin/payments` y `/admin/memberships`: se mantiene honestidad de pagos; no se inventan cobros ni Stripe operativo.

## Resultado esperado
Menos huecos negros, cards más compactas, CTAs sin duplicados y avance visual perceptible sin rediseño caótico.
