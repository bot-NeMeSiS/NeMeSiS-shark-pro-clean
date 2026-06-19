# V827 Reference Photo Visual Gap Audit

Base real usada: V826_FULL_REFERENCE_APP_EXPERIENCE_SCREEN_COMPLETION_FINAL.
Nueva versión: V827_REFERENCE_PHOTO_REBUILD_DESIGN_SYSTEM_FINAL.

## Resumen

V826 ya cubría pantallas y estabilidad, pero visualmente seguía dependiendo de muchas capas históricas. V827 crea una capa de diseño más unificada: tokens V827, topbar consistente, cards más profundas, fondo SHARK reforzado, escudos con tamaño común, botones coherentes y móvil más compacto.

## Comparativa por pantalla

| Pantalla | Qué faltaba | Qué sobraba o se veía viejo | Template | CSS/componente tocado |
|---|---|---|---|---|
| /app | Más jerarquía visual, hero fuerte, cards deportivas uniformes | Mezcla de capas V799/V812/V826 | client_app_center.html | Bloque V827 hero/kpis/cards |
| /partidos /calendar | Más densidad tipo app deportiva y competición protagonista | Filas heredadas con estilos distintos | calendar.html | Match rows, league blocks, crest sizing |
| /live /directo | Centro live más premium y campos/cards coherentes | Diferencias entre feature y cards secundarias | live.html | Live feature, pitch, live cards |
| /picks | Cards más vendibles y métricas más claras | Pick destacado algo plano | picks.html | Pick card, feature metrics, CTA buttons |
| /shark | Debe sentirse pantalla principal | Floating duplicado ya estaba protegido, se refuerza hero | shark.html | Shark hero, hide floating on SHARK routes |
| /profile | Debía encajar con shell premium | Template secundario con menos identidad | profile.html | Marcador V827 y estilos comunes |
| /telegram | Necesitaba coherencia visual sin secretos | Diferente al resto del cliente | telegram.html | Shell/cards/buttons comunes |
| /support | Necesitaba integrarse visualmente | Hero simple | support.html | Shell/cards/buttons comunes |
| /admin/dashboard | Command center sobrio | Demasiado parecido a cliente en algunas superficies | admin_dashboard.html | Admin surfaces sober |
| /admin/daily-automation | Más jerarquía de operación | Paneles densos heredados | admin_daily_automation.html | Admin cards/kpis |

## Neutralizado

- Se ocultan acciones secundarias antiguas de cliente (`v811-top-actions`, `v797-session-pills`) en V827 para reducir duplicación.
- Admin queda sin fondo SHARK cliente y sin floating SHARK.
- /shark, /shark-ai y /shark-core siguen sin floating duplicado.

## No realizado

No se generaron screenshots reales, por lo que no se declara pixel-perfect.
