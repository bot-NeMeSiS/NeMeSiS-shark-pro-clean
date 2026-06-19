# V816 Routes Links Navigation QA

## Check

`tools/check_v816_routes_links_navigation.py`

## Resultado esperado

Valida:

- rutas cliente criticas;
- rutas admin criticas;
- enlaces core en `base.html`;
- cache-busting CSS V816;
- runtime V816;
- ausencia de hrefs sospechosos `None`/`undefined`;
- SHARK sin duplicacion por CSS/base.
