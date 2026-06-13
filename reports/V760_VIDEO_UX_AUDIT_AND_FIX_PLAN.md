# V760 Video UX Audit and Fix Plan

## Observación desde el vídeo aportado

Se revisó el vídeo `NeMeSiS SHARK PRO 2026-06-13 23-29-07.mp4` y se detectaron problemas claros de experiencia cliente:

- La navegación superior estaba saturada con demasiados enlaces para cliente.
- La navegación inferior repetía demasiadas acciones y hacía difícil saber qué tocar.
- Aparecía un botón flotante de modo PC/Móvil además de otros accesos, generando sensación de botones duplicados.
- SHARK flotante no funcionaba correctamente por errores de JavaScript en `base.html`.
- Existían bloques visibles de versiones V756/V757/V758/V759 que para un cliente final parecen ruido técnico.
- En Home se mezclaban pantalla comercial pública, panel cliente, planes, radar y accesos, generando desorden.
- Había URLs rotas por pérdida de `?` en enlaces como `/calendarlane=today`, `/livef=live`, `/picksfiltro=value` o `/sharkpick=...`.
- Calendario, live y track record mostraban demasiadas capas antes del contenido real.
- Los estados vacíos no siempre guiaban claramente al usuario.

## Objetivo V760

Dejar la experiencia cliente en modo más vendible:

- Menos ruido.
- Menos repetición.
- Botones claros.
- SHARK funcional.
- Inicio cliente ordenado.
- Calendario, live, picks y track record más directos.
- Mantener intactos Telegram, Cron, DB_PATH, Madrid Time, usuarios, sesiones y V755.

## Cambios seguros aplicados

- Reparación de JavaScript global en `base.html`.
- Reparación de SHARK flotante y favoritos.
- Retirada del botón flotante global PC/Móvil; la ruta `/experiencia` sigue disponible desde acciones y menú.
- Navegación cliente simplificada.
- Home cliente reescrito para usuarios logueados, separando claramente experiencia cliente de landing pública.
- CSS V760 para ocultar ruido técnico de versiones en cliente autenticado.
- Corrección masiva de enlaces rotos.
- Nuevo check V760.

## No tocado

- No se tocó Cron.
- No se tocó `tools/render_cron_telegram_tick.py`.
- No se tocó `/api/automation/telegram/tick`.
- No se cambió `AUTOMATION_SECRET`.
- No se cambió `DB_PATH`.
- No se enviaron mensajes reales a Telegram.
- No se alteraron usuarios, membresías ni datos reales.
