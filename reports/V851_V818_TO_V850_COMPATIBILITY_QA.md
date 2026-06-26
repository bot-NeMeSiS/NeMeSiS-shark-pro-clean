# V851 Compatibilidad V818-V850

## Preservado
- V818 master tick y health-check.
- V844 Telegram quality filter.
- V845 SHARK AI product assistant.
- V847 API-SPORTS provider guard.
- V850 live/crests/match detail.

## Método
Se añadió `tools/check_v851_v818_to_v850_compatibility.py`, que consulta `/api/runtime-version` mediante test client y valida flags de compatibilidad.

## Riesgo
Bajo: los cambios son de plantilla, CSS, versionado y checks. No se alteran engines de datos, pagos ni cron.
