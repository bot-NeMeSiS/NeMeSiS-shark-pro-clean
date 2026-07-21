# V939 Umbrales de calidad de picks

## Premium ready

- Partido persistido y completo.
- Mercado y seleccion no ambiguos.
- Cuota real mayor que 1.
- Proveedor identificado.
- Timestamp de cuota valido y fresh, hasta 15 minutos.
- Quality score de completitud minimo 90.
- Cero motivos de bloqueo.

## Validated

- Quality score minimo 75.
- Puede requerir revision humana.
- No implica publicacion ni envio.

## Recorded y stale

- De 15 a 60 minutos: evidencia parcial; no Telegram premium automatico.
- Mas de 60 minutos: `PROVIDER_STALE` y bloqueo.

Los umbrales no sustituyen el criterio deportivo ni constituyen una promesa de resultado.
