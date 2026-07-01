# V878 Sentinel Layer Purge Rules QA

## Reglas agregadas

`engines/continuous_shark_sentinel_engine.py` expone `visual_rules_v878` con:

- clases deprecated en templates principales;
- botones duplicados;
- CTAs repetidos;
- nav cliente en admin;
- nav admin en cliente;
- floating SHARK duplicado;
- label duplicado en macros;
- demasiadas acciones por card;
- empty states gigantes;
- riesgo de overflow movil;
- Stripe operativo falso;
- Telegram filler;
- OpenAI falso activo;
- logo roto sin fallback.

## Objetivo

Sentinel debe detectar regresiones de capas visuales sin ejecutar acciones peligrosas.

