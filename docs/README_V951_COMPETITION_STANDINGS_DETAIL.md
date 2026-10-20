# V951 — Clasificación de competición, datos completos y lectura móvil

V951 mejora la tabla de clasificación que se muestra en las fichas de competición.

## Alcance

- Presenta PJ, ganados, empatados, perdidos, goles a favor, goles en contra,
  diferencia, puntos, forma y estado cuando esos campos existen en la tabla
  sincronizada, junto con su hora guardada de actualización cuando está disponible.
- Reutiliza un escudo ya asociado a un equipo de la misma competición solo cuando
  el nombre normalizado identifica una única ficha. Si hay homónimos, no asigna
  uno por aproximación.
- El filtro de escudos existente valida la URL y conserva el recurso gráfico de
  sustitución cuando no hay una imagen válida.
- En móvil deja visibles posición, equipo, partidos jugados, diferencia y puntos;
  el resto se puede abrir por equipo mediante controles nativos de teclado.
- Incrementa la versión de la app y del caché estático a `V951_COMPETITION_STANDINGS_DETAIL`.

## Límites

- La tabla sigue dependiendo de los datos recibidos y sincronizados por la
  plataforma. V951 no crea clasificaciones a partir de calendarios parciales.
- No añade llamadas a proveedores, escrituras de base de datos, reglas de acceso,
  contenido de apuestas ni datos deportivos nuevos.
- Una fila sin valor de origen se presenta como no disponible.
- El código local y las pruebas no demuestran que V951 esté publicado en Render.

## Verificación

Ejecutar `tests/test_competition_center_premium_experience.py` y
`tests/test_admin_master_release.py`, además de las regresiones de página de
competición. La integración y el despliegue se validan por separado contra el SHA
que esté activo en Render.
