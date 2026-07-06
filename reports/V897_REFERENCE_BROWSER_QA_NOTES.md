# V897 Reference Images And Browser QA Notes

## Referencias visuales

Carpeta oficial:

`reference_images/`

README:

`reference_images/README.md`

Si no hay imágenes objetivo, Sentinel debe reportar `REFERENCE_IMAGES_MISSING` y no declarar comparación visual real.

## Browser QA opcional

Herramienta:

`tools/run_browser_reference_qa.py`

Uso recomendado con servidor local arrancado:

`python tools/run_browser_reference_qa.py --base-url http://127.0.0.1:5000`

Rutas incluidas:

- `/`
- `/cliente-login`
- `/app`
- `/calendar`
- `/live`
- `/picks`
- `/admin-login`
- `/admin/autonomous-company-sentinel`

Capturas:

`reports/browser_qa/`

Si Playwright no está instalado, la herramienta no falla: genera reporte indicando que el browser no está disponible.

