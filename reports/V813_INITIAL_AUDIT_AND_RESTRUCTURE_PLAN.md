# V813 Initial Audit and Restructure Plan

Versión base auditada: V812_CLIENT_REFERENCE_REBUILD_REAL_LIFECYCLE_TOPBAR_SHARK_FINAL.

## Estado inicial

La aplicación ya tenía una capa cliente moderna con Sports Hub, calendario, directo, picks, SHARK flotante, topbar/bottom nav y panel admin avanzado. Render, Telegram, cron, Madrid Time, pagos, membresías y DB_PATH estaban consolidados en la base.

## Hallazgos principales

- La navegación enlazaba correctamente la mayoría de rutas críticas: `/app`, `/calendar`, `/live`, `/picks`, `/shark`, `/mi-cuenta`, `/admin/control-center`, `/admin/map`, `/admin/automation-center` y `/admin/telegram/diagnostics`.
- Faltaba alias `/support`, aunque la pantalla real de soporte existía como `/soporte` y `/contact`.
- La versión V812 mantenía una capa visual potente, pero necesitaba un ajuste final de densidad y control móvil para acercarse más a app deportiva premium.
- El ciclo de partido podía enviar al fallback `Próximo` un partido de fecha pasada sin marcador si no entraba por otros detectores.
- El filtro automático de Telegram era football-only, pero todavía podía admitir competiciones de bajo valor comercial para canal premium.
- La limpieza del ZIP depende del builder existente, que excluye `.git`, entornos, cachés, bases locales, logs, vídeos, ZIPs internos y carpetas temporales.

## Plan aplicado

1. Elevar versión a V813.
2. Añadir alias seguro `/support`.
3. Activar marcador `data-v813-shell` en `base.html`.
4. Añadir capa visual V813 sin rehacer el diseño.
5. Reforzar lifecycle para que partidos pasados sin resultado sean `Resultado pendiente`, nunca `Próximo`.
6. Endurecer filtro Telegram de canal profesional.
7. Añadir checks V813 de rutas/enlaces y ecosistema.
8. Crear informes finales y preparar release ZIP Render Ready.
