# V928 Next Steps

1. Subir el contenido interno de `release_output/V928_DEPLOY_ROOT_CONTENTS` a la raiz de `main`; no subir la carpeta padre.
2. Confirmar que `app.py`, `VERSION.txt`, `requirements.txt`, `templates/`, `static/`, `engines/` y `tools/` quedan directamente en la raiz del repositorio.
3. Esperar el deploy de Render sin disparar Telegram, pagos ni tareas destructivas.
4. Consultar `/api/runtime-version` hasta obtener V928, `version_files_match=true`, `deployment_alignment_status=aligned_local_files` y `static_css_cache_busting=true`.
5. Forzar una recarga una vez para retirar cualquier service worker anterior y comprobar que el cache activo es `NEMESIS_CACHE_V928`.
6. Grabar video desktop y movil revisando home, app, partidos, live, picks, detalle real disponible, historico, planes, cuenta, Telegram y SHARK.
7. Revisar admin dashboard, Telegram, pagos, usuarios, picks, datos, Workforce, Sentinel, outbox y lanzamiento real.
8. Validar especialmente textos largos, filtros, acciones tactiles, fallbacks de escudo y estados vacios con datos reales de produccion.

No declarar equivalencia pixel a pixel hasta completar la revision humana de capturas y video.
