# V933 Sports Experience QA

## Superficies

Calendario, live, picks, detalle, historico, dashboard cliente y paneles admin de picks/partidos/datos.

## Reglas aplicadas

- Render desde DB/cache; ninguna llamada externa obligatoria al abrir pagina.
- Partido visible solo con identidad, fecha/hora, competicion y fuente validas.
- Live solo con estado, marcador, minuto y eventos recibidos.
- Pick publicable solo con partido, mercado, seleccion, cuota y estado validos.
- Resultado y ROI solo tras grading real.
- Registros incompletos quedan separados o bloqueados.
- Logos usan asset real disponible o fallback tipografico; no se inventan escudos.

## Estados vacios

Cliente recibe mensajes breves y acciones hacia calendario, live o picks. Admin conserva proveedor, ultima sync, cache, registros validos/incompletos y acciones protegidas.

## Validacion

Los checks V931/V932 confirman coherencia contador/lista, cero llamadas externas durante render, SQLite moderna/legacy/vacia/bloqueada y datos sinteticos confinados a fixtures. Sentinel reconoce los componentes deportivos V933 y termina con 0 incidencias.

