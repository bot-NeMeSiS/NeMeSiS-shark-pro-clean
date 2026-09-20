# NeMeSiS - Master Control

Entrada operativa unica. Actualizado 2026-09-20.
DEPORTE PRIMERO -> SHARK DESPUES -> APUESTAS EN TERCER LUGAR.

## Base real

Produccion y GitHub convergen actualmente en:
`bf0a36dd1f2ff928d143ae6ac0254bf20f991529`.

PR #16 y PR #19 estan fusionados. Render web + cron estan LIVE sobre el SHA actual.
PR #19 añade lectura historica persistida por fecha en Calendario sin tocar Track Record ni proveedores.
PR #14 y PR #15 quedaron cerrados como SUPERSEDED, sin borrar su evidencia historica.

## Orden operativo vigente

1. OPS-001 — cierre operativo Sentinel sobre main actual, manteniendo LOCAL SAFE y verificando persistencia/limites.
2. Sports Reality / Directos — continuar desde main, no desde PR #14; validar comportamiento productivo y verdad deportiva sin inventar feed.
3. Resultados / navegacion historica — completar experiencia deportiva por fecha separada de Track Record/ROI.
4. Design / Product Finish — conservar frente visual y cerrar conformidad contra referencias sin asumir R9/H07 resueltos.
5. Comercial — pagos/Stripe/ELITE+ solo tras gates especificos.

## Autoridad

REAL_PRODUCTION observada con SHA/fecha/alcance -> GitHub main/CI -> codigo y pruebas del mismo SHA -> informes fechados -> sintesis -> historia.

Un PASS local no sustituye produccion.
Un deploy LIVE no certifica proveedor, pagos, derechos, experiencia fisica ni todos los consumidores.
Un documento no concede permisos.

## Guardrails

- Sentinel local no se transforma en worker productivo.
- No inventar marcadores, minutos, picks, cuotas, resultados o confianza.
- No ampliar proveedor ni gasto sin autorizacion y evidencia.
- No mezclar ramas historicas superseded con main automaticamente.
- Design y Sports Reality permanecen frentes activos hasta su cierre verificable.

Ver [CURRENT_TRUTH](CURRENT_TRUTH.md), [ACTIVE_WORK](ACTIVE_WORK.md), [CODEX_QUEUE](CODEX_QUEUE.md), [BLOCKERS](BLOCKERS.md) y [RELEASE_STATE](RELEASE_STATE.md).
