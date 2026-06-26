# V847 Telegram SHARK API-SPORTS Context QA

Telegram:

- V844 se conserva intacto.
- API-SPORTS puede alimentar candidatos si los datos están en cache/sync existente.
- Todo candidato Telegram debe pasar por filtro V844.
- Si no hay partido top o pick real, no se manda relleno.
- V847 no envía mensajes reales en local.

SHARK:

- V845 se conserva.
- SHARK recibe `api_sports_provider` en su contexto.
- Puede explicar “API-SPORTS no configurada”, “Esperando proveedor” o “Proveedor activo con caché”.
- Fallback sin OpenAI sigue activo.
- No inventa datos si proveedor no trae información.
