# V617 — Full Project Audit & Clean Build

## Base auditada
- Base detectada: `V616_FINAL_STABILITY_RENDER_SMOKE_READY`.
- Objetivo: consolidar un paquete limpio, verificar estructura crítica y evitar retrocesos sobre los arreglos V611–V616.

## Comprobaciones realizadas
- `python -m compileall app.py engines database_manager.py`: OK.
- `rows()` no llama a `seed_core()`.
- `execute()` no llama a `seed_core()` ni `init_db()`.
- `create_user()` no llama a `seed_core()`.
- `default_profile()` no llama a `seed_core()`.
- `/` no llama a `dashboard_data()`.
- `/api/health` no llama a `dashboard_data()` ni `seed_core()`.
- Rutas Flask detectadas sin duplicados.
- Plantillas referenciadas por `render_template()` encontradas.
- Plantillas de observabilidad presentes.
- Búsqueda de mojibake UTF-8 común: 0 restos detectados.

## Limpieza del paquete
El ZIP final excluye:
- `.git`
- `__pycache__`
- ficheros `.pyc/.pyo`
- bases de datos locales
- logs
- ZIPs internos
- patches internos
- archivos temporales del sistema

## Nota de validación
El entorno local de este chat no tiene Flask instalado, por lo que no se ejecutó Flask test client. La validación fuerte realizada aquí es estática y de compilación. La prueba final debe hacerse en Render revisando:
- `/api/health`
- `/api/runtime-version`
- `/api/startup-check`
- `/`
- `/login`
- `/admin-login`
- `/picks`
- `/live`
- `/calendar`
- `/admin/observability/errors`

## Resultado
Paquete limpio preparado para subir a GitHub/Render sin basura acumulada y sin tocar funcionalidades críticas.
