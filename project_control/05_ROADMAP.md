# 05 — Roadmap operativo

## P0 — Cerrar Sports Truth de extremo a extremo

Objetivo: una sola decisión canónica por partido para estado, frescura, marcador, minuto y confianza.

Entregado cuando:

- Home, `/live`, `/calendar`, `/partidos`, Match Center y SHARK coinciden para el mismo partido.
- `LIVE` requiere evidencia reciente y proveedor/estado compatible.
- `FINISHED` o desaparición sostenida del feed live no puede regresar a `LIVE` por snapshot residual.
- `STALE` nunca se publica como directo.
- Confianza se degrada automáticamente ante stale, ausencia de timestamp o contradicción.
- Hay tests con transición `LIVE → FT`, desaparición del proveedor, snapshot viejo y status conflictivo.

## P1 — Match Center / Sports Knowledge

- Construir profundidad deportiva real: eventos, alineaciones, jugadores, estadísticas, standings, H2H y contexto.
- Enlazar equipos, jugadores, competiciones y partidos sin páginas huérfanas.
- Mantener prioridad Tier S/A y no malgastar llamadas de API en datos de poco valor.

## P1 — Experiencia deportiva móvil y PC

- Seguir la referencia premium sin volver a acumular capas CSS legacy.
- Densidad útil, jerarquía clara, navegación rápida y Match Center como núcleo.
- Todo componente debe consumir datos reales y estados vacíos honestos.

## P1 — SHARK Second

- SHARK debe interpretar el Sports Knowledge ya normalizado, no crear una segunda verdad deportiva.
- Distinguir hechos deportivos verificados de análisis/recomendación.
- Personalización por usuario/membresía sin inventar precisión.

## P2 — Betting Third

- Picks, cuotas, EV, stake y track record deben apoyarse en partido/mercado frescos y evaluables.
- No publicar pick si el lifecycle del partido o las cuotas no cumplen contrato.
- Mejorar trazabilidad: fuente, timestamp, mercado, selección, resultado y grading.

## P2 — Comercialización controlada

- Onboarding claro.
- Membresías FREE / PRO / ELITE consistentes en web, Telegram y permisos.
- Stripe solo se considera listo cuando la ruta real de pago/webhook/renovación/cancelación esté certificada.
- Soporte, recuperación de cuenta, privacidad y derechos de contenido listos antes de apertura amplia.

## P2 — Observabilidad y empresa

- Mantener automatizaciones actuales y reducir ruido.
- Convertir hallazgos repetidos en tests/contratos, no en más tareas programadas.
- Weekly Board debe decidir qué se construye y qué se descarta cada semana.

## Siguiente avance recomendado

`SPORTS_TRUTH_SINGLE_SOURCE_OF_TRUTH_FINAL`: localizar todas las rutas que calculan o presentan LIVE y hacerlas depender de un único helper/contrato canónico con pruebas de consistencia transversal.
