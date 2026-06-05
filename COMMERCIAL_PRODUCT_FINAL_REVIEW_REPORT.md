# NeMeSiS SHARK PRO - Revisión Comercial Integral

## Alcance

Revisión directa sobre la carpeta oficial del proyecto, sin rehacer la app y sin añadir módulos nuevos. El objetivo fue endurecer lo existente: idioma, rutas, enlaces, duplicados visuales, arranque ligero, seguridad básica y paquete limpio Render Ready.

## Errores encontrados

- Textos con codificación rota en plantillas y `app.py`: `MembresÃ­as`, `MÃ¡s`, `PregÃºntame`, `NavegaciÃ³n`, `Membres?a`, `autom?ticas`.
- Enlaces a `/membresias` quedaban rotos porque la ruta Flask también había heredado el texto corrupto `/membres?as`.
- Estado `pending` podía mostrarse en inglés en la pantalla de seguimiento de picks.
- Equipos y competiciones podían repetirse visualmente en listados y APIs al venir desde varias fuentes.
- `/explorar`, `/soporte` y `/seguimiento` ya existían como experiencia/plantilla o enlace, pero necesitaban quedar conectadas y blindadas.
- Restos de ZIP/reportes anteriores seguían en la carpeta durante la revisión.

## Errores corregidos

- Normalizadas rutas y enlaces de membresías a `/membresias`.
- Corregidos textos corruptos en `base.html`, home, calendario, live, match hub, recomendaciones, admin users y textos de `app.py`.
- Traducido `pending` visible a `Pendiente` en seguimiento de picks.
- Añadida deduplicación segura para:
  - partidos
  - competiciones
  - equipos
- Aplicada deduplicación en listados principales, búsqueda, APIs de equipos y diagnósticos de escudos.
- Revalidada navegación interna: `0` enlaces internos muertos detectados.
- Confirmado que `rows()` y `execute()` no disparan `seed_core()` ni `init_db()`.
- Confirmado que `/` no usa `dashboard_data()` pesado.

## Duplicados eliminados

- Partidos: deduplicación por `id`, `external_id`, `source_match_id` o firma deportiva por fecha/liga/equipos.
- Competiciones: deduplicación por `key`, `id` o firma por nombre/país/scope.
- Equipos: deduplicación por `key`, `id`, `external_id` o firma por nombre/país/liga.

## Textos corregidos

- `MembresÃ­as` -> `Membresías`
- `MÃ¡s` -> `Más`
- `NavegaciÃ³n rÃ¡pida` -> `Navegación rápida`
- `PregÃºntame` -> `Pregúntame`
- `Membres?a` -> `Membresía`
- `Membres?as` -> `Membresías`
- `autom?ticas` -> `automáticas`
- `pending` visible -> `Pendiente`

## Rutas revisadas estáticamente

- `/`
- `/login`
- `/admin-login`
- `/registro`
- `/picks`
- `/live`
- `/calendar`
- `/membresias`
- `/explorar`
- `/soporte`
- `/seguimiento`
- `/admin/data-center`
- `/admin/observability`
- `/admin/observability/errors`
- `/api/health`
- `/api/runtime-version`
- `/api/startup-check`
- `/api/observability/summary`
- `/api/observability/errors`

## Validación ejecutada

- `python -m compileall app.py engines database_manager.py`: OK.
- Auditoría estática de enlaces internos: OK, `0` enlaces muertos.
- Auditoría estática de arranque ligero: OK.
- Limpieza de `__pycache__`: OK.
- Flask test client no ejecutado porque el runtime local disponible no tiene Flask instalado (`ModuleNotFoundError: No module named 'flask'`).

## Módulos

| Módulo | Estado | Observaciones |
| --- | --- | --- |
| SHARK | Activo | Sin cambios funcionales; compila. |
| SHARK Learning | Activo | Sin cambios funcionales; compila. |
| Accuracy / ROI | Activo | Seguimiento muestra estados en español. |
| Telegram | Activo | Sin cambios de lógica; formato conservado. |
| Auto Picks | Activo | Sin cambios de lógica; textos corregidos. |
| Live | Activo | Sin duplicados visuales heredados de partidos. |
| Calendario | Activo | Deduplicación y textos corregidos. |
| Picks | Activo | Estados visibles más profesionales. |
| Equipos | Activo | Deduplicación en API/listados. |
| Competiciones | Activo | Deduplicación en salida principal. |
| Observabilidad | Activo | Rutas críticas registradas. |
| Data Center | Activo | Sin cambios destructivos. |

## Pendiente real

- Ejecutar smoke test HTTP en Render o en un entorno local con dependencias instaladas.
- Revisar datos reales de la DB persistente de Render para fusionar duplicados históricos a nivel de base si existen. En esta máquina no hay `/data/database.db` accesible para limpieza de datos persistente.
- Medir tiempos reales con tráfico/DB Render; la revisión local solo valida estructura, sintaxis y enlaces.

