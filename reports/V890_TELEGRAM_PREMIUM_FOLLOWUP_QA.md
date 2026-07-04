# V890 QA seguimiento Telegram premium

V889 queda preservado.

Validaciones esperadas:
- Motor `telegram_pick_quality_engine.py` existe.
- APIs admin de preview/dry-run siguen protegidas.
- Dry-run no envia Telegram real.
- `QUEUE_SKIPPED` preservado.
- No se inventan picks, cuotas ni partidos.

Siguiente paso:
- Desplegar y validar runtime Render antes de probar envio real.
