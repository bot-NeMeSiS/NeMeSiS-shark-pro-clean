# V845 SHARK AI Security Privacy QA

Controles:
- no se exponen API keys;
- runtime solo devuelve `openai_configured` booleano;
- no se envían secretos a plantillas;
- SHARK no manda Telegram real desde cliente;
- fallback interno evita errores visibles;
- respuestas sanitizadas contra lenguaje irresponsable.
