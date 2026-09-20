# SENTINEL OPERATIONAL CLOSURE — 2026-09-20

Estado: **DONE_LOCAL_SAFE / NO PRODUCT EXECUTOR**.

Base revisada: `main@7a1ba50bf9d6fec8648fcacc2dae72b7cbe730ba`.

## Qué se verificó

- El supervisor Sentinel se inicia únicamente por `tools/local_desktop/run_sentinel_local.py`.
- Ese supervisor:
  - fuerza `NEMESIS_LOCAL_SAFE_MODE=1`;
  - usa `OFFLINE_SAFE`;
  - fija `NEMESIS_LOCAL_EXTERNAL_AUTHORIZED=0`;
  - desactiva background jobs, auto-picks y auto-Telegram;
  - limpia secretos/credenciales externas del entorno local;
  - usa DB y estado bajo `data/local_dev`;
  - sirve en `127.0.0.1`, no en interfaz pública.
- Los endpoints Sentinel exigen:
  - sesión ADMIN con `user_id`;
  - `local_safe_mode_enabled()`;
  - `SENTINEL_JOBS_ENABLED=True`;
  - DB de jobs cuyo directorio padre sea exactamente `LOCAL_SAFE_DATA_DIR`;
  - fichero de store existente;
  - heartbeat de executor reciente para aceptar POST.
- POST exige CSRF.
- Acción y parámetros están cerrados a `product_surface_review / client_templates`.
- El worker fijo se ejecuta como:
  `product_experience_worker.py --static-only --no-write --dry-run`.
- Se valida la revisión de fuentes antes y después del child process.
- Errores del child/result handoff se saneán y no persisten secretos/rutas.
- Store usa idempotencia, claim token, lease y fencing; una ejecución interrumpida no revive ni acepta resultados tardíos.

## Tests ya integrados

La suite integrada cubre:
- acceso denegado a visitor/FREE/PRO/ELITE;
- aislamiento entre admins;
- CSRF;
- parámetros cerrados;
- GET sin escrituras operativas;
- executor ausente => 503;
- Sentinel deshabilitado => 503;
- double-click y concurrencia => un único job;
- persistencia entre reload/tabs;
- lease/fencing;
- fallo saneado sin retry automático;
- worker real en modo dry-run con `database_status=NOT_ACCESSED`.

## Evidencia productiva

- Render web arranca con `gunicorn app:app`, no con el supervisor local.
- Tras el deploy revisado no aparecen en logs:
  - `LOCAL_ONLY Sentinel HTTP ready`;
  - `sentinel_jobs`;
  - `executor_not_connected`;
  - `local_control_not_connected`.
- No se creó scheduler productivo nuevo para Sentinel.

## Decisión

`OPS-001` se considera **DONE en alcance LOCAL_SAFE**.

Esto NO significa que Sentinel sea un agente autónomo de producción.
No se autoriza:
- auto-fix productivo;
- auto-commit/push/merge/deploy;
- escritura en DB productiva;
- llamadas nuevas a proveedores;
- pagos;
- envíos Telegram fuera de los flujos existentes.

Siguiente prioridad: Sports Reality / Directos sobre el main actual, manteniendo verdad deportiva y proveedor real como gates separados.
