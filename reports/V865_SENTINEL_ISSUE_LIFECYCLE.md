# V865 Sentinel Issue Lifecycle

Estados permitidos:

- `open`
- `acknowledged`
- `grouped`
- `planned`
- `codex_prompt_ready`
- `in_progress`
- `safe_fixed`
- `needs_deploy`
- `deployed_pending_validation`
- `resolved`
- `recurring`
- `ignored`

Modelo operativo:

- `open`: incidencia detectada.
- `acknowledged`: revisada por admin/equipo.
- `grouped`: agrupada con incidencias similares.
- `planned`: convertida en tarea.
- `codex_prompt_ready`: prompt Codex listo.
- `in_progress`: mejora en curso.
- `safe_fixed`: fix local seguro aplicado.
- `needs_deploy`: requiere despliegue real.
- `deployed_pending_validation`: desplegado, pendiente de validar.
- `resolved`: revalidado como resuelto.
- `recurring`: vuelve a aparecer.
- `ignored`: descartado conscientemente.
