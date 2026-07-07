# V902 Stale False Positive Reconciliation QA

Objetivo: no borrar historia, sino marcar la verdad actual.

Acciones:
- Se añadió `tools/reconcile_v902_sentinel_truth.py`.
- Cada issue conserva historial y recibe `last_revalidated_version`, `last_revalidated_at_madrid`, `active_now` y `v902_truth_note`.
- Las incidencias no reproducibles pasaron a `RESOLVED_BY_RESCAN`.
- Las brechas visuales se mantienen como `VISUAL_REFERENCE_PENDING_BROWSER_QA`.

Falsos positivos:
- No se eliminaron registros.
- No se ocultaron errores activos.
- Los avisos de configuración pendiente se tratan como estado operativo seguro cuando la UI no promete lo contrario.

