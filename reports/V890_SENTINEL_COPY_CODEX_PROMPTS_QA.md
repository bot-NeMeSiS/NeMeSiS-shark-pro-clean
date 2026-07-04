# V890/V892 Sentinel Copy Codex Prompts QA

El centro genera un prompt por incidencia con:

- ID.
- Area.
- Severidad.
- Problema.
- Ruta afectada.
- Archivo probable.
- Evidencia.
- Impacto.
- Reglas sagradas del proyecto.
- Acciones concretas.
- Validaciones obligatorias.
- Entrega esperada.

Los botones de copia son elementos `button` reales con JavaScript seguro basado en `navigator.clipboard` y fallback local a `textarea`. No se usan enlaces falsos `#` ni `javascript:void(0)`.

Estados soportados:

- `OPEN`
- `IN_REVIEW`
- `CODEX_READY`
- `FIX_IN_PROGRESS`
- `FIXED_PENDING_VALIDATION`
- `RESOLVED`
- `IGNORED_SAFE`
- `FALSE_POSITIVE`
- `REOPENED`
