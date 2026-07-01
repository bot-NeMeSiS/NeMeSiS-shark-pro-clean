# V875 Real Runtime Header Error QA

## Producción

Render V855 sigue reportando:

`Invalid header value b'386760cfa00b37f98d680113043f9768\n'`

## Local

Local V874/V875 mantiene:

- `sanitize_http_header_value`
- `sanitize_runtime_error_value`
- `runtime_error_state`
- saneado de `last_error`
- no exposición de bytes crudos en runtime local.

## Conclusión

El error real no puede darse por resuelto en producción hasta desplegar V875 y volver a consultar runtime.

