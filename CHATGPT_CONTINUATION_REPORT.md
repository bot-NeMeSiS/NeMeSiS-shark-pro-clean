@"
# CHATGPT CONTINUATION REPORT - V844

## Estado base
La carpeta oficial estaba en V843, con producto comercial revisado, rutas corregidas y ZIP limpio.

## Qué cambia V844
V844 se centra en Telegram: calidad de candidatos, no-filler, bloqueo de ligas raras/deportes no permitidos y diagnóstico admin.

## Filtro creado
engines/telegram_quality_filter_engine.py permite fútbol top, bloquea NBA/otros deportes/youth/reserves/regional/amateur/friendly débil y penaliza segundas extranjeras o competiciones desconocidas.

## Telegram
No se envían mensajes reales en local. El canal público queda más conservador: si no hay contenido top, no se manda relleno.

## Pendiente real
Probar en Render con datos reales y TELEGRAM_CHAT_ID real para confirmar qué candidatos aparecen bloqueados y cuáles salen al canal.
## V845_SHARK_AI_INTELLIGENCE_PRODUCT_ASSISTANT_FINAL

Base real usada: `V844_TELEGRAM_TOP_PICK_QUALITY_CARDS_FILTER_FINAL`.

Objetivo de V845: convertir SHARK en un asistente de producto real, responsable y conectado con partidos, picks, Telegram V844, perfil y soporte.

Cambios principales:
- Se añadió `engines/shark_ai_product_assistant_engine.py`, motor local defensivo que no llama APIs externas por sí mismo.
- `/api/shark/ask` usa contexto real de usuario, membresía, partido, pick y filtro Telegram V844.
- `/shark` se reconstruyó como pantalla de asistente premium con respuesta, estado de datos, preguntas rápidas y acciones.
- `/picks` y `/match/` enlazan con textos claros: `Explicar pick con SHARK` y `Analizar con SHARK`.
- Se añadió `/admin/shark-ai` como entrada admin al centro SHARK con estado OpenAI/fallback y reglas anti-invención.
- `/api/runtime-version` expone V845 y `openai_configured` como booleano, sin secretos.

Política de seguridad:
- No inventa picks, cuotas, resultados, minutos, eventos, posesión, estadísticas ni ROI.
- Si falta información, muestra `Cuotas pendientes`, `Resultado pendiente`, `Sin pick real publicado` o recomienda esperar.
- Nunca usa lenguaje de garantía como `apuesta segura`, `garantizado` o `sin riesgo`.
- Si falta `OPENAI_API_KEY`, funciona en modo análisis interno.

Pendiente real:
- Probar visualmente en navegador real si se quiere declarar una revisión pixel-perfect.
- Con datos reales abundantes en producción, se puede ajustar el tono y longitud de las respuestas.
# V847_COMPANY_BRAIN_API_SPORTS_DATA_PROVIDER_AND_PRODUCT_QA_FINAL

Base real usada: V845_SHARK_AI_INTELLIGENCE_PRODUCT_ASSISTANT_FINAL desde la carpeta oficial. No se usó ZIP viejo como base.

Qué se hizo:

- Se auditó el uso real de API-SPORTS/API-Football en código, live, match detail, cron y engines.
- Se añadió `engines/api_sports_provider_engine.py` como fachada segura con cache, dry-run y guard anti-gasto.
- Se añadió `/admin/api-sports` y `/api/admin/api-sports/status` sin exponer secretos.
- `/api/runtime-version` ahora muestra `api_football_configured`, `api_sports_configured`, `the_odds_configured`, `provider_active`, `last_sync`, `last_error` y `usage_guard`.
- SHARK V845 recibe contexto seguro del proveedor.
- Telegram V844 queda intacto y sigue filtrando candidatos top.
- Queda documentado el backlog visual V848 para fondo SHARK/puntitos y pantallas de referencia.

Validaciones: ver `reports/V847_PRODUCTION_STABILITY_QA.md` y `RELEASE_MANIFEST_V847.json`.
