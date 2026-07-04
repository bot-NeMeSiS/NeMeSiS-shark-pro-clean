# V891/V893 Reference Visual Gap QA

## Resultado

Se crea `sentinel_reference_qa_engine.py` para comprobar si existen referencias visuales y para documentar cuando no hay Playwright/capturas reales disponibles.

## Comportamiento

- Si no hay capturas reales, genera incidencia de tipo `BROWSER_CAPTURE_UNAVAILABLE`.
- Si no encuentra referencias, genera incidencia de tipo `REFERENCE_IMAGES_MISSING`.
- No declara coincidencia visual perfecta sin evidencia.

## Estado esperado

La comparacion visual real debe ejecutarse despues de desplegar la version actual en Render y capturar pantalla PC/movil.
