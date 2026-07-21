# V939 Escenarios de recovery

1. Render caido.
2. DB no disponible.
3. DB corrupta.
4. API deportiva caida.
5. Telegram caido.
6. Webhook Stripe caido.
7. Cron detenido.
8. Backup stale.
9. Release defectuoso.
10. Secreto revocado.
11. Perdida del operador principal.

Cada simulacion devuelve deteccion, impacto, pasos, dependencias, objetivo RTO/RPO, evidencia, bloqueos y siguiente accion. Ninguna puede restaurar, desplegar, rotar secretos ni modificar produccion.
