# V845 SHARK AI Fallback QA

Si `OPENAI_API_KEY` no está configurada:
- SHARK entra en `Modo análisis interno`.
- No rompe la pantalla ni el endpoint.
- Usa datos reales disponibles.
- No enseña errores técnicos al cliente.
- No llama proveedores externos.

Validación:
- `tools/check_v845_shark_ai_fallback.py`.
