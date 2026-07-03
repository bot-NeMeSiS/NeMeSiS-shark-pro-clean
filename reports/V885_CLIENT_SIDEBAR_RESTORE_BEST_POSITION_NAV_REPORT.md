# V885 Client Sidebar Restore Best Position Nav Report

## Resumen

V885 devuelve al cliente una navegacion lateral util en PC sin reabrir el problema de duplicados. La regla final queda clara: sidebar cliente en desktop, bottom nav en movil y rail admin separado.

## Corregido

- Sidebar cliente canonico `ns-client-sidebar` restaurado.
- Topbar cliente autenticado deja de duplicar enlaces principales.
- Bottom nav queda como fuente movil.
- Admin queda aislado de navegacion cliente.
- Visual Worker y Sentinel ahora conocen reglas V885.
- Runtime expone `has_v885_client_sidebar_restore`.

## Preservado

- V818 master tick.
- Madrid Time.
- Telegram no filler/dedupe.
- SHARK safe mode.
- API-SPORTS/The Odds guards.
- DB_PATH, usuarios, sesiones, membresias y pagos.
- Sistema visual `ns-*`.
- V881, V882, V883 y V884.

## No probado

- Browser QA real.
- Deploy Render.
- Telegram real.
- Pagos reales.

## Siguiente accion

Deploy manual de V885, validar runtime y hacer captura PC/movil para ajustar posicion fina si hiciera falta.
