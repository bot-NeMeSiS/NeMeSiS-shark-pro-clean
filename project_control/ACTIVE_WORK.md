# Active Work

## Mision local actual - 2026-09-23

Telegram Premium: cierre QA / LOCAL_ONLY de la orden mas reciente del fundador.
186 pruebas focales PASS; preview aislada 127.0.0.1:54912. Sin envios reales ni publicacion.
Alcance, archivos, evidencia exacta y limites: reports/TELEGRAM_PREMIUM_LOCAL_20260923.md.
Los cambios previos de higiene se conservan separados. No continuar otro frente automaticamente.

## Higiene previa preservada - 2026-09-23

OPS-002/CX-002: higiene estructural en `codex/repo-hygiene-20260923`, base `706094630d337f9e329a8401fae217b316a9b49c`.
Alcance: inventario, respaldo, retirada acotada de generados, reglas Git y paquete de distribucion, QA local y este registro.
PR72 sigue separado, con dos archivos sin commit; PR60/68 y mejoras antiguas no se fusionan en higiene.
Design y documental se preservan con cambios. `.pytest_cache` conserva un bloqueo de acceso; no cambiar ACL ni forzar su borrado.
La autorizacion de publicacion del bloque historico siguiente NO se aplica a esta mision.
Estado y siguientes acciones limitadas: `GIT_RELEASE_CLEANUP_REPORT.md`. No retomar automaticamente otro frente.

## Historico: frente de publicación autorizado · 2026-09-21

El fundador ha autorizado subir e integrar las mejoras desde esta conversación.
Trabajar por bloques verificables; no añadir funciones sin publicar lo validado.
Base remota: `63cd3d9a1d70d839bd0f91d78fb4875931fa635e`, posterior a PR #56.

**Bloque actual: descubrimiento de partidos en Calendario.**

- Buscador fuera del desplegable; filtros opcionales dentro del mismo GET.
- Conservar liga/país seleccionados aunque no existan en las opciones actuales.
- Avisar de cambios sin aplicar, sin alterar partidos ni contadores al escribir.
- Recuperar contexto visible, controles táctiles y foco al volver al buscador.
- Restaurar posición solo para historial válido, sin reponer datos deportivos ni
  sobrescribir una interacción iniciada por el cliente.
- 183 pruebas locales PASS, incluidas 39 de componentes Chromium; CI y despliegue
  de este bloque aún no certificados al redactar. Consultar la PR de la rama
  `chatgpt/publicacion-calendario-cliente-20260921` para el cierre.

Antes de integrar: exigir QA + preflight + Smoke completos del HEAD exacto.
Después: comprobar Web/Cron y la identidad servida; Auto Deploy es el único
mecanismo, no lanzar un deploy manual duplicado. No forzar proveedores ni tocar
DB productiva, secretos, pagos o envíos de Telegram.

Los candidatos anteriores permanecen conservados, no desplegados en su totalidad.
PR #56 ya entregó su gate y pruebas; preservar también la prueba nueva de listas
Founder. La búsqueda se entrega aquí como subconjunto frontend independiente:
no declarar corregidas las reglas de etiquetas backend ni la temporada completa.
Reconciliar los siguientes bloques contra main, no contra el antiguo `accba672`.

## Frente remoto histórico · 2026-09-20 (superado por PR #53–#56)

Único siguiente bloque autorizado por la evidencia actual: **Sports stale evidence
+ continuidad operativa**.

Objetivo:
- reutilizar `build_realtime_state_snapshot` y `_sports_entity_freshness_snapshot`;
- mantener los contadores actuales sin cambiar su clasificación;
- adjuntar como máximo 5 muestras STALE con fixture/partido, competición, proveedor,
  reloj observado, antigüedad, motivo y estado canónico;
- transportar la muestra por diagnóstico -> compact cron -> sanitizador;
- hacer que Founder OS la muestre sin llamadas a APIs;
- añadir regresiones de límite, contrato y redacción de secretos;
- actualizar `project_control` en el mismo cambio para evitar otro deploy solo por docs.

Base remota al iniciar este frente:
`c7237c4669f7f5c5e0ceefe4150fd71039b49507`, Web/Cron LIVE.

No se modifica el algoritmo de frescura, no se inventan datos, no se fuerzan
proveedores, no se alteran pagos/membresías/Telegram y no se dispara deploy manual.

## Historial local preservado · 2026-09-19


Actualizado 2026-09-19. Vista resumida; estados ejecutables solo en [CODEX_QUEUE](CODEX_QUEUE.md).

## CX-002 / OPS-002: organizacion incremental

IMPLEMENTADO Y VALIDADO LOCAL en el alcance del cierre. Clasificacion UNKNOWN y
retirada legacy siguen abiertas; ver evidencia separada en el cierre unico.

Consolidar documentos y conectar su lectura con Sentinel, sin interrumpir ni
retroceder la integracion funcional. Un integrador local: Codex. Sin agentes,
colas, schedulers ni permisos nuevos.

- Reutilizar resumenes disponibles dentro del proyecto, no chats inaccesibles.
- Un ID por trabajo en la cola, con evidencia, responsable y siguiente paso.
- Clasificar documentacion/artefactos/legacy sin retirar nada sin sus cuatro gates.
- Worktrees: main ACTIVE; Sentinel ACTIVE; Design y documental PRESERVE.
- Ninguna DB, .env, log, copia de candidato o evidencia unica se elimina.
- Inventario reproducible: tools/audit_project_organization.py, Git de lectura y metadatos. No importar app de Design.
- Evidencia detallada y rollback documental previo: data/local_dev/organization-20260919/.

## Cierre actual: preview y replay final

Preview local reproducible: tools/local_review/start_nemesis_preview.bat;
parada con stop_nemesis_preview.bat. Instancia 54910 activa al cierre.
FINAL_OVERRIDES_STALE_LIVE_V1: 10/10 local, dos fallos de producto corregidos
(upsert fuera de orden y final omitido del payload realtime). Cinco superficies.
380 casos distintos comprobados (358 + 22 tras reparar runner Windows),
45 vistas actuales y Jinja/Secret/Privacy PASS. No certificacion global/productiva.
Recomendaciones compactadas; Calendario sin main anidado. Latencia /app sigue
abierta, sin mejora significativa en A/B final. Fuentes y limites en cierre unico.

## Continuacion A-E anterior, preservada

Sentinel aceptado queda sin nuevas modificaciones. En el mismo candidato se
cierran regresiones de periodos/minuto en Directo y Match Center, reutilizacion
por request y aislamiento de usuarios en /app, alias /historico, recomendaciones
SHARK sin confianza inventada y rol ADMIN ante expiracion de membresia.
R8, soporte local, iconos y contratos deportivos conservados. Detalle en
[LOCAL_CONTINUITY](../reports/LOCAL_CONTINUITY_20260919.md).

584 PASS en seleccion transversal actual; 96 vistas/capturas y nueve adicionales
de revision final de apuestas en navegador real,
203 Jinja y Secret/Privacy PASS. No certificacion global o productiva.
122 rutas acumuladas sin commit, staged 0; 22 rutas de fuente/pruebas/herramientas
intervenidas en A-E, separadas del trabajo previo en el informe.
La convergencia visual completa, feed/cobertura, coste de primera carga,
validaciones externas y definicion ELITE+ siguen pendientes. No se crean IDs nuevos.

## Reanudar

Ediciones congeladas. Comparar solo branch/HEAD/indice y delta contra
data/local_dev/final-source-manifest.json (huella 8e3475faa5665654...). Revisar
en la vista previa LOCAL SAFE /app -> /calendar -> partido -> retorno y
/recommendations; Sentinel sigue disponible en /admin/sentinel-issues.
El proximo paso es revision humana del candidato y su alcance, no otra auditoria
global ni publicacion. No ejecutar todos los prompts historicos. Proveedor,
pagos e integracion requieren su autorizacion concreta; no iniciar automaticamente.
