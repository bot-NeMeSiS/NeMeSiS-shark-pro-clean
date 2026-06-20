# V829 Full Routes Buttons Links Ecosystem Audit

## Cliente

Botones/enlaces clave revisados y conectados:

- Inicio: `/app`.
- Partidos: `/calendar` y `/partidos`.
- Directo: `/live` y `/directo`.
- Picks: `/picks`.
- SHARK: `/shark`.
- Perfil: `/profile`.
- Telegram: `/telegram`.
- Soporte: `/support`.
- Favoritos: `/favorites`.
- Histórico: `/track-record`.
- Combis: `/combis`.
- Mercados: `/mercados`.
- Highlights: `/highlights`.
- Salir: `/logout`.

## Admin

Enlaces principales conservados:

- Dashboard/control center.
- Mapa.
- Automatización.
- Telegram command center.
- Data Center.
- Usuarios.
- Membresías.
- Pagos.
- Certificación.
- Vista cliente.

## Correcciones V829

- Se añade `v829-mobile-quick` con enlaces secundarios útiles para móvil.
- Se mantiene bottom nav única con cinco accesos principales.
- Se revisa que no aparezca el literal `{{ title or ... }}`.
- No se detectan enlaces principales faltantes en los checks V829.

## Pendiente manual

Algunas anclas heredadas sin `href` actúan como componentes visuales o contenedores en templates históricos. No se eliminan para no romper layouts antiguos; quedan documentadas por checks de revisión.
