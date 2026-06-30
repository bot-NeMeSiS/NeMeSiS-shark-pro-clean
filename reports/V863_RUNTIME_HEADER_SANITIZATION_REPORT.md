# V863 Runtime Header Sanitization Report

## Problema real detectado

El runtime público V862 mostraba:

`Invalid header value b'386760cfa00b37f98d680113043f9768\n'`

## Corrección aplicada

- Se añadió `sanitize_http_header_value`.
- Se añadió `sanitize_runtime_value`.
- Se sanitizan cabeceras salientes en `after_request`.
- `/api/runtime-version` sanea recursivamente el snapshot de estabilidad antes de serializar.
- Los saltos de línea en valores de runtime se convierten en texto seguro.

## Validación local

`tools/check_v863_runtime_header_sanitization.py` valida que las cabeceras de `/api/runtime-version` no contienen `\n` ni `\r`.
