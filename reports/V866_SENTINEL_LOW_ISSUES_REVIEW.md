# V866 Sentinel low issues review

## Entrada
V865 registró 19 avisos low por `None/null/undefined` en rutas de cliente.

## Revisión
Se ejecutó Sentinel estático en V866 antes del ajuste y reprodujo los 19 avisos low:
- VISITOR: `/`, `/cliente-login`, `/registro`, `/support`.
- FREE: `/partidos`, `/calendar`, `/live`, `/directo`, `/picks`, `/shark`, `/support`, `/track-record`.
- PRO: `/picks`, `/shark`, `/track-record`.
- ELITE: `/live`, `/picks`, `/shark`, `/track-record`.

## Diagnóstico
El detector buscaba tokens técnicos en HTML completo. Eso podía marcar scripts, atributos o datos internos como si fueran texto visible.

## Corrección
`engines/shark_sentinel_engine.py` ahora extrae texto visible antes de marcar `None/null/undefined`.

## Resultado
Sentinel estático V866:
- Score: 10.0.
- Issues abiertos: 0.
- Issues críticos: 0.

## Clasificación
Los 19 avisos quedan cerrados como falsos positivos de detector amplio, no como texto visible real.
