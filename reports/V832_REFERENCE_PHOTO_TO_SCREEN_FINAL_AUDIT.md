# V832 Reference Photo To Screen Final Audit

## Alcance

Se revisó la estructura visual real existente frente al objetivo de app deportiva premium: móvil compacto, PC con jerarquía clara, SHARK visible, admin sobrio y navegación coherente.

## Pantallas cliente

- `/`: landing premium con SHARK, CTA y fondo visual.
- `/cliente-login` y `/registro`: paneles de acceso con shell visual unificado.
- `/app`: centro principal con resumen, accesos y cards.
- `/partidos` y `/calendar`: listados deportivos con cards compactas, estados y detalle.
- `/live` y `/directo`: centro live sin inventar minuto ni marcador.
- `/picks`: cards vendibles y empty state si no hay datos suficientes.
- `/match/<id>`: conexión hacia partidos, picks y SHARK.
- `/shark`, `/shark-ai`, `/shark-core`: pantalla estrella sin floating duplicado.
- `/profile`, `/telegram`, `/support`: pantallas de cuenta y ayuda integradas.
- `/favorites`, `/track-record`, `/combis`, `/mercados`, `/highlights`: se mantienen en shell compacto y enlazado.

## Pantallas admin

- `/admin/dashboard`, `/admin/map`, `/admin/daily-automation`, `/admin/automation-os`, `/admin/telegram/command-center`, `/admin/data-center`, `/admin/users`, `/admin/memberships`, `/admin/payments`, `/admin/final-certification` mantienen shell separado, sin bottom nav cliente ni floating SHARK.

## Qué se modifica

V832 no reescribe plantillas funcionales. Añade una capa visual final, marca pantallas reales con `data-v832-template`, crea macros ligeras y documenta workflow GitHub/Render.

## Qué se neutraliza

Se mantiene neutralizada la bottom nav duplicada en desktop, el floating SHARK en admin y en rutas SHARK, y la flecha mobile conflictiva heredada de V830.
