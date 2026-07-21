# V939 Product Analytics Privacy QA

- Salida agregada; no devuelve email, nombre, telefono, IP, cookie ni contenido de sesion.
- No guarda IP completa.
- No implementa fingerprinting.
- No devuelve payloads de actividad.
- Eventos desconocidos no se convierten en conversiones.
- La lectura es SQLite read-only.
- Retencion de eventos: `REQUIRES_REVIEW` antes de activar nueva instrumentacion.
- Consentimiento: requerido cuando aplique.

La DB local observada contiene 6 eventos de actividad y muestra insuficiente para tasas fiables. V939 responde `INSUFFICIENT_DATA`.
