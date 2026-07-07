# V904 Autonomous Workforce Input Inventory

Base usada: V903_TOTAL_SENTINEL_AUTO_FIX_RENDER_ALIGNMENT_AND_STABILITY_FINAL.

Render real antes de V904: V902B_DEPLOY_ALIGNMENT_AND_AUTOMATION_SECRET_ROTATION_GUARD_FINAL. No se declara V904 en producción hasta que `/api/runtime-version` lo confirme.

Entradas leídas:
- `data/runtime/sentinel_issues_memory.json`: memoria histórica disponible.
- `data/runtime/autonomous_company_sentinel/issues.json`: 0 issues activos actuales.
- `data/runtime/autonomous_company_sentinel/latest_run.json`: worker disponible.
- `data/runtime/autonomous_company_sentinel/reference_gap_report.json`: 14 gaps/issues visuales leídos.
- `data/runtime/autonomous_company_sentinel/outbox/codex_outbox.md`: outbox disponible.
- `reference_images/reference_manifest.json`: 16 imágenes reales de referencia.

Prioridad V904:
- Admin: dashboard, Autonomous Company Sentinel, Sentinel Issues y Codex Outbox.
- Cliente: `/app`, `/calendar`, `/live`, `/picks`, `/telegram`, `/shark`.
- Seguridad: no secretos, no Telegram real, no pagos reales, no DB destructiva.

Fuera por seguridad:
- Deploy/push automático.
- Rotación real de secretos.
- Pagos Stripe reales.
- Envíos Telegram reales.
- Migraciones destructivas o cambios en usuarios/sesiones.
