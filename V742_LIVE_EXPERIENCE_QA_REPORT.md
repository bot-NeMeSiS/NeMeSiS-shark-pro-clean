# V742 Live Experience QA Report

## Cambios

- `/live` se convierte en centro Live filtrable.
- Alias añadidos: `/directo`, `/en-directo`.
- Buscador por equipo, liga o país.
- Filtros: En directo, Hoy, Próximos, Finalizados, Con pick, Favoritos, España, Andalucía y Grandes ligas.
- Ordenación por relevancia deportiva y hora Madrid.
- Estados claros: En directo, Finalizado, Próximo y estados derivados si están sincronizados.
- No se inventa minuto ni marcador.
- Añadido panel admin `/admin/live-experience` para revisar Live, Hoy, Próximos, Finalizados, Con pick y Favoritos desde una fuente deduplicada.
- Añadida API `/api/admin/live-experience`.

## QA

- `tools/check_v742_live_experience.py`: OK.
- Smoke Flask: `/live`, `/directo`, `/admin/live-experience` y `/api/admin/live-experience` sin 500.
- Muestra de prueba:
  - un partido live detectado;
  - un próximo detectado;
  - filtro live devuelve solo el directo.

## Riesgo pendiente

La calidad visual final depende de datos reales de Render y revisión móvil manual.
