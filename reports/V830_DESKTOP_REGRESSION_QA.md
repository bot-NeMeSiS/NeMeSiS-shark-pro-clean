# V830 Desktop Regression QA

## Alcance desktop

Rutas revisadas a nivel de shell/CSS:

- `/app`
- `/partidos`
- `/live`
- `/picks`
- `/shark`
- `/profile`
- `/support`
- `/admin/dashboard`
- `/admin/daily-automation`
- `/admin/telegram/command-center`

## Resultado esperado

- La bottom nav cliente queda oculta en desktop autenticado.
- Admin no recibe bottom nav cliente.
- Admin no recibe floating SHARK cliente.
- La corrección V830 se limita sobre todo a `@media(max-width:768px)`.
- Las reglas desktop existentes de V827/V828/V829 se conservan.

## Riesgo controlado

No se cambió estructura de rutas ni lógica del servidor. La corrección se aplica en CSS y versionado, con checks específicos para detectar regresiones.
