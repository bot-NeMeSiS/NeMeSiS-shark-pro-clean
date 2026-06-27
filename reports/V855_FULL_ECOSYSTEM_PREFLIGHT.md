# V855 Full Ecosystem Preflight

Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`.

Base real confirmada antes de cambios:
- VERSION.txt: V854_CLIENT_ADMIN_REAL_RENDER_FINAL_POLISH_AND_PRODUCT_QA.
- APP_VERSION: V854_CLIENT_ADMIN_REAL_RENDER_FINAL_POLISH_AND_PRODUCT_QA.
- Runtime local: V854 con flags V853, V850, V847, V845, V844 y V818 activos.

No se usó ZIP viejo V827 ni `NeMeSiS shark pro.zip` como base.

Estructura detectada:
- Templates cliente y admin disponibles.
- Engines de Telegram, SHARK, API-SPORTS, live, escudos y experiencia disponibles.
- `build_clean_release.py` y `audit_release_zip.py` disponibles.
- La carpeta contiene `.git`, `.venv`, cachés y `release_output`, pero no son base de trabajo y quedan excluidos por release.

Rutas críticas existentes o enlazadas:
- Cliente: `/`, `/cliente-login`, `/registro`, `/app`, `/partidos`, `/calendar`, `/live`, `/directo`, `/picks`, `/shark`, `/telegram`, `/profile`, `/support`, `/track-record`.
- Admin: `/admin/dashboard`, `/admin/control-center`, `/admin/data-center`, `/admin/api-sports`, `/admin/api-sports-audit`, `/admin/telegram/command-center`, `/admin/shark-ai`, `/admin/daily-automation`, `/admin/users`, `/admin/memberships`, `/admin/payments`.
