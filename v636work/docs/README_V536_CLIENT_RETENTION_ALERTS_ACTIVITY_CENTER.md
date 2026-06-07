# V536 — Client Retention Alerts + Activity Center

Avance centrado en retención del cliente y experiencia diaria:

- Nueva ruta `/alertas` para cliente.
- Nueva ruta `/actividad` para historial personal.
- APIs `/api/client/alerts` y `/api/client/activity`.
- Alertas inteligentes basadas en live, picks publicados, favoritos, próximos partidos y Telegram.
- Perfil cliente con centro de alertas visible.
- Home dinámica con radar SHARK cuando el cliente está logueado.
- Navegación cliente incluye Alertas.
- No se inventan datos: si no hay picks o live, se muestra estado premium y siguiente acción útil.
- Mantiene V535 completo.
- `app.py` compila OK.
- ZIP limpio Render-ready.
