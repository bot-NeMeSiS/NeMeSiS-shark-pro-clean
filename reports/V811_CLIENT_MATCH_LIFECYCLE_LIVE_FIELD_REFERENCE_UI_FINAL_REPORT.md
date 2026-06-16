# V811_CLIENT_MATCH_LIFECYCLE_LIVE_FIELD_REFERENCE_UI_FINAL

Cliente-only polish sobre V810.

## Implementado
- Ventana API-Football cercana para marcador/minuto/resultados con caché segura.
- Partidos ya jugados dejan de salir como próximos y pasan a resultados o resultado pendiente.
- get_upcoming_matches filtra partidos finalizados/pasados sin marcador.
- Resultados incluye partidos de hoy ya terminados o pendientes de marcador real.
- Campo SHARK Live muestra presión, córners, ataques y ataques peligrosos solo si API-Football lo aporta.
- No se dibuja ubicación exacta de balón si no hay coordenadas reales.
- Barra superior cliente más parecida a las referencias.
- Tiburón decorativo grande/flotante en cliente PC/móvil.
- Dedupe robusto de botón SHARK.

## No tocado
DB_PATH, usuarios, sesiones, membresías, pagos, secretos, Telegram real, Render Cron.
