# V855 Production Stability QA

Preservado:
- V818 master tick.
- V844 Telegram.
- V845 SHARK.
- V847 API-SPORTS.
- V850 live/escudos.
- V853 admin command center.
- V854 polish global.

Sin cambios en:
- DB_PATH.
- pagos.
- usuarios/sesiones.
- secretos.
- envío Telegram real.
- llamadas API por render.

Validaciones esperadas:
- py_compile.
- compileall.
- Madrid Time.
- Jinja.
- check V855.
- smoke cliente/admin/API.
- ZIP forbidden_count=0.
