# V852 Auditoría de Producto Basada en Vídeo Real

## Base
- Base confirmada: `V851_LOGO_BRAND_HEADER_MOBILE_PC_FIX`.
- No se usó ZIP viejo como base.

## Qué se vio bien
- Fondo SHARK/puntitos ya existe.
- Bottom nav y marca V851 están mejor encaminados.
- Live, picks, SHARK, Telegram y API-SPORTS tienen capas funcionales previas.

## Problemas priorizados
- Picks de baja relevancia podían ocupar demasiado protagonismo.
- Picks pasados o incompletos podían parecer activos.
- `Selección pendiente` y cuotas pendientes necesitaban estado visual de revisión.
- `/live` mostraba proveedor activo junto a cache/live 0 sin explicación clara para cliente.
- Faltaba un empty state premium que distinga proveedor activo sin directos de fallo técnico.
- Se revisó texto objetivo: `lo primo`, `Result ados`, `EspaÁa/Madrid` y mojibake.

## Cambios V852
- Se endureció `engines/picks_quality_engine.py`.
- `/picks` ordena por calidad y degrada picks caducados/ligas bajas.
- `/live` explica `Sin directos reales ahora mismo` cuando el proveedor está activo pero devuelve 0.
- Se añadió CSS V852 para cards, picks en revisión, diagnóstico live y filtros móviles.
