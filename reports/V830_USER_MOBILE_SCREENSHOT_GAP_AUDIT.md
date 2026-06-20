# V830 User Mobile Screenshot Gap Audit

## Base real usada

Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`

Base detectada antes de V830: `V829_MOBILE_LINKED_ECOSYSTEM_FINAL_APP_EXPERIENCE`.

## Qué se ve en la captura

- La barra inferior móvil aparece cortada y desplazada hacia la izquierda.
- Solo se aprecian parcialmente los enlaces `Directo`, `Picks` y `SHARK`.
- Los enlaces `Inicio` y `Partidos` quedan fuera de la zona visible.
- Aparece un botón flotante con flecha hacia arriba en la zona inferior derecha.
- Hay demasiado espacio oscuro bajo el contenido.
- El comportamiento apunta a overflow horizontal y conflicto entre bottom nav, safe-area, scroll-to-top y floating SHARK.

## Causa probable encontrada

El CSS acumulaba varias capas históricas de navegación inferior. En V829 todavía había reglas móviles con `left:8px` y `right:8px` más `max-width`, una combinación que puede dejar la barra más ancha que el viewport o mal centrada en capturas móviles reales. También seguía existiendo el botón `ns-scroll-top`, visualmente parecido a una flecha flotante independiente.

## Rutas y plantillas afectadas

La corrección se aplica desde `templates/base.html` y `static/app.css`, por lo que afecta a todas las pantallas cliente móviles que heredan el shell: `/app`, `/partidos`, `/calendar`, `/live`, `/directo`, `/picks`, `/profile`, `/telegram`, `/support`, `/favorites`, `/track-record`, `/combis`, `/mercados`, `/highlights` y `/match/<id>`.

## Corrección aplicada

- Se añadió shell V830 con `data-v830-shell`.
- Se añadió una capa final CSS `V830 MOBILE BOTTOM NAV PIXEL QA`.
- La bottom nav móvil queda centrada con `left:50%` y `transform:translateX(-50%)`.
- El ancho se controla con `min(430px, calc(100vw - 24px))`.
- Se fuerza grid de 5 enlaces visibles.
- Se oculta `ns-scroll-top` en móvil para eliminar la flecha rara.
- Se recoloca el floating SHARK por encima de la barra inferior.
- Se añade padding inferior al contenido para que la nav no tape cards.
- Se refuerza `overflow-x:hidden` y `min-width:0` en contenedores críticos.

## Validación esperada

La barra inferior debe verse completa, centrada y sin corte lateral en móviles de 390px y 430px. No debe aparecer la flecha flotante en móvil. SHARK debe quedar por encima de la navegación y ocultarse en `/shark`, `/shark-ai` y `/shark-core`.
