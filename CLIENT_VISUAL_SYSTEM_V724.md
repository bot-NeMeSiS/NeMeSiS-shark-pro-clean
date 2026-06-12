# Client Visual System V724

## Objetivo

V724 define una capa visual cliente para que NeMeSiS SHARK PRO se sienta como una app deportiva premium: compacta, clara, móvil-first y comercial.

## Principios

- Cliente sin textos técnicos.
- Mucha información útil en poco espacio.
- Tarjetas compactas.
- Botones consistentes.
- Dark premium con acentos cian, verde y dorado.
- Empty states claros.
- Juego responsable siempre presente cuando se habla de picks o combis.

## Colores

- Fondo principal: oscuro deportivo.
- Acento SHARK: cian.
- Valor/positivo: verde.
- ELITE/premium: dorado.
- Riesgo/alerta: rojo suave.

## Clases Principales

- `.shark-shell`: contenedor cliente.
- `.shark-card`: tarjeta base premium.
- `.shark-card-premium`: tarjeta destacada.
- `.shark-section`: sección cliente.
- `.shark-section-title`: título de sección.
- `.shark-kpi-grid`: grid de métricas.
- `.shark-kpi-card`: tarjeta KPI.
- `.shark-action-grid`: acciones rápidas.
- `.shark-pill`: badge compacto.
- `.shark-status`: estado compacto.
- `.shark-team-row`: fila de equipo.
- `.shark-match-card`: partido.
- `.shark-pick-card`: pick.
- `.shark-combi-card`: combinada.
- `.shark-empty-state`: estado vacío premium.
- `.shark-premium-cta`: llamada a plan premium.

## Tarjetas

Las tarjetas deben:

- tener radio contenido
- mostrar primero lo importante
- evitar párrafos largos
- usar badges cortos
- no mostrar `None`, `null`, `undefined` ni textos técnicos

## Botones

Usar:

- principal para acción primaria
- secundario para navegación
- botones cortos: “Ver análisis”, “Preguntar a SHARK”, “Telegram”

Evitar:

- botones con frases largas
- rutas técnicas
- acciones ambiguas

## Picks

Cada pick visible debe explicar:

- selección
- cuota
- stake
- confianza
- riesgo
- motivo
- precaución

No vender como premium señales sin cuota real o sin selección clara.

## Combis

Tres modos:

- segura: 2-4
- media: 5-8
- larga: 9-15

La combi larga siempre debe mostrarse como alto riesgo.

## Telegram

Cliente debe ver:

1. abre el bot
2. envía el código
3. recibe alertas

Nunca mostrar token, chat id, cron, scheduler, API ni configuración interna.

## Responsive

En móvil:

- no scroll horizontal
- tarjetas de una columna
- bottom nav compacto
- SHARK flotante pequeño
- CTAs tocables
- textos cortos

## Mantenimiento Futuro

Antes de añadir una pantalla cliente, reutilizar clases V724. Si una pantalla necesita un nuevo bloque visual, añadirlo al final de `static/app.css` sin romper clases históricas.
