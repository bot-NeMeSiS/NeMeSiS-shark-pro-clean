# V872 Sentinel screen rules QA

## Reglas reforzadas por V872

V872 no crea un motor nuevo, pero refuerza las condiciones que el Sentinel ya inspecciona:

- botones repetidos;
- nav cliente en admin;
- SHARK flotante duplicado;
- textos `None/null/undefined` visibles;
- mojibake común;
- Stripe operativo falso;
- Telegram filler;
- apuestas garantizadas;
- overflow y cards sobredimensionadas por señales CSS.

## Objetivo de ejecución

Ejecutar `python tools/run_continuous_sentinel_static.py` después de los cambios. El objetivo es mantener score alto y cero incidencias reales.
