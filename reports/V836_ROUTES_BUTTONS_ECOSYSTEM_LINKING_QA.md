# V836 Routes Buttons Ecosystem Linking QA

## Cliente

Rutas enlazadas desde shell y pantallas principales:

- Inicio: `/app`
- Partidos: `/partidos`
- Calendario: `/calendar`
- Directo: `/live`
- Picks: `/picks`
- SHARK: `/shark`
- Perfil: `/profile` y `/mi-cuenta`
- Telegram: `/telegram`
- Soporte: `/support`
- Favoritos: `/favorites`
- Histórico: `/track-record`
- Combis: `/combis`
- Mercados: `/mercados`
- Highlights: `/highlights`
- Salir: `/logout`

## Admin

Rutas enlazadas:

- Panel: `/admin/control-center`
- Dashboard: `/admin/dashboard`
- Mapa: `/admin/map`
- Automatización: `/admin/automation-center`, `/admin/daily-automation`, `/admin/automation-os`
- Telegram: `/admin/telegram/command-center`
- Data Center: `/admin/data-center`
- Usuarios: `/admin/users`
- Membresías: `/admin/memberships`
- Pagos: `/admin/payments`
- Vista cliente: `/sports-hub`
- Salir: `/logout`

## Resultado

V836 añade checks automáticos para detectar enlaces principales ausentes, variables Jinja literales y duplicados críticos.
