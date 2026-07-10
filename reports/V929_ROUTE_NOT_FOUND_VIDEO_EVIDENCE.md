# V929 Route Not Found Video Evidence

## Evidencia visible

- Archivo: `NeMeSiS SHARK PRO - Ruta no encontrada 2026-07-10 20-18-44.mp4`.
- Duracion: 4:18.40.
- Viewport grabado: navegador desktop de 1360x720.
- El video comienza con la pagina 404 premium ya abierta.
- Ruta solicitada visible: `/clientes`.
- El enlace o pantalla inmediatamente anterior al 404 no aparece en la grabacion.
- Por ello no se atribuye el fallo a un boton concreto sin evidencia.
- Aproximadamente en el segundo 7-8 se pulsa `Entrar` y `/cliente-login` carga correctamente.
- Despues del login se recorren Inicio, Partidos, Directo, Picks, Historico, SHARK, Telegram y Cuenta sin otro 404 visible.

## Causa comprobada

La ruta historica `/clientes` no estaba registrada en la base V928. Era una URL antigua/alias faltante; el handler 404 funcionaba correctamente y no era la causa.

## Correccion

Se registro `/clientes` y `/clients` con resolucion por rol: publico a `/cliente-login`, cliente autenticado a `/app` y admin autenticado a `/admin/users`.
La validacion no sustituye cualquier 404 por la home y conserva status 404 contextual para recursos dinamicos inexistentes.

## Limite de evidencia

No se conoce el texto del enlace original ni la pantalla de origen porque no aparecen en el video. No se inventa esa informacion.
