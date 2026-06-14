# V783 Home/Membership/Client Experience Compact Final

Objetivo: corregir la primera pantalla y las zonas cliente que desperdiciaban espacio.

## Cambios

- Home pública rehecha para mostrar desde el primer pantallazo: propuesta, acceso, FREE, PRO y ELITE.
- Membresías visibles sin obligar al cliente a abrir otra sección para entender los planes.
- Pantalla `/membresias` compactada: hero menor, planes arriba, botones claros y Stripe intacto.
- Home autenticada compactada: Hoy, Directo, Picks, SHARK, Histórico y plan visible.
- `/app` recibe bloque compacto de plan/cuenta para que pagos y membresías no queden escondidos.
- CSS V783 reduce tamaños grandes, padding excesivo, cards desproporcionadas y mejora móvil.

## No tocado

- Telegram, Cron, DB_PATH, usuarios, sesiones, membresías existentes, Stripe webhook, picks, live V780, escudos V779, Madrid Time, Track Record, highlights, Data Marketplace y Automation Center.

## QA

- Nueva comprobación: `tools/check_v783_home_membership_client_experience.py`.
- La pantalla de inicio ya no depende solo de `/membresias` para vender planes.
- Se mantiene Stripe real V782 y sus formularios con CSRF.
