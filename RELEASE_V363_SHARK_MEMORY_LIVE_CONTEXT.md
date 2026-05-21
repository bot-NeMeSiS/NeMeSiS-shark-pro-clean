# V363.0 · SHARK Memory + Live Context Engine

Avance aplicado sobre V362 sin romper rutas existentes.

## Incluye
- Tabla `shark_memory_events` para memoria persistente real por usuario.
- Tabla `match_context_snapshots` para snapshots live/contextuales.
- API `/api/v363/live-context` con lectura de picks reales persistidos.
- API `/api/v363/shark-memory` para resumen de memoria.
- API POST `/api/v363/shark-memory/event` para guardar interacciones.
- Vista cliente `/cliente/v363-shark-memory-preview`.
- Vista admin `/admin/v363-shark-memory`.

## Importante
No inventa partidos ni datos. Si no hay picks reales en SQLite, muestra estado vacío premium. Si hay picks, crea contexto SHARK desde esos datos.
