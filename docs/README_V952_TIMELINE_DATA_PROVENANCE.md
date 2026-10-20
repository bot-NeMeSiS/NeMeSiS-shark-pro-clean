# V952 — procedencia visible de la cronología

## Cambio

La cronología de la ficha de partido muestra al cliente la fuente deportiva
registrada y la hora más reciente de captura de los eventos que forman esa
cronología. La hora se deriva de `source_timestamp` o `timestamp` de los eventos
canónicos guardados y se valida con el parser de fechas ya usado por el Match
Center.

Si no hay una hora válida, la pantalla informa que no está disponible. Los
identificadores de fuente desconocidos se presentan de forma genérica para no
exponer etiquetas internas como si fueran nombres de proveedores. Si hay varias
fuentes en los eventos, se indica que la cronología tiene varias fuentes.

## Límites

- No se realizan llamadas al proveedor desde la página.
- No se escriben ni modifican datos.
- La hora indica la última captura guardada entre los eventos mostrados; no es
  garantía de que el feed siga actualizado en este instante.
- No se sustituye la marca ausente por la hora del marcador ni por la hora del
  servidor.

## Validación

La regresión comprueba fuente y marca más recientes, la representación visible,
la ausencia de fecha fabricada y el contrato de lectura sin E/S del Match Center.
