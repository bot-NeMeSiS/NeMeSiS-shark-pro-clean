# V932 Next Steps

1. Subir el contenido interno de `release_output/V932_DEPLOY_ROOT_CONTENTS` a la raiz de `main`.
2. Confirmar que `app.py`, `VERSION.txt`, `requirements.txt`, `templates/`, `static/`, `engines/` y `tools/` quedan directamente en la raiz.
3. Esperar el auto-deploy de Render o ejecutar el mecanismo de deploy ya autorizado, sin exponer hooks.
4. Comprobar `/api/runtime-version` hasta obtener V932, archivos de version alineados, cache busting activo y `NEMESIS_CACHE_V932`.
5. Usar una cuenta cliente de prueba real autorizada para capturar `/app`, calendario, live, picks, historico, perfil, Telegram y membresias.
6. Usar una cuenta admin de prueba autorizada para capturar dashboard, usuarios, pagos, picks, datos, Telegram, Workforce, Sentinel y navegacion.
7. Probar login, redirect interno, favoritos y logout sin modificar usuarios o pagos reales.
8. Si no hay agenda real, revisar en admin la ultima sync y ejecutar solo la sincronizacion protegida autorizada.

Proxima accion: desplegar V932 y realizar Browser QA autenticado con una cuenta de prueba autorizada. No declarar V932 en produccion ni cerrar QA visual hasta que Render y las capturas lo confirmen.
