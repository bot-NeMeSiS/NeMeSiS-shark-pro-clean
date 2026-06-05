# V622 COMMERCIAL PRODUCT HARDENING

## Objetivo

Consolidar NeMeSiS SHARK PRO como base beta comercial sin añadir nuevas funcionalidades grandes: menos enlaces muertos, menos duplicados visibles, arranque seguro y paquete limpio para Render.

## Errores encontrados

- Enlaces internos heredados apuntaban a rutas sin endpoint activo: `/explorar`, `/soporte`, `/seguimiento` y varios centros admin legacy.
- Las listas de partidos podían mostrar duplicados cuando el mismo partido llegaba desde varias fuentes o importaciones.
- La ruta de soporte tenía plantilla existente pero no flujo de datos propio.
- La pantalla de seguimiento existía como plantilla, pero no se activaba desde el menú cliente.
- La versión seguía marcada como V621.

## Correcciones aplicadas

- Actualizada versión a `V622_COMMERCIAL_PRODUCT_HARDENING`.
- Añadida deduplicación central de partidos por `id`, `external_id`, `source_match_id` o firma deportiva.
- Aplicada deduplicación en calendario agrupado, partidos por fecha, próximos partidos y resultados.
- Activadas rutas cliente existentes:
  - `/explorar`
  - `/soporte`
  - `/seguimiento`
- Añadidos alias admin protegidos para centros legacy, redirigiendo a centros actuales sin exponer admin al cliente.
- `/soporte` ahora acepta GET/POST, valida asunto/mensaje y registra la solicitud en actividad de usuario si hay sesión.
- `/seguimiento` carga métricas de rendimiento para no dejar la plantilla sin datos.
- Auditoría estática de enlaces internos: `0` enlaces muertos detectados tras la reparación.

## Validaciones

- `python -m compileall app.py engines database_manager.py`: OK.
- `rows()` no llama a `seed_core()` ni `init_db()`.
- `execute()` no llama a `seed_core()` ni `init_db()`.
- `/` no llama a `dashboard_data()`.
- `/api/health`, `/api/startup-check` y `/api/runtime-version` no disparan inicialización pesada.
- Rutas críticas registradas estáticamente:
  - `/`
  - `/login`
  - `/admin-login`
  - `/registro`
  - `/picks`
  - `/live`
  - `/calendar`
  - `/admin/data-center`
  - `/admin/observability`
  - `/admin/observability/errors`
  - `/api/health`
  - `/api/runtime-version`
  - `/api/startup-check`
  - `/api/observability/summary`
  - `/api/observability/errors`

## Limitación de pruebas locales

El runtime local disponible para Codex no tiene Flask instalado (`ModuleNotFoundError: No module named 'flask'`), por lo que no se pudo ejecutar Flask test client en esta máquina. La validación realizada fue de compilación Python y auditoría estática de rutas/enlaces.

## Tabla de módulos

| Módulo | Estado | Observaciones |
| --- | --- | --- |
| SHARK | Activo | Se conserva sin cambios funcionales. |
| SHARK Learning | Activo | Engines compilan correctamente. |
| Telegram | Activo | Sin cambios de lógica; no bloquea home ni health. |
| Auto Picks | Activo | Sin cambios de lógica; alias admin legacy redirige a picks. |
| Warehouse | Activo | Sin cambios de esquema. |
| Live | Activo | Se beneficia de deduplicación en listados. |
| Calendario | Activo | Deduplicación en agrupación y próximos partidos. |
| Picks | Activo | Sin cambios funcionales; seguimiento enlazado. |
| Match Detail | Activo | Sin cambios funcionales. |
| ROI Dashboard | Activo | `/seguimiento` queda conectado a rendimiento. |
| Observabilidad | Activo | Rutas críticas registradas. |
| Data Center | Activo | Alias admin legacy consolidados hacia centros actuales. |

## Pendiente real

- Ejecutar smoke tests con Flask en entorno con dependencias instaladas o directamente en Render.
- Revisar rendimiento real con tráfico y base persistente de Render.
- Mantener `.git` en la carpeta oficial si se quiere seguir trabajando con GitHub; el ZIP final lo excluye.

