# NeMeSiS SHARK PRO · vicepresidencia y consejo asesor

**Integración preparada en la PR borrador #305; no desplegada hasta revisión y CI.**

La Presidencia la conserva el fundador. La vicepresidencia es un sistema interno
de coordinación y asesoramiento, no una nueva persona, un modelo de IA autónomo
ni una sesión abierta de ChatGPT. Funciona sin que el fundador permanezca
conectado únicamente cuando el servicio web, el programador existente y su
almacenamiento están realmente disponibles.

## Operación en la infraestructura actual

1. El Cron existente convoca el endpoint protegido de Continuous Evolution.
2. Una revisión nativa por franja horaria analiza 15 responsabilidades
   Company OS y 7 especialidades Game UI bajo presupuesto acotado.
3. En el mismo recibo se guarda el resumen de vicepresidencia:
   hallazgos estáticos, vacíos de evidencia y agenda limitada.
   No se crean nuevas tareas, otro Cron, servidores o llamadas de IA.
4. La vista protegida /admin/company-os presenta la jerarquía y el consejo.
   Abrir la página no inicia tareas.
5. Founder Brief diario continúa como síntesis existente. La prueba está
   en recibos y revisión exacta, no en el número de nombres de trabajadores.

## Delegación y permisos

| Operación | Sin el fundador |
|---|---|
| Leer recibos internos, comparar evidencias y clasificar | Revisiones de solo lectura |
| Preparar prioridades, propuestas y brief | PROPOSE_ONLY |
| Código, PR, merge, deploy, Telegram, precios, planes, usuarios, proveedor o presupuesto | Necesitan aprobación explícita y protecciones existentes |
| Cobrar/reembolsar, apostar, envíos masivos, forzar push o sustituir la BD | Prohibidos a la automatización |

La política del módulo es solo informativa: no concede permisos HTTP.
Nunca se confiere el cargo ejecutivo como permiso técnico independiente.

## Consejo y revisión cruzada

Hay diez funciones: estrategia/producto, finanzas, arquitectura, seguridad,
cumplimiento, datos deportivos, SHARK, Game UI/UX de videojuegos,
marketing/ventas y clientes/soporte. No son empleados contratados ni modelos
independientes únicamente por existir su definición.

Las tríadas de 15+7 áreas distinguen analista, verificador de evidencia y
revisor crítico. Sus hashes estáticos NO equivalen a votos independientes.
Se requiere validación adicional, incluidos navegador, producción o
revisión humana, según el riesgo.

## Pruebas y puesta en marcha

- Tests de permisos, fail-closed, recibos recientes/viejos y no ejecución ficticia.
- El recibo horario incluye vicepresidency_readout pero conserva expected_count=22.
- El panel refleja AWAITING_RECENT_REVIEW sin recibo o
  RECENT_STATIC_COORDINATION con revisión estática reciente.
- Ningún GET inicia ciclos o escribe en BD.
- No dar por resueltos backups, 502, Stripe, cuotas o pausa TheSportsDB por
  existir este sistema de dirección.
- Mantener PR en borrador, ejecutar CI y revisar la integración con main,
  antes de aprobar cualquier despliegue.
