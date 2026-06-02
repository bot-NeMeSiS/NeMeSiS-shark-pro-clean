# V590 — Match Detail Premium

## Objetivo
Convertir la ficha de partido en el centro premium de la aplicación, sin crear menús nuevos ni tocar login, membresías, Telegram, Render o SQLite.

## Cambios principales

- Añadido perfil premium V590 para cada partido.
- Añadido bloque superior de "Centro premium del partido".
- Añadida forma reciente local/visitante con indicadores G/E/P.
- Añadido bloque H2H/cara a cara usando partidos persistidos.
- Añadido bloque de cuotas 1X2 y lectura de value usando `odds_snapshots` o cuotas ya guardadas.
- Añadida lectura premium SHARK con contexto de partido próximo, directo o finalizado.
- Mejorada la ficha para antes del partido, directo y finalizado sin inventar datos.
- Añadido endpoint de comprobación `/api/v590/match-detail-check`.
- Añadidos estilos responsive específicos V590.

## Archivos modificados

- `app.py`
- `templates/match_detail.html`
- `static/app.css`
- `VERSION.txt`

## Endpoint nuevo

- `/api/v590/match-detail-check`

Devuelve:

- estado V590
- partido de muestra
- secciones activas
- calidad de datos
- puntuación SHARK estimada

## Seguridad

No se han creado nuevas pantallas grandes.
No se han modificado flujos críticos:

- Login
- Registro
- Membresías
- Telegram
- Auto Picks
- SHARK Learning
- Calendario V589
- Render
- SQLite persistente

## QA

- `compileall app.py engines` OK.
- ZIP preparado sin `.git`, `__pycache__`, bases de datos locales, logs ni ZIPs internos.
