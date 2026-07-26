# V938 External Monitoring and Dead-Man Alerts

## Diseño

Un proceso fuera de Render debe consultar cada 5 minutos runtime/health y registrar:

- disponibilidad y latencia;
- versión y SHA esperado;
- edad del último Cron y sync deportivo;
- DB health enmascarado;
- stale/falsos live;
- errores Stripe visibles sin iniciar pagos;
- estado Telegram sin enviar.

Si faltan dos pulsos consecutivos, crea una alerta interna deduplicada. Nunca alerta a clientes, nunca despliega, nunca restaura y nunca envía Telegram de producto.

## Estado

**NO CERTIFICADO.** V938 entrega la política y la señal de readiness; no crea infraestructura externa ni activa destinos sin autorización.
