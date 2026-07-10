# V928 Real Data UI Guard QA

## Principio aplicado

La referencia define estructura y presentacion, no contenido de produccion. V928 no copia sus partidos, cuotas, resultados, ROI, ingresos, usuarios, suscriptores ni escudos.

## Controles

- Los partidos, live, resultados y cuotas se leen de DB/cache/contextos seguros; no se llama a proveedores durante render.
- Un pick solo se presenta como completo/publicable cuando dispone de partido, mercado, seleccion y cuota reales y vigentes.
- Track record y ROI se calculan solo con picks cerrados reales.
- Pagos, MRR, membresias y usuarios admin proceden de registros/configuracion reales o muestran estado vacio.
- Los fallbacks de escudo son neutros y no suplantan insignias oficiales.
- Los estados vacios indican causa y siguiente accion, sin rellenar cifras.

## Resultado

`tools/check_v928_real_data_ui_guard.py` finalizo correctamente. No se detectaron tokens de datos demo visibles ni una ruta de render que exija una llamada externa. Datos inventados: no.
