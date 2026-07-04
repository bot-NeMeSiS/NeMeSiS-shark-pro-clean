# QA integracion AutoPilot V889

Integracion:
- Continuous Sentinel expone `telegram_premium_pick_rules_v889`.
- AutoPilot reconoce categoria `telegram_premium_picks`.

Incidencias que debe vigilar:
- No hay picks premium suficientes.
- Intento de enviar pick sin cuota.
- Intento de enviar pick sin seleccion.
- Dedupe bloquea o no bloquea correctamente.
- Formatter falla.
- Visual card falla.
- Render no esta alineado.

No ejecuta acciones peligrosas.
