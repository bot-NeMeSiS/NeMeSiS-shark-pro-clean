# V935 Realtime Cache QA

## Estrategia

- Cache-first en servidor y cliente.
- TTL local: 15 segundos.
- Poll con live: 45-60 segundos segun snapshot.
- Sin live: 180-300 segundos.
- Live stale: 120 segundos.
- Jitter: +/- 8 %.
- Backoff exponencial hasta 300 segundos.
- Pausa con pestaña oculta.
- Una promesa compartida por endpoint/scope en cada pagina.
- ETag y Last-Modified con respuesta condicional 304 verificada.
- Stale fallback si falla la reconstruccion de cache.

Proveedor por page view: 0 llamadas. Escrituras DB durante polling GET: 0. El estado local es `no_live_events` y espera datos reales sin simular marcadores ni minutos.
