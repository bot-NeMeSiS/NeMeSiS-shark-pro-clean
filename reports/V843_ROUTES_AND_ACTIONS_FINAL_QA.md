@"
# V843 Routes And Actions Final QA

## Objetivo
Validar que los botones principales no estén muertos, no usen href vacío y no apunten a rutas internas mal formadas.

## Correcciones aplicadas
- Enlaces SHARK desde picks y detalle de partido.
- Enlaces de combis y mercados.
- Enlace de actualización de directo.
- Filtros de match-hub.
- Enlaces de membresías.
- Consulta SHARK por equipo.

## Resultado de check
	ools/check_v843_routes_actions.py pasa correctamente tras la corrección.

## Criterio comercial
Un usuario puede navegar entre app, partidos, directo, picks, SHARK, perfil, Telegram, soporte y pantallas secundarias sin encontrar botones básicos rotos por URL mal formada.

## Validación final
La validación V843 confirma que las rutas principales responden sin 500/404, que las rutas protegidas redirigen correctamente cuando no hay sesión y que no quedan hrefs vacíos ni enlaces internos mal formados detectados por el check V843.
