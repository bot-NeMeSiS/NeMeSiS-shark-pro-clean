# V884 Client User Journey Flow QA

## Pantallas revisadas

- /
- /app
- /partidos
- /calendar
- /live
- /directo
- /picks
- /shark
- /telegram
- /profile
- /track-record
- /support

## Flujo esperado

El cliente debe entender rapido:

- que plan tiene;
- donde ver partidos;
- donde ver directos;
- donde ver picks;
- donde usar SHARK;
- donde conectar Telegram;
- donde revisar perfil, soporte y track record;
- que falta cuando no hay datos reales.

## Estado V884

- El worker funcional revisa rutas cliente y bloquea enlaces admin visibles.
- Las pantallas deportivas mantienen estados seguros cuando no hay filas reales.
- No se inventan partidos, picks, cuotas ni marcadores.
- SHARK y Telegram quedan tratados como valor de producto, no como promesas falsas.

## Riesgo detectado

- En local/Sentinel pueden seguir apareciendo avisos low cuando hay estado seguro pero no hay filas deportivas reales visibles. Eso es correcto: no se inventan datos, pero queda tarea de datos/sync/filtros.
