# V800 Client Reference Screen QA Checklist

## Cliente
- Home muestra foco principal si hay partido real; si no, estado vacío bonito.
- App Center mantiene la ruta Partido → Pick → SHARK.
- Calendario enlaza cada partido a `/match/<id>` y mantiene SHARK por partido.
- Directo muestra ticker con partidos reales o estado vacío si no hay live.
- Picks explica qué apostar, motivo y riesgo solo con datos del pick.
- Detalle de partido no inventa confianza: usa pick real o muestra `—`.
- Mi cuenta muestra cerrar sesión visible.
- Telegram cliente muestra vinculación/estado real o pendiente.

## Datos reales
- No usar porcentajes, cuotas, ROI, forma o resultados mock.
- No rellenar campos deportivos si la API/DB no los tiene.
- Mostrar `Pendiente`, `—`, `Sin pick`, `Esperando sincronización` cuando toque.

## Producción
- Confirmar en Render `/api/runtime-version` con V800.
- Probar `/app`, `/calendar`, `/live`, `/picks`, `/match/<id>`, `/mi-cuenta`, `/telegram`.
- Confirmar que Telegram/Cron sigue protegido por `AUTOMATION_SECRET`.
