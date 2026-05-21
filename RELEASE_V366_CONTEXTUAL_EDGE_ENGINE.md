# NeMeSiS SHARK PRO V366.0

Avance aplicado encima de V365 sin borrar rutas anteriores.

## Nuevo
- SHARK Contextual Edge Engine.
- Scoring contextual cruzando SHARK Score, Value Index, calidad de datos, cuota y riesgo.
- Estado comercial por señal: DESTACAR EN PRO/ELITE, PUBLICABLE CON CONTROL, SOLO REVISIÓN ADMIN u OCULTAR CLIENTE.
- Commercial Readiness Center para admin.
- Tablas SQLite nuevas: `shark_contextual_edge`, `shark_commercial_readiness`, `shark_user_memory_profile`.
- Endpoints nuevos:
  - `/api/v366/contextual-edge`
  - `/api/v366/readiness`
  - `/cliente/v366-contextual-edge`
  - `/admin/v366-commercial-readiness`

## Compatibilidad
- Mantiene V363, V364 y V365.
- No toca configuración Render.
- No requiere variables nuevas.
