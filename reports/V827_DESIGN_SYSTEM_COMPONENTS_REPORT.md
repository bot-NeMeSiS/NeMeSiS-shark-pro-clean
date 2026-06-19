# V827 Design System Components Report

## Componentes consolidados

- App shell cliente: `body[data-v827-shell="true"]`, `ns-main-shell`.
- Topbar cliente: `.top.ns-topbar`, `.topin`, `.brand`, `.nav-clean`.
- Bottom nav móvil: `.bottom-nav-clean` con cinco columnas en móvil.
- Fondo SHARK: `.v825-shark-background` reforzado por V827.
- Floating SHARK: `.shark-widget`, `.shark-fab`, oculto en pantallas SHARK y admin.
- Hero premium: `.v799-appbar`, `.v812-hero-shell`, `.v783-public-hero`, `.v774-client-hero`.
- Cards deportivas: `.v799-agenda-row`, `.v801-agenda-row`, `.v812-row`, `.sports-row`.
- Live cards: `.v799-live-feature`, `.v799-live-card`, `.v803-live-field`.
- Pick cards: `.v799-feature-pick`, `.v799-pick-card`, métricas del pick.
- Empty state premium: `.premium-empty`, `.empty`, `.v799-empty`, `.v812-empty`, `.v827-empty-state`.
- CTA button: `.btn`, `.primary`, `.v827-btn`.
- Admin command card: `.v794-admin-panel`, `.v794-admin-card`, `.v794-admin-kpi-grid`.

## Macro añadida

`templates/components/v827_design_system.html` contiene macros ligeras para `premium_empty`, `stat_chip` y `cta`. Se deja preparada para nuevas pantallas sin forzar refactor de templates estables.

## Principio aplicado

V827 no añade otra piel caótica: define tokens y reglas finales que normalizan las clases reales ya usadas por la app.
