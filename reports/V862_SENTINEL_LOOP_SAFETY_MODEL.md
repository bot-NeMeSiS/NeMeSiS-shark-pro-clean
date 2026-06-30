# V862 Sentinel Loop Safety Model

## Reglas

- No modifica código automáticamente.
- No hace deploy.
- No toca secretos.
- No borra DB ni usuarios.
- No cambia pagos reales.
- No envía Telegram masivo.
- No llama APIs caras.
- No inventa datos.

## Niveles

- Level 1 Diagnostic: detectar, reportar, priorizar, generar prompt.
- Level 2 Safe Internal Fix: limpiar caché propia, marcar issue revisado, regenerar reporte, deduplicar incidencias, recalcular score interno.
- Level 3 Approval Required: sync, Telegram test, picks, membresías, release, cambios visuales/templates/CSS.
- Level 4 Forbidden Automatic: código en producción, deploy, secretos, DB, usuarios, pagos reales, Telegram masivo, fake data.
