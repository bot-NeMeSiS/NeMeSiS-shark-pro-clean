# V726 Total Project Cleanup Live Experience Organization

## Objetivo

V726 consolida la base oficial de NeMeSiS SHARK PRO sin rehacer la aplicación ni romper Render, Telegram, Cron, membresías, SHARK, Data Memory ni el flujo V723-V725.

El foco fue:

- limpiar el árbol del proyecto de forma segura;
- reforzar el ZIP Render Ready;
- compactar la experiencia Live y Calendar;
- mantener horarios en Europe/Madrid;
- conservar los cron protegidos;
- dejar trazabilidad real de auditoría, purga y validación.

## Estado inicial

- Base confirmada: `V725_MADRID_TIME_RELEASE_WORKFLOW_AUTOMATION_FIX`.
- La carpeta oficial no estaba desactualizada.
- Existían artefactos locales generados por validaciones, cachés, reportes históricos y salida de release.
- El ZIP limpio anterior estaba en `release_output`.
- La app ya tenía cron seguro, Telegram V640+, Sports Hub V701+ y hora Madrid V725.

## Cambios aplicados

### Limpieza y release

- `tools/audit_project_tree.py` se consolidó con clasificación V726:
  - `NECESARIO`
  - `BASURA_SEGURA`
  - `DUPLICADO_LEGACY`
  - `DUDOSO_REVISAR`
  - `PELIGROSO_NO_PUBLICAR`
- `tools/purge_project_safe.py` se conectó a la auditoría V726 y genera reportes V726.
- `tools/build_clean_release.py` incluye los entregables V726 y mantiene exclusiones estrictas.
- `VERSION.txt` y `APP_VERSION` se actualizaron a `V726_TOTAL_PROJECT_CLEANUP_LIVE_EXPERIENCE_ORGANIZATION`.

### Live

- `templates/live.html` se compactó para lectura deportiva rápida.
- Se eliminó ruido visual y texto técnico.
- Los partidos en directo muestran minuto real cuando existe.
- Si no hay minuto real, se muestra `En directo` sin inventar datos.
- Si no hay marcador real, se muestra un estado limpio.
- El estado vacío queda claro: “No hay partidos en directo ahora mismo. SHARK seguirá vigilando el calendario.”

### Calendar

- `app.py` ahora resuelve filtros reales para calendario:
  - Hoy
  - Mañana
  - Semana
  - Favoritos
  - Con pick
  - Directo
- `templates/calendar.html` se reescribió en español limpio y formato compacto.
- Los partidos se agrupan por día y se muestran con hora española.
- Los directos en calendario usan `En directo` cuando no hay minuto real.

### Sports Hub

- Se ajustó la tarjeta compacta para directos:
  - minuto real si existe;
  - `En directo` si no hay minuto;
  - hora Madrid para partidos no live.
- La estrella de favorito queda visible en la fila compacta.

### CSS

- `static/app.css` recibió reglas V726 para:
  - filas de partido más densas;
  - filtros horizontales de calendario;
  - badges live/upcoming/finished;
  - mejor lectura móvil;
  - menos espacio muerto.

## Auditoría del árbol

- Auditoría inicial antes de purga: 4.876 archivos.
- Primera purga segura ejecutada: 412 archivos eliminados.
- Auditoría posterior a purga: 4.471 archivos.
- Auditoría tras validaciones y generación de informes: 4.545 archivos.

Los elementos marcados como `PELIGROSO_NO_PUBLICAR` corresponden sobre todo a `.git`, `.venv`, salidas de release y archivos locales protegidos. No entran en el ZIP final.

## Validación ejecutada

- `py_compile app.py`: OK.
- `compileall app.py engines services blueprints tools tests database_manager.py`: OK.
- `tools/check_madrid_times.py`: OK.
- `tools/nemesis_daily_codex.py`: OK.
- `tools/smoke_check.py`: OK.
- Flask test client: sin errores 500 en rutas críticas probadas.
- Cron endpoints:
  - sin secret: 403.
  - con secret: 200.

## Limitaciones reales

- `pytest` no está instalado en el entorno local actual, por lo que no se pudo ejecutar `pytest -q`.
- La entrega se valida con compilación, smoke checks y cliente Flask.
- Telegram real y datos reales de producción dependen de variables Render y servicios externos.

## Conclusión

V726 deja la aplicación más limpia, más compacta y mejor organizada para Live/Calendar/Sports Hub, manteniendo intactos los flujos críticos de Render, cron, Telegram, SHARK, membresías y automatización.
