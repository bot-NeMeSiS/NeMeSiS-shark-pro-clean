# V912 Public Copy Spanish Polish QA

## Objetivo

Pulir copy público visible en español sin tocar rutas, datos, pagos ni secretos.

## Correcciones aplicadas

- `La app gua al cliente` -> `La app guía al cliente`.
- `Informacion deportiva` -> `Información deportiva`.
- `Terminos` -> `Términos`.
- `garantías` y `análisis` normalizados en portada.

## Archivos

- `templates/home.html`
- `templates/base.html`

## Validación

El check V912 valida:

- Home no contiene `gua al cliente`.
- Home contiene `La app guía al cliente`.
- Footer no contiene `Informacion` ni `Terminos`.
- Footer contiene `Información deportiva` y `Términos`.
