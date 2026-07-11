# V933 Performance QA

## Controles

- CSS V933 separado en tokens y producto, cargado con query de version.
- Service worker actualizado a `NEMESIS_CACHE_V933`.
- HTML y CSS antiguos no se sirven desde el cache V932 tras activar el nuevo worker.
- Browser QA bloquea service workers para revisar assets actuales.
- Las vistas deportivas no llaman proveedores externos durante render.
- DB bloqueada responde de forma acotada y sin bloqueo persistente.
- Iconos se reutilizan desde el sistema existente; no se añadieron librerias pesadas.

`tools/check_v933_performance.py` paso. Las 224 navegaciones completaron sin timeout, 500 ni 502 en el entorno local de QA.

## Limite

No se obtuvo una medicion Lighthouse de Render; latencia de red, cold start y proveedores deben medirse post-deploy.

