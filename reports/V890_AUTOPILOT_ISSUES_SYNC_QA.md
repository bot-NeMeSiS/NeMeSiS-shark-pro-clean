# V890/V892 AutoPilot Issues Sync QA

Se integro sincronizacion segura desde AutoPilot y Visual Worker:

- `POST /api/admin/sentinel/issues/sync-autopilot`
- `POST /api/admin/sentinel/issues/sync-visual-worker`

Ambos endpoints requieren sesion admin. Sin sesion devuelven `403`.

La sincronizacion:

- lee hallazgos existentes;
- normaliza estructura;
- calcula fingerprint;
- deduplica;
- incrementa `occurrences` si reaparece;
- marca `REOPENED` si algo resuelto vuelve a verse;
- no borra memoria AutoPilot;
- no ejecuta acciones peligrosas.
