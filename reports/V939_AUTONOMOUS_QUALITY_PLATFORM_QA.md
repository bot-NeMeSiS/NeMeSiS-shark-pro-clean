# V939 Autonomous Quality Platform QA

Flujo integrado:

`DETECT -> CLASSIFY -> EVIDENCE -> PRIORITIZE -> TASK -> CODEX PROMPT -> APPROVAL -> FIX -> VERIFY -> CLOSE -> LEARN`

## Puede preparar

Reportes, incidencias internas, deteccion de mojibake, propuesta de fallback, estado interno, prompts y checklists.

## Requiere aprobacion

Codigo, rutas, autenticacion, DB, pagos, envio Telegram, APIs externas, deploy, push, borrado y secretos.

Incluso las categorias seguras tienen `execution_enabled=false` en este motor: V939 prepara la decision, no la ejecuta.

`PASS LOCAL`.
