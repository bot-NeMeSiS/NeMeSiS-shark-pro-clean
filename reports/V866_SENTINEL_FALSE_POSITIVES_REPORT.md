# V866 Sentinel false positives report

## Falso positivo detectado
La regla anterior revisaba `none`, `null` y `undefined` en todo el HTML.

## Riesgo
El admin workflow recibía incidencias low repetidas aunque el texto no estuviera visible al cliente.

## Ajuste
El Sentinel ahora limpia scripts, estilos, SVG, templates, comentarios y etiquetas antes de revisar tokens técnicos visibles.

## Mantiene alertas
Si `None`, `null` o `undefined` aparecen en texto visible real, Sentinel seguirá abriendo issue low.
