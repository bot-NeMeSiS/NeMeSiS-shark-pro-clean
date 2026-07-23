# PQV939-007 - Alcance, evidencia y propuesta controlada

Fecha Madrid: 2026-07-23

## Definicion literal del backlog

- Titulo: `Fecha de sincronizacion en formato ISO crudo`.
- Prioridad: P2.
- Pantallas y timestamps del video: barra de sincronizacion y paneles laterales en casi todo el recorrido; ejemplos 00:25, 02:07 y 02:26.
- Elemento visible: `2026-07-22T14:25:21+02:00`.
- Descripcion: la marca es correcta y trazable, pero usa un formato tecnico menos legible que `22 jul 2026, 14:25 · Madrid`.
- Impacto: reduce claridad y coherencia con la promesa de Hora Madrid.
- Comportamiento esperado: fecha legible en cliente, Madrid explicito e ISO original conservado para maquinas y diagnostico admin.

## Pantallas y consumidores demostrados

El macro compartido `realtime_state_bar` se consume en cliente desde `/`, `/app`, `/calendar`, `/live`, `/picks` y `/match/<id>`. El macro `provider_state` se consume en `/app`, `/calendar`, `/live`, `/picks` y `/match/<id>`. El mismo estado de tiempo real se usa en admin desde `/admin/dashboard`, `/admin/data-center`, `/admin/data-trust-center` y `/admin/realtime-center` con `technical=true`.

## Evidencia de codigo

1. `templates/components/v933_ui.html` imprime `last_sync` directamente en `provider_state`.
2. El mismo archivo imprime `last_safe_sync` directamente en `realtime_state_bar`, sin separar presentacion cliente y evidencia tecnica.
3. `static/v934-realtime.js` vuelve a escribir `payload.last_safe_sync` como texto visible despues del polling, por lo que una correccion solo en Jinja reapareceria al refrescar.
4. `engines/v934_realtime_sports_engine.py` conserva correctamente el ISO en `last_safe_sync`, pero no entrega una etiqueta de presentacion.
5. `app.py` ya dispone de filtros Madrid y `engines/madrid_time_engine.py` ya centraliza parseo y conversion de zona. No hace falta crear un motor ni duplicar reglas de timezone.
6. Las APIs y el centro admin ya conservan la marca ISO, por lo que la trazabilidad tecnica puede mantenerse sin exponerla como copy cliente.

## Causa raiz confirmada

La capa de dominio entrega una marca ISO correcta, pero el contrato compartido no distingue `valor de maquina` de `etiqueta visible`. Tanto el render inicial como el polling usan el valor de maquina como copy. No es un problema de datos, DB, proveedor, timezone ni CSS.

## Doble perspectiva

### Cliente

El ISO aumenta esfuerzo de lectura y parece un detalle interno. Debe ver una fecha breve en espanol, hora de 24 horas y `Madrid`, sin perder frescura ni trazabilidad.

### Admin

El operador necesita la marca exacta para diagnostico. El modo `technical=true`, las APIs protegidas y el atributo `datetime` conservaran el ISO original; la correccion no elimina informacion tecnica ni altera datos.

## Propuesta minima aprobada por alcance

1. Incorporar al motor Madrid existente un formateador generico y determinista para marcas de sincronizacion.
2. Exponer una etiqueta `last_safe_sync_label` junto al ISO ya existente, sin sustituirlo.
3. Registrar un filtro Jinja especifico que delegue en ese unico formateador.
4. Mostrar la etiqueta solo al cliente y conservar el ISO en `datetime`, atributo de evidencia, API y modo admin tecnico.
5. Hacer que el polling use la etiqueta cliente y nunca restaure el ISO visible fuera del modo tecnico.
6. Ampliar Sentinel, AutoPilot y Company Intelligence existentes con el contrato PQV939-007, sin autocorreccion.
7. Crear pruebas de comportamiento y mutacion, y Browser QA aislado desktop/movil.

## Archivos autorizados

- `engines/madrid_time_engine.py`
- `engines/v934_realtime_sports_engine.py`
- `app.py`
- `templates/components/v933_ui.html`
- `static/v934-realtime.js`
- `engines/sentinel_autopilot_engine.py`
- `engines/continuous_shark_sentinel_engine.py`
- `engines/company_intelligence_engine.py`
- `tests/test_v939_product_perfection_p2.py`
- informes y evidencia exclusivos de PQV939-007
- `reports/PRODUCT_QUALITY_MASTER_REVIEW_V939.md`, solo al cerrar todas las pruebas

## Fuera de alcance

- CSS y diseno general.
- `sports-metrics-v1` y `match_card()`.
- logica deportiva, DB, SHARK, Picks, Telegram, Stripe, Operations Center y Recovery.
- cualquier otro P2 o P3.
- `PROJECT_NEMESIS_SPORTS_EXPERIENCE_MASTER_SPECIFICATION.md`.

## Impacto esperado

- El cliente deja de ver ISO crudo en render inicial y polling.
- Admin y APIs conservan la evidencia exacta.
- No cambian consultas, escrituras, polling, rutas, contadores ni datos.

## Riesgo y reversion local

Riesgo bajo: una entrada temporal invalida podria quedar sin etiqueta. El formateador usara un estado seguro y las pruebas cubriran UTC, offset Madrid, valor vacio e invalido. La reversion local consiste en retirar solo el formateador, la etiqueta derivada y sus consumidores de este diff; no requiere tocar DB ni datos.

## Pruebas necesarias

- Conversion UTC/Madrid y etiqueta espanola determinista.
- Render cliente legible con ISO preservado en atributos.
- Render admin tecnico con ISO exacto.
- Polling cliente usa `last_safe_sync_label` y admin conserva `last_safe_sync`.
- Mutacion que reintroduce el ISO visible abre P2 y reduce Sentinel/AutoPilot.
- Company Intelligence guarda causa, impacto, regla, QA, version, fecha Madrid y `RESOLVED_LOCALLY` solo en memoria temporal autorizada por test.
- Browser QA 1366x768 y 390x844 en rutas afectadas y de regresion.

## Regla preventiva y tarea AutoPilot

Sentinel debe fallar si un cliente imprime `last_sync`/`last_safe_sync` sin el formateador, si el polling usa el ISO como copy o si se pierde el atributo de evidencia. AutoPilot debe crear una tarea P2 especifica con archivos probables, pruebas y aprobacion humana obligatoria; nunca debe editar DOM, CSS, datos, Git ni produccion.

## Criterios de aceptacion

- Cero ISO crudo visible en HTML cliente, antes y despues del polling.
- `Madrid` visible y hora convertida correctamente.
- ISO intacto en `datetime`, atributo de evidencia y API.
- Modo tecnico admin conserva la marca exacta.
- Cero 500, overflow, errores de consola o mezcla de navegacion en el alcance probado.
- Sentinel detecta la mutacion, AutoPilot no autocorrige y Company Intelligence registra aprendizaje local.
