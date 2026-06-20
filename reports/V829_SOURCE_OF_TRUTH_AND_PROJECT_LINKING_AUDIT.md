# V829 Source Of Truth And Project Linking Audit

## Fuente real usada

- Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`.
- Versión detectada antes de tocar: `V828_REFERENCE_PIXEL_PARITY_FULL_ECOSYSTEM_FINAL`.
- Nueva versión aplicada: `V829_MOBILE_LINKED_ECOSYSTEM_FINAL_APP_EXPERIENCE`.
- No se usó ningún ZIP subido al chat como base.
- El ZIP limpio más reciente antes de V829 era el release V828 en `release_output`.

## ZIPs antiguos

Existen ZIPs y referencias históricas, pero no se usan como fuente porque pueden contener `.git`, `.venv`, cachés, DBs locales, logs, `release_output` viejo o proyecto anidado. Solo se consideran diagnóstico si hiciera falta.

## Limpieza local y release

La carpeta de trabajo conserva `.git`, `.venv`, `.pytest_cache`, `__pycache__` y `release_output` porque son parte del entorno local/desarrollo. El builder de release los excluye del ZIP final.

## Git/GitHub

`git` no está disponible en PATH durante esta ejecución. No se hizo commit ni push automático. El ZIP final queda listo para subir o para que GitHub Desktop detecte cambios en la carpeta oficial.

## Render-ready

Archivos detectados:

- `Procfile`.
- `render.yaml`.
- `requirements.txt`.
- `runtime.txt`.
- `.env.example`.
- `.env.render.clean`.

## Rutas críticas detectadas

Cliente: `/`, `/cliente-login`, `/registro`, `/app`, `/calendar`, `/partidos`, `/live`, `/directo`, `/picks`, `/match/<id>`, `/shark`, `/shark-core`, `/profile`, `/telegram`, `/support`, `/favorites`, `/track-record`, `/combis`, `/mercados`, `/highlights`.

Admin: `/admin/dashboard`, `/admin/map`, `/admin/daily-automation`, `/admin/automation-os`, `/admin/data-center`, `/admin/telegram/command-center`, `/admin/users`, `/admin/memberships`, `/admin/payments`, `/admin/final-certification`.

APIs: `/api/runtime-version`, `/api/automation/master-tick`, `/api/automation/health-check`.

## Se preserva

V818 master tick, V819 dedup, V820 crests, V821 hotfix 502, V822 stability, V825 identidad SHARK, V827 design system, V828 paridad visual, Telegram automático, Render Cron, DB_PATH, Madrid Time, usuarios, sesiones, membresías, pagos, picks, live y sistema de escudos.
