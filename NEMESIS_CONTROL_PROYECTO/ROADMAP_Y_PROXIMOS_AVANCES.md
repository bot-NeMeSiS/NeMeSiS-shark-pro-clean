# ROADMAP Y PRÓXIMOS AVANCES

## P0 — SPORTS TRUTH COMO ÚNICA FUENTE DE VERDAD

Objetivo: una sola decisión canónica por partido para estado, frescura, marcador, minuto y confianza.

Terminado cuando:
- Home, `/live`, `/calendar`, `/partidos`, Match Center y SHARK coinciden para el mismo partido.
- `LIVE` requiere evidencia reciente y compatible.
- `FINISHED` o desaparición sostenida del feed live no puede regresar a `LIVE` por un snapshot residual.
- `STALE` nunca se publica como directo.
- La confianza se degrada automáticamente ante stale, ausencia de timestamp o contradicción.
- Existen tests para `LIVE → FT`, desaparición del proveedor, snapshot viejo y status conflictivo.

## P1 — MATCH CENTER / SPORTS KNOWLEDGE
- Eventos, alineaciones, jugadores, estadísticas, standings, H2H y contexto real.
- Enlazar equipos, jugadores, competiciones y partidos sin páginas huérfanas.
- Priorizar competiciones Tier S/A y controlar gasto de APIs.

## P1 — EXPERIENCIA DEPORTIVA MÓVIL Y PC
- Mantener sistema visual único y premium.
- Más densidad útil, jerarquía clara y navegación rápida.
- Match Center como núcleo de la experiencia.

## P1 — SHARK SECOND
- SHARK interpreta Sports Knowledge normalizado; no crea una segunda verdad deportiva.
- Separar hechos verificados de análisis y recomendaciones.

## P2 — BETTING THIRD
- Picks, cuotas, EV, stake y track record solo sobre partidos/mercados frescos y evaluables.
- Mejorar trazabilidad de fuente, timestamp, mercado, selección, resultado y grading.

## P2 — COMERCIALIZACIÓN CONTROLADA
- Onboarding, FREE/PRO/ELITE, Stripe certificado, Telegram, soporte, privacidad y derechos de contenido.

## Siguiente avance recomendado

`SPORTS_TRUTH_SINGLE_SOURCE_OF_TRUTH_FINAL`: localizar todas las rutas que calculan o presentan LIVE y hacerlas depender de un único helper/contrato canónico con pruebas de consistencia transversal.
