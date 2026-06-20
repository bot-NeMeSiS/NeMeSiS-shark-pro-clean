# V836 Autonomous Mobile Review QA

## Revisión aplicada

- Bottom nav móvil preservada desde V830 y reforzada en V836.
- 5 enlaces visibles: Inicio, Partidos, Directo, Picks, SHARK.
- Safe-area iOS reforzada.
- `overflow-x` bloqueado en `html`, `body` y contenedores principales.
- Botón de subir oculto en móvil.
- Floating SHARK colocado por encima de bottom nav.
- Floating SHARK oculto en pantallas SHARK.
- Sidebar/rail desktop ocultos en móvil.
- Admin sin bottom nav cliente.
- Tablas admin con scroll interno seguro.

## Pantallas cliente cubiertas

- Home, login, registro, app, partidos, calendar, live, directo, picks, match detail, SHARK, profile, Telegram, soporte, favoritos, histórico, combis, mercados y highlights.

## Riesgos mitigados

- Bottom nav cortada.
- Botón flotante raro en zona inferior.
- Scroll horizontal.
- Cards demasiado anchas.
- Botones pequeños.
- SHARK duplicado.
