# V731 Client Experience QA Report

- Estado: **OK**
- Score: **100/100**
- Templates cliente escaneados: 17
- Avisos totales: 13
- Avisos importantes: 0

## Pantallas críticas
- `/` · `home.html`: OK · Hora Madrid: sí · Estado vacío: sí
- `/dashboard` · `client_overview.html`: OK · Hora Madrid: sí · Estado vacío: sí
- `/sports-hub` · `sports_hub.html`: OK · Hora Madrid: sí · Estado vacío: sí
- `/live` · `live.html`: OK · Hora Madrid: sí · Estado vacío: sí
- `/calendar` · `calendar.html`: OK · Hora Madrid: sí · Estado vacío: sí
- `/picks` · `picks.html`: OK · Hora Madrid: sí · Estado vacío: sí
- `/combis` · `combis.html`: OK · Hora Madrid: sí · Estado vacío: sí
- `/shark` · `shark.html`: OK · Hora Madrid: revisar · Estado vacío: sí
- `/telegram` · `telegram.html`: OK · Hora Madrid: revisar · Estado vacío: revisar
- `/favorites` · `favorites.html`: OK · Hora Madrid: sí · Estado vacío: sí
- `/perfil` · `profile.html`: OK · Hora Madrid: revisar · Estado vacío: sí
- `/membership` · `membership.html`: OK · Hora Madrid: revisar · Estado vacío: sí
- `/match/<id>` · `match_detail.html`: OK · Hora Madrid: sí · Estado vacío: sí

## Siguiente acción recomendada
- Mantener QA visual con capturas reales de móvil/desktop tras desplegar.

## Primeros avisos
- INFO · texto_tecnico · `calendar.html`:48 · `None` — Revisar que este texto no sea visible al cliente final.
- INFO · microcopy · `client_overview.html`:11 · `Live` — Usar Directo cuando sea texto visible al cliente.
- INFO · texto_tecnico · `combis.html`:73 · `None` — Revisar que este texto no sea visible al cliente final.
- INFO · texto_tecnico · `daily_briefing.html`:64 · `None` — Revisar que este texto no sea visible al cliente final.
- INFO · texto_tecnico · `favorites.html`:28 · `None` — Revisar que este texto no sea visible al cliente final.
- INFO · microcopy · `favorites.html`:38 · `Live` — Usar Directo cuando sea texto visible al cliente.
- INFO · texto_tecnico · `home.html`:86 · `None` — Revisar que este texto no sea visible al cliente final.
- INFO · texto_tecnico · `live.html`:40 · `None` — Revisar que este texto no sea visible al cliente final.
- INFO · texto_tecnico · `match_detail.html`:39 · `None` — Revisar que este texto no sea visible al cliente final.
- INFO · texto_tecnico · `match_hub.html`:66 · `None` — Revisar que este texto no sea visible al cliente final.
- INFO · texto_tecnico · `picks.html`:52 · `None` — Revisar que este texto no sea visible al cliente final.
- INFO · texto_tecnico · `sports_hub.html`:52 · `None` — Revisar que este texto no sea visible al cliente final.
- INFO · texto_tecnico · `team_detail.html`:6 · `None` — Revisar que este texto no sea visible al cliente final.

## Notas
- Este control es estático y conservador: no sustituye la revisión visual real en móvil/desktop.
- El objetivo es detectar señales de riesgo antes de publicar, sin modificar datos ni enviar Telegram.
