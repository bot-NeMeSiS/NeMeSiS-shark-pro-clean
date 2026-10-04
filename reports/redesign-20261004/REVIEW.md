# NeMeSiS SHARK PRO — entrega visual final

Rama: `redesign/core-client-founder-20261004`. Base: `b7e8aea1`. Revisión local con aplicación Flask y sesiones aisladas; sin merge, deploy, cambios de secretos, pagos ni Telegram real.

## Resultado

Implementados los bloques A–F sobre un Core común, con experiencias cliente y Founder/Admin separadas. El diseño utiliza Dark Premium, jerarquía deportiva, LIVE rojo con confirmación real y SHARK violeta/verde. Se consolidan los propietarios existentes de los componentes; no se añade una hoja global de overrides.

El Master Finalization Program permanece **BLOQUEADO por certificación de almacenamiento pendiente**. La rama visual no autoriza cerrar ese programa ni desplegar. DB_PATH y la lógica de certificación no se modifican.

## Pantallas terminadas y defectos eliminados

| Bloque | Implementación y revisión |
|---|---|
| A | Shell, Home y navegación común; fondo neutro, profundidad, contraste, tipografía, tarjetas y acciones. Cinco destinos principales y cuenta desplegable móvil. Una cuenta admin en una ruta cliente conserva el shell cliente. |
| B | Live, Calendar y Match Center; marcador, equipos, competición y hora de Madrid prioritarios. Partidos reales programados/finalizados y estado no disponible. Diagnóstico de calidad/procedencia restringido a admin; estados técnicos traducidos. |
| C | Picks, Combinadas y SHARK; constructor y ayuda consumen Core, acciones IA violeta, estados sin pronósticos claros y sin ejemplos inventados. Límites y validación de selecciones intactos. |
| D | Cuenta reconstruida con componentes canónicos, membresías, login, registro, onboarding, favoritos, soporte y estados de carga/vacío/error. Renovación, portal y permisos conservan sus condiciones existentes. Iconos canónicos de soporte, salida y avisos. |
| E | Founder/Admin con densidad operativa propia. Recomendaciones accionables antes de métricas y chat, auditoría e histórico secundarios. Aprobar propuestas y cerrar sesión dejan de recibir énfasis de acción primaria/peligro. Bloqueo de almacenamiento arriba. |
| F | Adaptación real a 320, 390, 768, 1024 y 1440 px; navegación táctil, controles agrupados, carruseles contenidos y ningún desbordamiento horizontal de página detectado. Calendar evita pintar tarjetas fuera de pantalla sin cambiar datos. |

Los logos usan los assets oficiales/cacheados existentes y un fallback de iniciales estilizadas ante ausencia o error. No se inventan escudos oficiales. Los errores de carga remota se probaron bloqueando imágenes externas; no quedan imágenes rotas visibles.

Se eliminan de las superficies cliente mensajes de infraestructura y códigos técnicos: runtime, cron, storage, provider, cache, backfill, sentinel, PARTIAL/PASS/FAIL y DB_PATH. El filtro se aplica en Jinja y en actualizaciones dinámicas existentes. Ejemplos: NO_STATISTICS → «Estadísticas todavía no disponibles»; PROVIDER_UNAVAILABLE → «Datos temporalmente limitados». Las explicaciones de SHARK y Home utilizan lenguaje de usuario.

## Consolidación del diseño

- Ocho fuentes globales históricas retiradas del build y de enlaces de plantillas; dos propietarios editables: `design-tokens.css` y `design-system.css`. Los archivos históricos permanecen como referencia/compatibilidad de pruebas y no se sirven como capas globales.
- 200 variables históricas aliasadas al Core. 117 flags de activación históricos retirados del body; un flag contractual de compatibilidad y los hooks de componentes se conservan.
- 28 reglas inactivas de `data-v808-shell` retiradas antes de normalizar selectores, evitando activarlas accidentalmente.
- 1.175 declaraciones redundantes/sobrescritas retiradas de la cascada activa, respetando importancia y contexto condicional; la primera fase ya había retirado 178 duplicados exactos en fuentes históricas.
- Bundle compilado: 1,249,114 → 1,182,646 bytes, reducción 5.32 %. Fondo oceánico de 1.725.019 bytes retirado de las descargas de las superficies revisadas.
- Las hojas funcionales de constructor, ayuda y Founder consumen Core. Los selectores históricos de componentes que conservan un contrato real no se borran a ciegas.

La comparación visual está en `GALLERY.html`; reglas del Visual Master en `VISUAL_MASTER.md`. Las referencias anteriores orientan estructura e identidad, mientras que la dirección actual sustituye su fondo oceánico dominante y LIVE verde. No se afirma coincidencia exacta de píxeles con maquetas anteriores.

## Datos y método de validación

La matriz principal importa **387 registros deportivos reales** del endpoint público cacheado `/api/realtime/sports?scope=all`, generado el 4 de octubre de 2026 a las 21:35:49, Madrid. El endpoint declara `no_external_calls=true`. Tres fichas completas se obtuvieron de `/api/matches/<id>/detail`, con `database_writes=0` y `external_calls=0`; se conservan identidad y timestamps originales.

Las capturas respetan la caducidad de Sports Truth: un registro que era LIVE en la captura fuente ya no se presenta como directo cuando ha vencido. No se cambian relojes ni se prolonga la validez para fabricar una pantalla poblada. No hay pronósticos publicados en la muestra; Picks muestra el estado vacío real. Estadísticas, alineaciones, vídeo y cuotas solo aparecen cuando la fuente los aporta. No se invocó IA externa para obtener una respuesta de muestra.

Las cuentas «Revisión» son identidades de prueba en una copia SQLite aislada con OFFLINE_SAFE. No son usuarios de producción ni datos deportivos simulados. El snapshot y las credenciales locales de revisión permanecen fuera de Git.

El antes procede de las plantillas y CSS inmutables de `b7e8aea1`, con la misma copia deportiva y el mismo backend actual. Esto permite comparar presentación; no representa un benchmark de un backend histórico diferente.

## Pruebas ejecutadas

- **497 pruebas únicas superadas**, 0 fallos/errores: Core, referencias, Home, Madrid Time, Jinja/contratos, sesiones concurrentes, acceso, membresías, límites SHARK, Sports Truth, Founder, Telegram en preview seguro y backups. Las repeticiones se deduplican por caso.
- **155 capturas finales** de 31 rutas en cinco tamaños; **54 capturas históricas** PC/tablet/móvil. Las últimas capturas específicas sustituyen las anteriores de Home, SHARK y Match Center tras la limpieza de copy.
- En la matriz final: 0 overflow horizontal de página, 0 IDs duplicados, 0 errores JavaScript, 0 imágenes rotas visibles, 0 respuestas 5xx y 0 términos técnicos detectados por el escáner de texto cliente. Encabezados y textos de marcador comprobados por geometría.
- `/match/unavailable` devuelve 404 deliberadamente con una pantalla legible. Las demás rutas examinadas responden 200.
- Navegación móvil comprobada con acciones reales de abrir cuenta, soporte, Calendar y Live; foco por teclado. Se mantienen CSRF y las protecciones de operaciones.
- 197 plantillas Jinja parseadas; sintaxis JavaScript comprobada; bundle regenerado y validado contra sus fuentes; diff verificado.
- Tráfico externo del navegador bloqueado: **56 intentos de recursos externos** en la matriz, no solicitudes ejecutadas. La comprobación dirigida identifica imágenes de `r2.thesportsdb.com`; el fallback funciona. No se afirma ausencia de URLs remotas ni cobertura oficial certificada.

Los registros por captura, imágenes, pruebas XML y muestras de rendimiento acompañan la entrega. Los fallos de invocación de herramientas intermedias y pruebas mal configuradas no se contabilizan como comprobaciones superadas.

## Rendimiento comparado

22 rutas, cinco muestras calientes alternadas por versión (220 muestras). Instrumentación real de render Flask y sentencias SQLite, mismas plantillas históricas/actuales sobre backend actual y datos cacheados idénticos. Sockets salientes prohibidos. Cliente y admin medidos en ejecuciones separadas. Los últimos cambios menores de texto y la retirada de CSS inactivo no añaden consultas.

| Ruta | Antes, ms | Final, ms | Mediana SELECT antes / final |
|---|---:|---:|---:|
| /app | 328.37 | 302.73 | 23 / 23 |
| /calendario | 982.44 | 881.78 | 25 / 25 |
| /directo | 448.41 | 493.18 | 24 / 24 |
| /picks | 547.76 | 505.40 | 25 / 25 |
| /combinadas | 71.49 | 78.94 | 15 / 15 |
| /shark | 540.53 | 563.77 | 29 / 29 |
| /telegram | 180.08 | 188.97 | 26 / 26 |
| /mi-cuenta | 137.07 | 146.56 | 16 / 16 |
| /membresias | 41.21 | 39.89 | 7 / 7 |
| /onboarding | 146.94 | 145.22 | 17 / 17 |
| /match/sportsdb-ae6b4725f87f9b98dc | 80.68 | 71.57 | 29 / 29 |
| /match/sportsdb-7c11bc365f563d85f5 | 63.81 | 61.44 | 28 / 28 |
| /match/sportsdb-22f9acca23e1cc306a | 67.05 | 63.20 | 27 / 27 |
| /admin/dashboard | 529.21 | 638.67 | 57 / 57 |
| /admin/matches | 354.29 | 385.42 | 67 / 67 |
| /admin/picks | 2995.39 | 3034.93 | 980 / 980 |
| /admin/telegram/command-center | 3347.59 | 2889.40 | 1071 / 1071 |
| /admin/users | 2836.05 | 2857.62 | 983 / 983 |
| /admin/memberships | 3313.59 | 3424.84 | 985 / 985 |
| /admin/data-center | 3627.72 | 4638.53 | 1067 / 1067 |
| /admin/founder-os | 10.73 | 10.33 | 4 / 4 |
| /admin/founder-control | 9.29 | 9.08 | 4 / 4 |

En las 13 rutas cliente los conteos SELECT coinciden en las cinco muestras: 0 escrituras y 0 intentos externos del servidor. Las medianas SELECT de las nueve rutas admin también coinciden. El backend existente renueva periódicamente una caché: aparecen muestras con 635 lecturas adicionales y una UPDATE tanto en el antes como en el final. Esa renovación se conserva y no se atribuye a la presentación.

No hay mejora universal de latencia: Live, Combinadas y algunas superficies admin tienen medianas superiores en esta máquina; Calendar y otras rutas mejoran. Los paneles admin heredados de usuarios, membresías, picks y datos hacen aproximadamente 980–1.071 SELECT por petición habitual y siguen siendo costosos. La comparación no certifica carga de producción ni dispositivos físicos. La reducción de bytes CSS y la retirada del fondo sí son medidas objetivas del recurso servido.

## Riesgos y bloqueos pendientes

1. **Almacenamiento:** certificación externa de persistencia pendiente; Master Finalization Program bloqueado. No se cambian backups, DB_PATH ni persistencia para resolverlo dentro de un rediseño.
2. **Datos externos:** no se inventa cobertura ausente. Sin publicaciones reales no se puede certificar visualmente cada combinación de pick, alineación, estadística, vídeo o respuesta IA; sus contratos y estados disponibles se prueban, sin llamadas externas ni ejemplos publicados.
3. **Carga operativa:** coste de lecturas admin y renovaciones de caché heredados documentados. Requieren una revisión de rendimiento del backend con carga representativa antes de prometer mejores tiempos.
4. **Dispositivos:** capturas Chromium locales en cinco tamaños; quedan pendientes pruebas en dispositivos físicos y otros navegadores, y aceptación final de las capturas.
5. **Publicación:** rama y PR separados para revisión; ningún merge/deploy, pago o envío real autorizado/ejecutado. El PR se crea draft con `[skip preview]` para evitar previews automáticos de Render ([documentación oficial](https://render.com/docs/service-previews)).

Las carpetas anteriores after/before/evidence/final/founder y css-comparison.json son evidencias de una fase parcial, conservadas como histórico. La aceptación final usa exclusivamente screenshots/, GALLERY.html, route-performance.json, tests.xml y evidence-summary.json.

## Contratos conservados tras CI

Los probes operativos que detectan capacidades leyendo claves históricas de base.html conservan esas claves en un registro Jinja no renderizado. No vuelven a activar CSS ni se altera la lógica de cierre. Cuenta conserva el usuario de Telegram vinculado y la explicación de privacidad de actividad. Las pruebas anteriores que exigían textos Stripe/técnicos o diagnósticos visibles en cliente se actualizan al lenguaje y a la separación acordados, manteniendo las comprobaciones de lecturas únicas, permisos y ausencia de escrituras. La suite local ampliada reúne 497 pruebas únicas superadas.
