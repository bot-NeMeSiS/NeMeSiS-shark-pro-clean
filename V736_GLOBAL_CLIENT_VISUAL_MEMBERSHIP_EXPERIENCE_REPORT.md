# V736 Global Client Visual Membership Experience Report

## Versión

`V736_GLOBAL_CLIENT_VISUAL_MEMBERSHIP_EXPERIENCE`

## Objetivo

Aplicar una capa visual global de experiencia premium por membresía, inspirada en la referencia aportada: misma información, distinto color y energía según FREE, PRO, ELITE y ELITE+.

## Cambios principales

- `base.html` ahora añade clases globales por membresía: `ns-tier-free`, `ns-tier-pro`, `ns-tier-elite` y `ns-tier-eliteplus`.
- Se añadió barra superior de energía de membresía y badge de plan visible.
- `static/app.css` incorpora la capa **V736 Global Client Visual Membership Experience**.
- El estilo afecta de forma global a tarjetas, cabecera, botones, navegación inferior, formularios, tablas, estados vacíos, SHARK flotante, Live, Picks, Calendar, Track Record y paneles admin.
- Se añade centro admin `/admin/visual-experience` y API segura `/api/admin/visual-experience`.
- Se añade `engines/visual_experience_engine.py` y `tools/check_v736_visual_experience.py`.

## Temas visuales

- FREE: Ocean Blue.
- PRO: Cyber Green.
- ELITE: Golden Shark.
- ELITE+: Neon Purple.

## Alcance seguro

- No cambia lógica de picks.
- No toca cuotas, Cron, Telegram, Data Memory, pagos ni membresías reales.
- No expone secrets.
- No cambia `DB_PATH`.
- No rompe Madrid Time ni V735 Go Live.

## Validación local/sandbox

- `python -m py_compile app.py`: OK.
- `python -m compileall -q .`: OK.
- `tools/check_madrid_times.py`: OK.
- `tools/check_v728_client_experience.py`: OK.
- `tools/check_v729_security.py`: OK.
- `tools/check_v730_route_health.py`: OK.
- `tools/check_v731_client_experience.py`: OK.
- `tools/check_v732_production_readiness.py`: OK.
- `tools/check_v733_client_success.py`: OK.
- `tools/check_v734_public_launch.py`: OK.
- `tools/check_v735_go_live.py`: OK.
- `tools/check_v736_visual_experience.py`: OK, score 100/100.

## Pendiente real en Render

- Probar `/api/runtime-version`.
- Probar `/admin/visual-experience`.
- Probar móvil real con usuarios FREE, PRO y ELITE.
- Revisar capturas de Home, Sports Hub, Live, Calendar, Picks, Combis, SHARK, Telegram, Perfil y Match Detail.
