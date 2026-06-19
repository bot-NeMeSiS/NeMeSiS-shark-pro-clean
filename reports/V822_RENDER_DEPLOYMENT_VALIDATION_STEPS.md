# V822 Render Deployment Validation Steps

## Despues de subir el ZIP

1. Desplegar `NeMeSiS_SHARK_PRO_V822_PRODUCTION_STABILITY_RUNTIME_AUTOMATION_CRESTS_FINAL_RENDER_READY.zip`.
2. Abrir `/api/runtime-version` y confirmar `version=V822_PRODUCTION_STABILITY_RUNTIME_AUTOMATION_CRESTS_FINAL`.
3. Confirmar:
   - `has_v821_hotfix=true`
   - `has_v820_crests=true`
   - `has_v819_dedup=true`
   - `has_v818_automation=true`
   - `last_502_hotfix=true`
4. Abrir `/cliente-login`.
5. Abrir `/app`.
6. Abrir `/asset/team-logo/test`.
7. Ejecutar `/api/automation/master-tick?secret=AUTOMATION_SECRET&dry_run=1`.
8. Ejecutar `/api/automation/health-check?secret=AUTOMATION_SECRET`.

## Exito esperado

Sin 500/502, sin timeout y sin errores de SQLite locked en Render logs.
