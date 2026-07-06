# V898 Production 404 PWA Reference Outbox Truth

Versión local:

`V898_PRODUCTION_404_PWA_REFERENCE_OUTBOX_TRUTH_FINAL`

## Render real

Producción consultada en:

`https://bot-apuestas-crgf.onrender.com/api/runtime-version`

Resultado observado el 2026-07-06:

`V896_PRODUCTION_NOT_FOUND_ROUTE_RECOVERY_FULL_APP_SMOKE_FINAL`

Conclusión: producción ya no muestra el Not Found seco de Flask; sirve la recuperación premium V896. V898 prepara el siguiente deploy para cerrar PWA/cache, referencias y outbox.

## Correcciones

- 404 premium muestra ruta solicitada saneada.
- 404 añade botón `Restablecer app/PWA`.
- Service worker sube a `NEMESIS_CACHE_V898`.
- Service worker no cachea ni sirve 404 antiguo.
- `/admin/not-found-events` permite revisar eventos Not Found en panel admin.
- `/api/admin/not-found-events` sigue protegida sin sesión.
- `reference_images/` entra en el build limpio.
- `reference_images/reference_manifest.json` preparado.
- Codex outbox separa prompts activos de `Prompts archivados / obsoletos`.
- Autonomous Company Sentinel separa `active_issues_open`, `stale_issues`, `resolved_by_rescan` y `archived_prompts`.

## Seguridad

No se tocaron secretos, DB real, usuarios, pagos, envíos Telegram ni datos deportivos reales.

