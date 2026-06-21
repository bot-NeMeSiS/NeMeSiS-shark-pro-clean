# V845 SHARK AI Current State Audit

Base real confirmada: `V844_TELEGRAM_TOP_PICK_QUALITY_CARDS_FILTER_FINAL`.

Estado anterior:
- `/shark` existía como pantalla de acceso rápido, pero se sentía más como menú que como asistente experto.
- `/api/shark/ask` respondía desde lógica local antigua y arrastraba textos con mojibake en varias ramas.
- `/shark-core` y `/admin/shark-center` existían, pero no exponían claramente estado OpenAI/fallback ni reglas anti-invención.
- La integración con partido/pick estaba presente por enlaces, pero no había un motor unificado de respuesta segura.

Riesgos detectados:
- Respuestas demasiado genéricas.
- Posibilidad de hablar de picks sin contexto suficiente.
- Textos dañados en SHARK antiguo.
- Falta de explicación clara de riesgo/no apostar.
- Falta de diagnóstico admin específico del asistente.

Corrección V845:
- Se creó `engines/shark_ai_product_assistant_engine.py`.
- `/api/shark/ask` usa el motor V845 con contexto real de partido, pick, usuario, membresía y Telegram V844.
- `/shark` muestra respuesta, estado de datos, preguntas rápidas y acciones internas.
- `/admin/shark-ai` queda disponible como centro de estado SHARK.
