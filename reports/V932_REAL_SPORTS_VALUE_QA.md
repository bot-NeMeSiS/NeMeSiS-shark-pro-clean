# V932 Real Sports Value QA

## Verdad local

- Partidos reales completos disponibles: no.
- Live real disponible: no.
- Picks reales publicables disponibles: no.
- Ultima sync segura local: `2026-07-10T16:22:46Z`.
- Llamadas externas durante render: 0.

La DB local se mantiene sin agenda completa. Cliente muestra un estado breve y comprensible; admin recibe el diagnostico de proveedor/cache, ultima sync, registros validos, incompletos excluidos y accion protegida recomendada.

## Gate verificado

Una DB temporal aislada comprobo que:

- contador y lista de hoy usan exactamente el mismo conjunto;
- competicion, fecha, hora, equipos y fuente son obligatorios;
- registros incompletos van a `incomplete_matches`;
- live solo aparece con estado real valido;
- un pick solo pasa con mercado, seleccion, cuota mayor que 1, estado publicado, partido vigente y fuente no ficticia;
- picks sin cuota o con fuente placeholder quedan bloqueados;
- el render no invoca proveedores externos.

Los datos sinteticos usados por el check existen solo dentro de una DB temporal y nunca se escriben en la aplicacion o en produccion.
