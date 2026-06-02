# V571 — Deep Live Intelligence

Avance centrado en profundidad real del live sin añadir pantallas innecesarias.

## Incluye

- Nuevo motor `build_deep_live_intelligence` en `engines/live_engine.py`.
- Extracción de eventos/timeline desde payloads persistidos.
- Extracción de estadísticas live disponibles: posesión, tiros, tiros a puerta, córners, amarillas y rojas.
- Tarjeta inteligente por partido con estado, minuto, marcador, momentum SHARK, alertas, acción recomendada y calidad de datos.
- Nuevo endpoint:

```text
/api/live/deep?date=YYYY-MM-DD&lane=today
```

## Filosofía

No inventa datos. Si la fuente no trae eventos o estadísticas, el sistema mantiene fallback seguro y marca calidad de datos menor.

## Objetivo

Preparar la base para que SHARK pueda leer mejor el partido en directo y decidir cuándo vigilar, alertar o guardar histórico.
