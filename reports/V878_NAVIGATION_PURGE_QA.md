# V878 Navigation Purge QA

## Revision

Se reviso `templates/base.html`:

- Topbar compartida.
- Nav cliente.
- Rail cliente.
- Rail admin.
- Dock admin.
- Command strip admin.
- Floating SHARK.

## Accion V878

- Se mantiene aislamiento: admin oculta bottom nav, rail cliente y floating cliente.
- Cliente oculta rail/dock/command strip admin.
- Se preservan rutas admin y cliente existentes.

## Riesgo

Hay varias capas historicas de navegacion porque el producto acumula versiones. No se borran rutas ni menus sin browser QA real.

