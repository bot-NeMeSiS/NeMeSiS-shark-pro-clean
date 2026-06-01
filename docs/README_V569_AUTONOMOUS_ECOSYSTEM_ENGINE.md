# V569 — Autonomous Ecosystem Engine

Avance centrado en que NeMeSiS SHARK PRO funcione como ecosistema autónomo:

- memoria deportiva persistente (`ecosystem_memory`)
- logs de automatización (`automation_runs`)
- candidatos de picks automáticos (`auto_pick_candidates`)
- memoria SHARK (`shark_memory`)
- ruta cliente `/ecosistema`
- panel admin `/admin/autonomous-ecosystem`
- APIs `/api/autonomous-ecosystem/status`, `/api/autonomous-ecosystem/run`, `/api/autonomous-ecosystem/memory`, `/api/system/v569-check`
- ciclo automático: partidos próximos → recomendaciones → picks candidatos → memoria SHARK → Telegram preparado

El admin controla y supervisa; la app prepara datos y oportunidades automáticamente.
