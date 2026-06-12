# NeMeSiS SHARK PRO — V570 SHARK INTELLIGENCE CORE

Avance aplicado sobre el ZIP real subido por el usuario.

## Incluye
- Nueva ruta cliente `/shark-core`.
- Alias `/inteligencia` hacia el núcleo SHARK.
- Nuevo panel admin `/admin/shark-center`.
- APIs:
  - `/api/shark/core-summary`
  - `/api/admin/shark-center`
  - `/api/system/v570-check`
- Nuevo engine `engines/shark_intelligence_core.py`.
- Tabla persistente `shark_memory` para preparar memoria futura.
- SHARK conectado a favoritos, picks, recomendaciones, live y próximos partidos.
- Preguntas rápidas según membresía FREE / PRO / ELITE.
- CSS responsive añadido.
- `app.py` compila OK.
- Engines compilan OK.

## Nota
No se inventan picks, cuotas, marcadores ni eventos. SHARK resume y prioriza los datos reales/cacheados disponibles.
