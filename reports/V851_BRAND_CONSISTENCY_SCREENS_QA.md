# V851 Consistencia de Marca por Pantalla

## Pantallas cubiertas por el layout base
- `/`
- `/cliente-login`
- `/registro`
- `/app`
- `/partidos`
- `/calendar`
- `/live`
- `/directo`
- `/picks`
- `/shark`
- `/telegram`
- `/profile`
- `/support`
- `/admin/dashboard`
- `/admin/api-sports`
- `/admin/telegram/command-center`
- `/admin/shark-ai`

## Criterio aplicado
Todas heredan `templates/base.html`, que ahora centraliza marca con `templates/partials/brand_logo.html`.

## Resultado
Cliente, móvil, PC y admin usan una identidad coherente sin duplicar logos distintos por pantalla.
