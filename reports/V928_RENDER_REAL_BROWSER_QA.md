# V928 Render Real Browser QA

## Matriz

- Desktop: 1366x768, 1440x900, 1600x900 y 1920x1080.
- Mobile: 390x844 y 430x932.
- Rutas base: 26.
- Detalle real adicional: `/match/sportsdb-355afc23669c970bab`.

## Evidencia

- Matriz base: 156 intentos.
- Primer recorrido: 155 capturas, 132 respuestas 200, 23 respuestas 502 y 1 timeout en `/live`.
- Reintento `/live` 1366x768: 200, 17.802 ms, sin overflow.
- Detalle real: 6/6 respuestas 200, sin overflow; tiempos entre 6.223 y 12.478 ms.
- Total de PNG guardados: 162.
- Capturas de aplicacion con respuesta 200: 139.
- Capturas que documentan el 502 transitorio: 23.
- Overflow horizontal detectado en capturas validas: 0.

Una segunda sonda pausada devolvio 200 en 12/12 rutas, confirmando recuperacion del servicio, pero `/calendar`, `/live`, `/picks`, `/track-record` y `/memberships` siguieron tardando entre 9 y 23 segundos. La causa encontrada fue sincronizacion externa durante render cuando la cache caducaba.

Las capturas estan en `reports/V928_render_real_browser_qa/`. El JSON original se conserva sin reescribir para no ocultar el timeout ni los 502.

No se declara pixel-perfect; la inspeccion humana sigue siendo obligatoria.
