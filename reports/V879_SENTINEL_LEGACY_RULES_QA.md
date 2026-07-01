# V879 Sentinel Legacy Rules QA

## Reglas preservadas

El Sentinel mantiene reglas V878 para vigilar:

- clases deprecated en templates primarios;
- labels y CTAs duplicados;
- navegación cliente dentro de admin;
- navegación admin dentro de cliente;
- floating SHARK duplicado;
- demasiadas acciones por card;
- empty states excesivos;
- Stripe falso operativo;
- Telegram filler;
- OpenAI falso activo;
- logos rotos sin fallback.

## Estado V879

V879 no rebaja reglas del Sentinel. Al contrario, convierte el check V879 en guard adicional para confirmar:

- V879 versionado;
- V878 preservado;
- reportes V879 presentes;
- `ns-*` preservado;
- deprecated bridge fuera de templates primarios;
- sin tokens visibles `None/null/undefined`;
- sin secretos ni claims prohibidos.

## Objetivo Sentinel

Mantener score alto y cero issues reales antes del ZIP final.
