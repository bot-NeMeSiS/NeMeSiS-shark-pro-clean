# V701 Client Experience Launch Report

## Objetivo

Convertir la experiencia cliente de NeMeSiS SHARK PRO en una pantalla deportiva premium tipo Flashscore/Sofascore, manteniendo la ventaja SHARK: picks, score, value, favoritos, combis y Telegram.

## Mejoras de experiencia usuario

- El cliente autenticado ya no aterriza en un dashboard gen?rico: `/dashboard` redirige a `/sports-hub`.
- La navegaci?n cliente se reorganiza alrededor de valor real: Inicio, Partidos, Live, Picks, Combis, Favoritos, Telegram, Perfil y M?s.
- Se corrigieron textos corruptos visibles en `base.html` y preguntas r?pidas SHARK.
- Se redujo la sensaci?n de panel t?cnico en Sports Hub, Live, Calendar y Picks.
- Se a?adieron estados vac?os premium y mensajes claros cuando faltan datos.

## Sports Hub

- `/sports-hub` queda como coraz?n del producto.
- A?adidas pesta?as compactas:
  - Hoy
  - Directo
  - Ma?ana
  - Semana
  - Picks
  - Favoritos
  - Combis
- Listado compacto de partidos con hora/minuto, escudos, equipos, marcador/vs, favorito, SHARK Score y badge de pick.
- Agrupaci?n por competici?n.
- Deduplicaci?n defensiva de partidos.
- Nueva ruta `/today` como alias directo hacia Sports Hub.

## Live

- `/live` se compact? como marcador deportivo.
- Cada fila muestra minuto, marcador, equipos, escudos, competici?n, estado, favorito y SHARK/Momentum compacto.
- Se elimin? la apariencia de dashboard t?cnico.
- Si no hay directo, se muestra estado ?til y pr?ximos destacados.

## Calendar

- `/calendar` ahora usa una estructura m?s compacta y consistente con Sports Hub.
- Filtros claros en espa?ol: Hoy, Ma?ana, Esta semana, Pr?ximos, Live y Sports Hub.
- Filas con hora Espa?a, equipos, escudos, competici?n, marcador/estado y favorito.

## Picks

- `/picks` se redise?? como producto premium.
- Cada pick muestra:
  - Competici?n
  - Partido
  - Mercado
  - Selecci?n recomendada
  - Cuota
  - Stake
  - SHARK Score
  - Confianza
  - Riesgo
  - Value
  - Por qu? entrar
  - Por qu? no entrar
- Se mantiene estado claro si no hay picks: SHARK no inventa apuestas.

## Telegram

- No se toc? el fix V640 de sincronizaci?n env/DB.
- Se valid? localmente:
  - `/telegram`: 200
  - `/telegram/webhook` con `/start CODIGO`: 200
  - `/telegram/webhook` con `/link CODIGO`: 200
  - `/admin/telegram`: 200
  - `/admin/telegram/diagnostics`: 200
- La prueba de env?o real queda pendiente para Render con red y credenciales reales.

## M?vil

- A?adido CSS V701 para filas compactas, tabs sticky, bottom nav de 7 accesos y SHARK flotante menos invasivo.
- Sports Hub, Live, Calendar y Picks comparten patr?n visual para reducir aprendizaje.

## Pruebas realizadas

Compilaci?n:

```bash
python -m compileall app.py engines database_manager.py services
```

Resultado: OK.

Smoke tests con DB temporal:

- `/`: 200
- `/login`: 200
- `/cliente-login`: 200
- `/admin-login`: 200
- `/registro`: 200
- `/api/health`: 200
- `/api/runtime-version`: 200
- `/api/startup-check`: 200
- `/dashboard`: 302 hacia Sports Hub
- `/perfil`: 200
- `/sports-hub`: 200
- `/sports-hub?tab=live`: 200
- `/sports-hub?tab=tomorrow`: 200
- `/sports-hub?tab=week`: 200
- `/sports-hub?tab=favorites`: 200
- `/live`: 200
- `/calendar`: 200
- `/picks`: 200
- `/favorites`: 200
- `/combis`: 200
- `/telegram`: 200
- `/shark`: 200
- `/recommendations`: 200
- `/telegram/webhook` con `/start CODIGO`: 200
- `/telegram/webhook` con `/link CODIGO`: 200
- `/admin/dashboard`: 200
- `/admin/users`: 200
- `/admin/telegram`: 200
- `/admin/telegram/diagnostics`: 200
- `/admin/backups`: 200
- `/admin/automation`: 200
- `/admin/intelligence`: 302 hacia centro unificado
- `/admin/observability`: 200
- `/admin/observability/errors`: 200

Errores 500: 0.
Tracebacks: 0.
Incidencias controladas en smoke: 0.

## Variables Render necesarias

- `SECRET_KEY`
- `DB_PATH=/data/database.db`
- `ADMIN_EMAIL`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_USERNAME`
- `ENABLE_TELEGRAM_AUTO=true`
- `AUTO_SEND_TELEGRAM_PICKS=true`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` si se quiere email real de recuperaci?n.

## Limitaciones reales pendientes

- Probar Telegram real en Render con red y token real.
- QA visual manual en m?vil f?sico.
- La calidad de picks depende de datos reales disponibles de cuotas/mercados.
