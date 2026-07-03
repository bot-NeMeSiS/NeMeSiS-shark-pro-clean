# V886 Mobile Bottom Nav QA

## Objetivo movil

Validar que la recuperacion de sidebar PC no rompio la experiencia movil.

## Contrato CSS validado

- En `max-width: 1023px`, `.ns-client-sidebar` queda oculta.
- Bottom nav cliente usa `data-nav-zone="client-bottom"`.
- El contrato CSS mantiene bottom nav como navegacion movil principal.
- El main shell se resetea para evitar desplazamiento lateral heredado del desktop sidebar.

## Limitacion

No se ejecuto navegador real en viewport 390x844. No se declara ausencia pixel-perfect de scroll horizontal; se valida el contrato responsive por CSS y HTML.

## Pendiente

Instalar Playwright usable o ejecutar browser QA manual tras deploy para medir `document.documentElement.scrollWidth <= window.innerWidth`.
