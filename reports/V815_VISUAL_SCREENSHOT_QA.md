# V815 Visual Screenshot QA

## Estado

No se generaron capturas reales de navegador en este entorno.

## Motivo

No hay herramienta de navegador directa disponible en la sesion. Se intento verificar Playwright mediante Node REPL, pero el kernel no pudo arrancar por restriccion del sandbox de Windows.

## Sustitucion honesta

Se hicieron pruebas HTML/runtime con Flask test client:

- `/app`
- `/calendar`
- `/live`
- `/picks`
- `/shark`
- `/telegram`

Todas devolvieron HTML con:

- `data-v815-shell="true"`
- comentario fuente V815;
- CSS cache-busting V815;
- tiburon decorativo cliente;
- un solo widget SHARK en markup.
