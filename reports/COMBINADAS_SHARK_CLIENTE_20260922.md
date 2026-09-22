# Combinadas privadas y consejos SHARK — 22/09/2026

## Base, alcance y límites de esta entrega

Base exacta: PR63, main `efd8eee4ebcb5a21324a575e2c801c93eaf4a5d0`, árbol `9ee6f230ac01a3ffd1fc31cb24a908c0b0e43b42`. Candidato, no desplegado al redactar este informe. No integra PR59/60/64 ni sustituye el archivo estadístico candidato anterior. `app.py`, sincronizaciones, cuotas contratadas, usuarios reales, pagos y envíos Telegram quedan intactos.

La fuente local es una distribución CI de PR63 con texto recuperado; `app.py` coincide con el blob `1879f0c53e3ac59a62370906f2aabefee2c283e5`. No equivale a una copia certificada de todos los recursos binarios/blueprints opcionales. CI y navegador de la aplicación completa siguen siendo puertas de integración.

## Qué se adapta

El constructor antiguo acepta picks publicados y ya liquidados, conserva combinadas globales sin propietario y presenta confianza agregada como una característica de la combinación. Las rutas cliente se adaptan explícitamente al iniciar Flask, sin reglas URL duplicadas ni cambios dinámicos durante las peticiones:

- `/combis` pasa al mismo centro que `/combinadas`.
- `/api/combis` exige sesión y ofrece únicamente los borradores del propietario.
- `/api/combis/build` queda como vista previa sin persistencia. Esta es una diferencia de contrato deliberada: las escrituras privadas requieren el nuevo guardado explícito.
- El intento «combinada» de `/api/shark/ask` utiliza el mismo evaluador; las demás intenciones delegan al manejador anterior. Puede interpretar número de partidos, perfil y fecha; no es un modelo generativo ni un intérprete universal de apuestas.

Nuevas APIs: GET `/api/client/combinadas`, POST `/api/client/combinadas/preview`, POST `/api/client/combinadas/save`, GET `/api/shark/combi-advice`. La composición se monta en `blueprints/architecture.py`; cualquier futura integración de la PR60, que también interviene esa composición, debe conservar ambos blueprints en vez de sobrescribir el archivo.

## Un contrato de evidencia, no una apuesta

Solo fútbol 1X2 prepartido: 1, X o 2. Se exige pick publicado y pendiente, partido local inequívoco, equipos coherentes, cuota decimal válida y reciente, casa y procedencia registradas, reloj válido y mercado no cerrado. El estado y la vigencia usan las reglas deportivas existentes. Un 0–0 provisional no certifica un resultado; ninguna selección terminada o LIVE entra como nueva pata.

No se acepta más de una selección del mismo evento ni precios de casas distintas para ilustrar una oferta única. El identificador conservador de duplicados usa equipos ordenados y día Madrid: puede excluir encuentros legítimamente repetidos el mismo día antes que permitir un duplicado. No añade asociaciones por semejanza ni mezcla IDs de proveedores.

La fecha de recepción de un snapshot no renueva el reloj antiguo del proveedor cuando el payload conserva `last_update`. JSON truncado, proveedor/casa ambiguos y cotizaciones contradictorias con igual hora se rechazan. Las observaciones que solo tienen hora de recepción se marcan como RECEIPT_ONLY; no acreditan cuándo publicó la cuota el proveedor. No se usan las fechas editoriales del pick para fabricar vigencia.

El producto de cuotas usa Decimal. Es un cálculo ilustrativo, NO una oferta conjunta confirmada por la casa, probabilidad de éxito, ventaja calculada ni garantía. Se muestra el retorno condicional si todas ganan a esas cuotas y los límites de correlación. La pata de mayor cuota se explica como propiedad del precio, no como predicción calibrada. No se suman confianzas individuales. El importe de 0,10 euros es una simulación editable, no recomendación de gasto.

Se conserva el acceso a combinadas básicas desde PRO (2–3 selecciones). Se actualiza únicamente el límite central `combi_matches` de ELITE/ADMIN a 15 y el evaluador lee esa misma política. No hay un límite privado paralelo al de membresías. La propuesta automática está reservada a ELITE, de 2–15 partidos, y no rellena cuando falta muestra elegible. Los perfiles ordenan cuotas/horarios; no significan probabilidades ni un modelo predictivo.

## Borradores privados, confirmación y no repetición

Tabla aditiva `client_combi_drafts` en la base existente, creada solo al guardar con POST. Las lecturas son query-only y no migran. No se atribuyen a usuarios filas antiguas de `combis` sin propietario ni se publican los borradores privados en la cola editorial/Telegram.

El guardado relee picks, cuotas, partidos y acceso dentro de una transacción corta. Si cambia la revisión mostrada o expira la cuota, obliga a revisar de nuevo. Una clave de petición única por usuario impide duplicados; reutilizarla con otra selección se rechaza. Se almacenan hasta 100 borradores por usuario y se muestran los últimos 20, sin borrado silencioso.

La cuenta se valida en `users`, no se concede acceso por un rol de sesión sin verificación. Se respeta caducidad, cambio de plan y denegación de selecciones premium. Las respuestas del centro, APIs y SHARK son privadas/no-store. Los formularios usan CSRF existente. No se copian datos de cuenta a localStorage ni se hacen peticiones al proveedor al navegar.

Los borradores no se convierten en apuestas, banca ni ROI. No hay liquidación automática de combinadas, colocación en casas, envío automático a Telegram ni gestión de anulaciones/same-game en este bloque. Esos recorridos requieren contratos separados y evidencia real antes de activarlos.

## SHARK orientado al partido concreto

Picks, tarjetas compartidas, ficha y SHARK enlazan al mismo constructor. El panel dirigido por `pick` o `match_id` no se sustituye por el primer pick de la lista. Muestra casa, precio y hora, motivo de elegibilidad o de espera, razonamiento editorial guardado como tal y qué falta comprobar.

Reutiliza `build_team_result_evidence` de PR58 para mostrar hasta cinco resultados finales anteriores al inicio, con victorias/empates/derrotas, goles y enlaces a cada resultado. Fuente y temporada se filtran cuando son conocidas. No presenta esa muestra como toda la temporada ni como reconstrucción de lo que se sabía antes; son resultados antiguos consultados ahora. No inventa bajas, alineaciones, estadísticas ausentes ni probabilidades de ganar. No añade llamadas a un modelo generativo ni nuevos trabajadores externos.

## Pruebas realizadas

Pase local final: **262 casos distintos PASS, 0 FAIL/ERROR/SKIP**, incluidos **104 nuevos**. Se ejecutaron los tres archivos nuevos y regresiones existentes de verdad única, SHARK, evidencia de resultados y copia de snapshots. No es el total de la suite del repositorio.

Cobertura nueva: cuotas inválidas, ceros de importe rechazados, futuros relojes/caducidad, estados deportivos, mercados no 1X2, duplicados, misma casa, conflictos de precio, reloj antiguo del proveedor, planes, permisos, sesiones distintas, CSRF, lectura sin migrar, guardado/revalidación, seis reintentos concurrentes con un solo borrador, cambios de plan, datos de forma con ceros y orden, conexión Flask real y adaptación de intenciones del widget.

Cinco de los casos nuevos usan Chromium: componentes a 320/390/430/1366 px y escenario sin JavaScript. La plantilla del componente y CSS son reales, el contenedor de prueba simplifica base.html y los datos son SIMULATED_QA. Red interceptada: no son capturas de producción ni certificación integral de Safari/PWA. Formulario convencional permanece operativo; copiar al portapapeles confirma éxito solo si ocurre y ofrece selección de texto en caso contrario.

La auditoría local existente de navegación, sin ejecutar acciones, observó 830 rutas y 1138 enlaces, cero rotos y cero botones sin acción; mantiene 270 advertencias de su clasificación previa/dinámica. No se han cambiado reglas del auditor. Compilación Python y sintaxis JS, 206 plantillas Jinja y hora Madrid: PASS. Escáner existente: 1212 archivos y cero hallazgos al comprobar el código.

## Puerta de publicación

Exigir QA, Preflight y Smoke completos sobre el HEAD realmente subido, no trasladar el éxito de PR63 al candidato. Revisar fallos y diferencias de contrato. No forzar integración ni alterar umbrales para aprobar. Después de una integración autorizada: verificar SHA Web/Cron y mantener observación, sin despliegue duplicado.

La cobertura deportiva/API-Football y el archivo estadístico anterior siguen pendientes de su cierre propio. Si producción no contiene picks, cuotas y relojes suficientes, el constructor quedará vacío con motivos claros. Instalar estos componentes no genera esa evidencia. Este informe no declara una publicación ni una validación del proveedor real.
