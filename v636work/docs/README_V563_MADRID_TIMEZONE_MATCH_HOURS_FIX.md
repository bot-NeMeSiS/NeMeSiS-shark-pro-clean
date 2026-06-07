V563 — Madrid Timezone Match Hours Fix

- Normaliza horarios externos a Europe/Madrid.
- The Odds API UTC/Z se convierte a hora española.
- TheSportsDB strTimestamp/dateEvent+strTime se muestra como hora española.
- Añade /api/timezone-check.
- Migra partidos existentes con kickoff_iso al arrancar sin borrar DB.
- Mantiene V562 completo.
