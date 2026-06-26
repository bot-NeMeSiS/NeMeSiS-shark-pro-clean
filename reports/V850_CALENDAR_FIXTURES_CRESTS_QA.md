# V850 Calendar Fixtures Crests QA

Pantallas revisadas: `/partidos` y `/calendar`.

Mejoras:

- Template marcado con `data-v850-template`.
- Cada fila puede leer `v850_live_card`.
- Estado/minuto se muestran como chips seguros.
- Textos corregidos: `España/Madrid`, `Filtros rápidos`, `País`, `Foco rápido`, `Día`.

Orden y datos:

- Se preserva la logica existente de calendario/cache.
- No se llama API-SPORTS durante render.
- No se inventan partidos.
