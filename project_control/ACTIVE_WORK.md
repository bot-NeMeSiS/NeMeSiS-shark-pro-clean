# Active Work

## UX-002 / App Icon Identity

Estado: **BLOCKED** para produccion; implementacion y pruebas locales completadas.
Commit selectivo cdd88e507a9dd422d7e528f8eb795c2030060c3c, rama
codex/app-icon-identity, [PR #9](https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean/pull/9).
Sin wallpaper, nuevo shark, cambio de CSS global ni logica deportiva.
139/139 focales sobre HEAD base + iconos; 199 Jinja, compilacion, Secret/Privacy,
diff-check y performance SHARK local correctos. Suite combinada 590/602 PASS,
12 bloqueos previos LOCAL SAFE, 0 errors; no PASS global.
Bloqueos CI preexistentes reproducidos en logs base/nuevo: Playwright falta en
smoke; preflight exige resultado Browser QA V944 no generado por el workflow.
No eliminar checks, copiar evidencias antiguas ni hacer bypass. Reparacion CI
requiere alcance separado. Render workspace aun sin confirmacion; no deploy.
Evidencia privada: `.tmp_reference_review/app_icon_20260909/`; no incluir en PR.
Todos los temporales DB de esta QA retirados tras terminar los procesos.
Se detiene aqui; no iniciar CX-RESULTS ni otra limpieza.

## CX-ORG-01 / CX-002

Estado: **QA**, evidencia LOCAL_ONLY. Alcance conocido implementado; pendiente
revisar el tramo de autorizacion truncado en `SUPERSE`. No declaracion de purga total.
Responsable: Codex integrador unico. No subagentes/editores simultaneos creados.
Base: c6eaa003e6ae0e9d4af7d98198ec6eefafc97b04. Indice y candidato SE-01 protegidos.

### Ejecutado

- 13 documentos canonicos en project_control; referencias desde entradas previas.
- Jerarquia factual, cola unica, IDs/aliases y gates FIRST 10; sin nuevas capacidades.
- Inventario privado por ruta/hash/clase de los 4122 tracked, mas test SE-01 protegido.
- Clasificacion inicial: CANONICAL 523, HISTORICAL 2499, SUPERSEDED 9,
  RUNTIME 317, UNKNOWN 774. SUPERSEDED significa autoridad operativa desplazada,
  no contenido eliminado. Imports estaticos no demuestran ejecucion real.
- 142 grupos byte-identicos, 284 archivos: retenidos. Entre ellos VERSION/APP_VERSION,
  inicializadores, workflows y documentacion con contratos de ruta distintos.
- Retirada verificada: 393 .pyc, 11.162.408 bytes, solo dos caches de compilacion
  del run SE-01 terminado. Cero archivos versionados retirados. Cero codigo/runtime
  de negocio retirado. Manifiesto previo, hashes, limites absolutos y resultado guardados.
- Gitignore ampliado solo para temporales QA conocidos y sidecars SQLite3.
  Ignorar no equivale a dejar de versionar archivos ya tracked ni impide `git add -f`.
- Empaquetador: las exclusiones comunes se evaluaban despues de aceptar reports.
  Se adelantan dentro de include; mismas listas y demas funciones por AST.
  Diez casos negativos reproducian inclusion indebida; 24/24 pasan tras corregirlo.
  La seleccion de los 4122 archivos ya tracked sigue identica; no ZIP generado.

### Verificacion local de CX

- 24 tests de politica de empaquetado: 24 PASS, 0 FAIL/ERROR/SKIP.
  Antes del fix: los mismos 24, 14 PASS y 10 FAIL. Sin modificar expectativas.
- 13 documentos, 35 enlaces locales y 20 IDs unicos comprobados; estados/evidencia
  de la cola validados. 13 casos de ignore con positivos y negativos correctos.
- Compilacion de los dos Python de higiene; Secret/Privacy existente: 26 archivos,
  0 hallazgos. git diff --check exit 0. No imports de app ni generadores de reports.
- 4111 archivos previos byte-identicos; 12 existentes modificados deliberadamente
  en este alcance y 14 nuevos. Fuentes/tests SE, DAY 3/4/5, informe SE, HEAD e indice
  intactos. Los ocho cuerpos historicos se conservan, agregando solo el enlace.
- Pruebas sin DB, red ni procesos hijos. Tres consultas automaticas de version
  Windows de platform.py fueron bloqueadas antes del proceso; no afectaron tests.
  Arranque del arnes ajustado a temporales/log privados; ningun guard desactivado.
  El verificador admite solo Git de lectura, con formato Windows comprobado.
- No nueva suite global ni navegador: no cambia el producto, templates o estilos.
  Se preserva la evidencia SE previa, no se presenta como ejecucion nueva de CX.

### Evidencia privada y retencion

Directorio existente de evidencias: `.tmp_reference_review/cx_org_01_20260909/`.
before.json + copias selectivas, inventory.json, retirement.json, verification.json.
Excluido de Git/release; no copiarlo a project_control. No contiene DB/copias de cuenta.
Los XML, manifiestos, guardas, informe y pruebas SE-01 no se retiraron.
La cache eliminada es regenerable, no la evidencia de los tests.

Seis directorios historicos inaccesibles: retenidos, sin reparar ACL, ocultar su
existencia ni afirmar inventario interior completo. Los entornos .venv y copias
release_output se conservan; no se inspeccionan secretos ni se clona el workspace.

### Pendientes y parada

- Alcance conocido validado localmente; revision del cierre, no certificacion productiva.
- Confirmar workspace de Render para lectura posterior; no configurarlo por inferencia.
- Revisar parte faltante de autorizacion antes de cualquier retirada adicional.
- CX-RESULTS-01 NO INICIADO. Sin limpieza legacy funcional ni desarrollo deportivo.

El detalle historico SE-01 permanece en su informe; no se reescribe el XML global
de 543 PASS, 12 no certificados y 0 errors.
