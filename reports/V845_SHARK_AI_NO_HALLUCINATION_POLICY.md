# V845 SHARK AI No Hallucination Policy

SHARK no puede inventar:
- partidos;
- picks;
- cuotas;
- marcadores;
- minutos;
- eventos;
- posesión, tiros, ataques o estadísticas;
- ROI;
- escudos oficiales.

Reglas aplicadas:
- Sin cuota real: `Cuotas pendientes`.
- Sin pick real: `Sin pick real publicado`.
- Sin marcador: `Resultado pendiente`.
- Sin datos suficientes: recomendar esperar.
- Nunca usar lenguaje de garantía: no `garantizado`, no `apuesta segura`, no `sin riesgo`.
- Siempre incluir riesgo cuando se habla de apuestas.

Validación:
- `tools/check_v845_shark_ai_no_hallucination.py`.
