# V606 — Blueprint Migration Phase 1

## Objetivo

Empezar a resolver la deuda técnica más grande detectada por la auditoría: `app.py` demasiado grande y con muchas rutas.

## Decisión técnica

No se ha movido ninguna ruta todavía para evitar romper la app.
Esta versión crea una capa de preparación:

- paquete `blueprints/`
- motor `blueprint_migration_engine.py`
- herramienta `tools/route_map_v606.py`
- tests básicos

## Beneficio

Permite planificar la migración a Blueprints con evidencia real:

- número total de rutas
- grupos de rutas
- posibles duplicados
- prioridad de migración

## Prioridad futura

1. Auth Blueprint
2. Telegram Blueprint
3. API/System Blueprint
4. Football Blueprint
5. Admin Blueprint

## Seguridad

Actualización no invasiva. No toca funcionalidades existentes.
