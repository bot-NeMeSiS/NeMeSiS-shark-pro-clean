# V937 First 24H Monitoring Plan

## Ventana

Observacion horaria durante 24 horas, solo lectura y sin alertas a clientes.

## Revisar

- Runtime y SHA desplegado.
- HTTP 5xx y latencia de rutas criticas.
- DB health, locks y reinicios.
- Ultima sincronizacion, cache stale y cobertura deportiva.
- Cron y ultimo tick.
- Telegram queue, dedupe y errores, sin enviar.
- Errores de Stripe webhook si son visibles de forma segura.
- Sentinel, Navigation Integrity y health.

## Escalado

- Critico: runtime incorrecto, DB ausente, login roto, secreto, cobro o envio no controlado. Ejecutar stop/rollback.
- Alto: 5xx recurrente, datos stale como actuales, pick incompleto publico. Congelar lanzamiento y abrir hotfix V937.
- Medio: latencia deportiva >4 s sostenida, feed vacio o ETag ineficaz. Mantener NO-GO y corregir antes de usuarios reales.

La automatizacion debe pausarse al terminar las 24 horas o sustituirse por observabilidad permanente aprobada.
