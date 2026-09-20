# Active Work

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
