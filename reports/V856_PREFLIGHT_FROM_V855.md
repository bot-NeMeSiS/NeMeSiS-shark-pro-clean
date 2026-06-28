# V856 Preflight Desde V855

## Fuente real
- Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`.
- Base detectada antes de aplicar V856: `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`.
- ZIP V855 detectado: `release_output/NeMeSiS_SHARK_PRO_V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL_RENDER_READY.zip`.
- No se usó el ZIP viejo V827 ni `NeMeSiS shark pro.zip` como base.
- No se trabajó sobre carpeta anidada.
- No se tocaron secretos ni `.env` reales.

## Continuidad comprobada
- `VERSION.txt` estaba en V855 antes del cambio.
- `APP_VERSION` estaba en V855 antes del cambio.
- `/api/runtime-version` ya exponía flags de V855 y compatibilidad V818/V844/V845/V847/V850/V853/V854.
- Reportes V855 presentes.
- Check V855 presente: `tools/check_v855_full_ecosystem_reference_rebuild.py`.
- Build limpio presente: `tools/build_clean_release.py`.
- Auditoría ZIP presente: `tools/audit_release_zip.py`.

## Rutas y sistemas base
- Cliente: `/`, `/cliente-login`, `/registro`, `/app`, `/inicio`, `/panel-cliente`, `/partidos`, `/calendar`, `/live`, `/directo`, `/picks`, `/shark`, `/telegram`, `/profile`, `/support`, `/track-record`.
- Admin: `/admin/dashboard`, `/admin/control-center`, `/admin/data-center`, `/admin/api-sports`, `/admin/api-sports-audit`, `/admin/telegram/command-center`, `/admin/shark-ai`, `/admin/daily-automation`, `/admin/users`, `/admin/memberships`, `/admin/payments`.
- APIs críticas: `/api/runtime-version`, `/api/automation/master-tick`, `/api/automation/health-check`, `/api/shark/ask`.

## Decisión de V856
V856 se aplica como segunda pasada controlada sobre V855: capa visual más dura, motores de presentación puros, checks nuevos y documentación. No cambia `DB_PATH`, no fuerza llamadas API y no inventa datos.
