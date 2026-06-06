# V631 ELITE COMMERCIAL EVOLUTION

## Objetivo

Evolucionar la base V626 hacia beta comercial premium sin rehacer módulos ni romper SHARK, Telegram, Warehouse, Membresías Temporales o Backup Center.

## Mejoras aplicadas

- Versión actualizada a `V631_ELITE_COMMERCIAL_EVOLUTION`.
- Automatización diaria a las 10:00 Europe/Madrid mediante el flujo interno seguro.
- Panel admin `/admin/automation` con última ejecución, duración, estado, errores, partidos sincronizados, picks generados, picks enviados y backups creados.
- Botón admin `Ejecutar ahora` para lanzar el ciclo diario bajo demanda.
- Nuevo Sports Hub `/sports-hub` con partidos de hoy, directos, picks, SHARK destacado, favoritos y competiciones principales.
- Live mantiene la capa compacta V626 y se refuerza con lectura premium de escudos/marcador/minuto/SHARK.
- SHARK Product Experience en `/shark`: score, confianza, riesgo, motivo principal, value y explicación simple.
- Centro Comercial `/admin/intelligence` con FREE activos, próximos a expirar, sin Telegram, PRO, ELITE, inactivos, upgrades, VIP y actividad reciente.
- APIs admin:
  - `/api/automation/daily`
  - `/api/automation/daily/run`
- Navegación admin y cliente conectada a Sports Hub, Automatización y Comercial.

## Automatización diaria

El ciclo diario ejecuta:

- competiciones
- calendario
- live
- resultados
- recomendaciones
- auto picks
- Telegram
- caducidad de membresías
- backup
- warehouse
- ROI/rendimiento

La ejecución queda registrada en `automation_state` y en auditoría interna.

## Pruebas

- `python -m compileall app.py engines database_manager.py`: OK.
- Smoke test:
  - `/`, `/login`, `/admin-login`, `/registro`, `/picks`, `/live`, `/calendar`, `/sports-hub`, `/shark`: 200.
  - Registro cliente: 302.
  - Login cliente: 302.
  - `/perfil`, `/favorites`, `/sports-hub`, `/shark` con cliente: 200.
  - Login admin: 302.
  - `/admin/dashboard`, `/admin/users`, `/admin/backups`, `/admin/automation`, `/admin/intelligence`: 200.
  - Crear backup desde admin: 200.
  - Ejecutar automatización ahora: 200.
  - `/api/health` tras automatización: 200.
  - Observability errors: 0.

## Nota de prueba

En entorno local sin proveedores externos configurados, la automatización manual termina `PARTIAL`, crea backup y registra errores de proveedores/configuración sin romper la web. En Render, con variables reales, el ciclo usará las integraciones configuradas.

## Pendiente real

- Revisar visualmente `/sports-hub`, `/live`, `/shark` y `/admin/intelligence` en móvil real con datos abundantes.
- Ajustar frecuencia/ventana si el uso comercial pide otra hora además de 10:00 Europe/Madrid.
