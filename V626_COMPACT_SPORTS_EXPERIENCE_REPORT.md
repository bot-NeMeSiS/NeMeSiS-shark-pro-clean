# V626 COMPACT SPORTS EXPERIENCE

## Objetivo

Compactar la experiencia deportiva para mostrar más partidos, resultados y directos por pantalla, manteniendo la inteligencia SHARK existente y sin tocar Telegram, Warehouse ni motores SHARK.

## Mejoras aplicadas

- Actualizada la versión a `V626_COMPACT_SPORTS_EXPERIENCE`.
- Calendario convertido a lista deportiva compacta con escudos, hora/minuto, marcador, competición, estado y acceso directo al detalle.
- Live convertido a formato tipo marcador: local, marcador, visitante, minuto, estado y SHARK compacto.
- Añadido selector `Vista compacta / Vista detallada` en calendario y Live.
- La vista detallada de Live conserva momentum, riesgo y alertas SHARK sin ocupar espacio en la vista compacta.
- Favoritos usa ahora filas deportivas compactas para partidos relacionados.
- Perfil cliente muestra origen de membresía, fecha de expiración y días restantes.
- Admin de usuarios permite asignar membresías FREE / PRO / ELITE / ADMIN con duración 7, 15, 30, 60, 90 días o fecha personalizada.
- Si una membresía temporal caduca, el sistema la rebaja automáticamente a FREE.
- Añadidas columnas SQLite seguras: `membership_source`, `membership_start_date`, `membership_end_date`.
- Limpieza de textos corruptos visibles en las plantillas tocadas.

## Reducción visual conseguida

- Las tarjetas deportivas pasan de bloques altos a filas compactas de unos 54-68 px.
- Se sustituyen grids de tarjetas por listas densas en calendario, Live y favoritos.
- Los KPIs de Live se reducen y ocupan menos altura.
- En móvil se mantiene una fila compacta con hora, equipos, marcador y estado.

## Pantallas compactadas

- `/calendar`
- `/live`
- `/favorites`
- `/perfil`
- `/admin/users`

## Pruebas

- `python -m compileall app.py engines database_manager.py`: OK.
- Smoke test Flask con base temporal:
  - `/`, `/login`, `/admin-login`, `/registro`, `/picks`, `/live`, `/calendar`: 200.
  - `/perfil`, `/favorites`, `/admin/dashboard` sin sesión: 302 esperado.
  - Registro cliente: 302 esperado.
  - Login cliente: 302 esperado.
  - `/perfil`, `/favorites`, `/live`, `/calendar` con cliente: 200.
  - Login admin: 302 esperado.
  - `/admin/dashboard`, `/admin/users` con admin: 200.
  - Cambio temporal a PRO 7 días: OK.
  - Observability errors: 0.

## Pendiente real

- Validar visualmente en móvil real con datos deportivos abundantes.
- Confirmar en Render que la base persistente recibe las nuevas columnas sin incidencias.
