# V600 Audit Report — NeMeSiS SHARK PRO

Fecha: 2026-06-01

## Resumen ejecutivo

La app actual es funcional y conserva un alcance amplio: cliente, admin, membresías, favoritos, Telegram, picks, recomendaciones, live y SHARK. El principal riesgo no es falta de funcionalidad, sino acumulación histórica en `app.py`, duplicidad de pantallas/README y lógica dispersa entre rutas, motores y migraciones.

V600 se aborda como consolidación incremental: no se rehace la app, no se cambia UX, no se alteran membresías y se mantiene compatibilidad con Render/SQLite.

## Archivos revisados

- `app.py`
- `engines/*`
- `templates/*`
- `static/app.css`
- `database_manager.py`
- `render.yaml`
- `requirements.txt`

## Hallazgos

### Arquitectura

- `app.py` supera 300 KB y mezcla rutas, migraciones, seeds, scheduler, APIs, vistas admin, vistas cliente y QA.
- Existen múltiples capas versionadas (`V565`, `V566`, `V570`) conviviendo en el mismo archivo.
- La separación por engines existe, pero varias capacidades siguen duplicadas dentro de `app.py`.
- `database_manager.py` está bien orientado a Render/SQLite: WAL, busy timeout y retry frente a locks.

### Código duplicado o deuda técnica

- Lógica de recomendaciones y auto picks aparece en rutas, APIs y bloques V565/V566.
- Hay rutas históricas que siguen activas por compatibilidad, aunque no son navegación principal.
- Hay muchas plantillas admin especializadas; no conviene borrarlas sin mapa de uso real.
- Hay documentación histórica `README_V5XX*` en raíz, movida ahora a `docs/`.

### Templates

- La mayoría de pantallas están conectadas a rutas actuales.
- Hay plantillas legacy que pueden seguir siendo útiles para rutas antiguas o admin.
- No se recomienda eliminar templates en V600 sin telemetría de uso.

### Engines

- `live_engine.py` era demasiado básico para el objetivo comercial: momentum simple y timeline fallback.
- `scheduler_engine.py` cubría tareas principales, pero faltaban tareas explícitas para recomendaciones, auto picks, alertas live y warehouse histórico.
- `membership_engine.py` mantiene buena base para FREE/PRO/ELITE.

### Datos y SQLite

- La DB mantiene migraciones seguras por columnas.
- Faltaba warehouse histórico explícito para aprendizaje futuro.
- `user_activity` ya existe y se conserva.

### Render

- `render.yaml` mantiene `DB_PATH=/data/database.db`.
- `requirements.txt` cubre Flask/Gunicorn/Jinja/Werkzeug.
- No se cambia configuración Render en V600.

## Acciones V600 aplicadas

- Documentación histórica movida a `docs/`.
- Creado `README_MASTER.md`.
- Creado `CHANGELOG_V600.md`.
- `VERSION.txt` actualizado.
- `live_engine.py` consolidado con SHARK Momentum, timeline normalizado y alertas.
- Añadidas tablas `historical_matches`, `historical_picks`, `historical_recommendations`.
- Añadido snapshot histórico interno.
- Scheduler ampliado con tareas: `recommendations`, `auto_picks`, `live_alerts`, `warehouse`.

## Riesgos detectados

- `app.py` debería dividirse gradualmente en blueprints o módulos internos, pero no en una sola operación.
- La eliminación automática de templates/rutas muertas puede romper compatibilidad.
- Las recomendaciones automáticas deben seguir diferenciadas de picks publicados.
- Las alertas live están preparadas para Telegram, pero no deben enviar mensajes agresivos sin límites por usuario/membresía.

## Próxima hoja de ruta V601-V605

- V601: exponer Live Intelligence en más bloques de partido sin cambiar UX.
- V602: panel admin de warehouse histórico y métricas de aprendizaje.
- V603: convertir auto picks candidatos en flujo admin claro de aprobación.
- V604: límites Telegram por membresía y prioridad ELITE.
- V605: extracción gradual de rutas desde `app.py` a módulos/blueprints manteniendo URLs.
