# V935 Odds Freshness QA

Estados validados:

- `FRESH`: hasta 15 minutos, etiqueta `Cuota actual`.
- `RECORDED`: de 15 a 60 minutos, etiqueta `Ultima cuota registrada`.
- `STALE`: mas de 60 minutos, sin publicacion como actual.
- `EXPIRED`: mercado o partido cerrado.
- `INVALID`: cuota ausente/menor o igual que 1, sin fuente o sin timestamp valido.

Las cards muestran procedencia y frescura cuando existe evidencia. No se solicita cuota por page view; la vista consume exclusivamente DB/cache. Conteos locales: 0 fresh, 0 recorded, 0 stale y 0 invalid por ausencia de registros.
