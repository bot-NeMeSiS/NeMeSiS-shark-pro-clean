# V866 header invalid value hotfix

## Problema detectado
Render devolvía runtime 200, pero `last_error` incluía un salto de línea dentro del texto del error de cabecera inválida.

## Corrección aplicada
- Se añadió `sanitize_runtime_error_value`.
- `v822_runtime_stability_snapshot()` sanea `last_error` del proveedor.
- `/api/runtime-version` vuelve a sanear `runtime_stability.last_error` antes de responder.
- Se mantiene el error como diagnóstico, pero sin caracteres de cabecera peligrosos.

## Criterio
- No ocultar errores reales.
- No exponer secretos.
- No permitir `\n`/`\r` reales ni literales en `last_error` de runtime.
