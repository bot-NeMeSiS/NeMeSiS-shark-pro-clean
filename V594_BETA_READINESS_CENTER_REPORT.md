# V594 — Beta Readiness Center

## Objetivo
Preparar NeMeSiS SHARK PRO para beta comercial controlada con un centro de salud operativo que centraliza sistema, Telegram, Auto Picks, APIs, usuarios, datos y preparación comercial.

## Añadido
- Nuevo panel `/admin/beta-center`.
- Nuevo endpoint `/api/v594/beta-health-check`.
- Resumen de salud: base de datos, Telegram, scheduler, Auto Picks, envío automático, TheSportsDB, The Odds API, datos deportivos, escudos y cola Telegram.
- Indicadores beta: usuarios FREE/PRO/ELITE, conversión pagada, MRR estimado, picks, winrate, cola Telegram, ciclos automáticos y partidos guardados.
- Alertas internas para detectar antes de vender: API pendiente, Telegram fallido, pocos partidos, auto picks apagado o problemas de cola.
- Integración en `/admin/data-center`.
- Enlace directo en navegación admin.

## Seguridad
- No se han tocado login, membresías, SHARK, Telegram base, Render ni SQLite crítico.
- Las consultas son defensivas: si una tabla antigua no existe, el panel no rompe la app.
- No hay nuevas dependencias externas.

## Rutas nuevas
- `/admin/beta-center`
- `/api/v594/beta-health-check`

## Validación
- Compilación Python OK.
- ZIP limpio sin `.git`, `__pycache__`, bases de datos locales, logs ni ZIPs internos.
