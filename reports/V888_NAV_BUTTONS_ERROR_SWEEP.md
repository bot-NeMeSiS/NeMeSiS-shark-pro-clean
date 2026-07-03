# V888 Nav Buttons Error Sweep

## Revisión

Áreas revisadas:

- menú lateral cliente desktop
- bottom nav móvil
- admin rail
- topbar
- floating SHARK
- links rotos
- CTAs de login/registro

## Correcciones V888

- Corregido fallback JS de SHARK: `/api/shark/ask?q=...`.
- Corregido heartbeat JS de runtime: `r.ok ? r.json() : null`.
- Corregidos links de continuidad de plan:
  - `/registro?plan=...`
  - `/cliente-login?plan=...`

## Contratos preservados

- `client-sidebar` una sola vez.
- `client-bottom` una sola vez.
- admin rail solo en admin.
- sin nav cliente en admin.
- sin admin nav en cliente.

