# V885 Client Navigation Current State Audit

## Hallazgo principal

La navegacion lateral util de cliente habia quedado retirada tras la limpieza de duplicados. El estado previo era seguro contra duplicados, pero peor para experiencia PC: el cliente autenticado dependia de la topbar y el usuario echaba en falta el menu lateral.

## Estado previo

- `base.html` tenia `show_client_nav = is_client_area`.
- Cliente desktop usaba `nav-clean[data-nav-zone="client-topbar"]`.
- Cliente movil usaba `bottom-nav-clean[data-nav-zone="client-bottom"]`.
- Admin usaba `v808-admin-rail`.
- V881 ocultaba railes legacy como `v798-client-rail`, `v799-client-rail`, `client-sidebar`.

## Riesgos detectados

- Sin sidebar cliente PC, la navegacion pierde persistencia.
- Restaurar un rail legacy sin control podria duplicar topbar/bottom nav.
- Admin no puede recibir sidebar cliente ni SHARK flotante.

## Decision

Crear una fuente canonica nueva: `ns-client-sidebar`, visible solo para cliente autenticado en desktop. La topbar cliente autenticada deja de renderizar enlaces principales para evitar duplicado.
