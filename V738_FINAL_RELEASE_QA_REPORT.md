# V738 Final Release QA Report

## Resumen

- Versión: `V738_FINAL_COMMERCIAL_RELEASE_CANDIDATE_POLISH`
- Estado local: `FINAL_STATIC_READY_RENDER_VALIDATION_PENDING`
- Puertas estáticas principales: OK
- Visual global V736: OK
- App Feel V737: OK
- Final Release Center V738: OK
- Horarios Madrid: OK en selftest verano/invierno

## Plan final de validación en Render

1. **Subir ZIP final a GitHub/Render** — Desplegar la release final y esperar build verde.
2. **Verificar versión** — Abrir /api/runtime-version y confirmar V738_FINAL_COMMERCIAL_RELEASE_CANDIDATE_POLISH.
3. **Probar salud y seguridad** — Abrir /api/health, login cliente, login admin, CSRF/rate limit y centros admin.
4. **Confirmar horarios Madrid** — Revisar Calendar, Live, Picks, Match Detail y Telegram con un partido de hora conocida.
5. **Confirmar Telegram real** — Usar /admin/telegram/command-center, dry-run y test-send manual solo si procede.
6. **Confirmar persistencia** — Verificar DB_PATH=/data/database.db, usuarios siguen tras redeploy y Data Memory crece.
7. **QA móvil** — Probar iPhone/Android/PWA con FREE, PRO y ELITE para navegación inferior, SHARK y formularios.
8. **Abrir beta controlada** — Solo con Telegram, DB, horarios y login validados durante varios días.

## Nota

No se deben abrir usuarios externos hasta confirmar en Render real: versión, health, login, DB persistente, Cron 403/200, Telegram real y Data Memory.
