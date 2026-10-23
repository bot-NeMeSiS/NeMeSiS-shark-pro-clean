# V986 — Exportar partidos verificados al calendario

Desde el detalle de un partido, el usuario puede descargar un archivo iCalendar
con los equipos, la competición disponible y, si hay una URL pública canónica
configurada, un enlace de vuelta al detalle.

El handler usa solo datos ya guardados y no consulta proveedores. La descarga
es un GET de solo lectura: omite la inicialización global, abre la base existente
en modo lectura y devuelve un error de servicio no disponible si la base o su
tabla no están disponibles; nunca crea la base ni aplica migraciones. La consulta
se adapta a columnas opcionales ausentes en esquemas antiguos. Si la fuente solo
ofrece la fecha, el evento se exporta como recordatorio de día completo y lo
indica; no se inventa una hora ni una duración. Los partidos cancelados o
abandonados conservan ese estado en la exportación. Para aplazados, suspendidos,
desactualizados, incompletos o contradictorios, la pantalla explica que falta
una fecha fiable y no descarga una cita ambigua. Los registros cargados desde el
archivo histórico no muestran un enlace de exportación que la ruta actual no
puede resolver. Las rutas de descarga mal formadas tampoco ejecutan el arranque
ni escriben diagnósticos de 404. El archivo es un iCalendar estático, no un mensaje iTIP PUBLISH;
no inventa organizador, fecha ni duración. La pantalla y la descarga avisan que
la importación no se actualiza automáticamente.

Las horas locales de Madrid que caen en el salto de primavera o en la hora
repetida del otoño tampoco generan una cita inventada: si la fuente no incluye
un desplazamiento horario y la hora civil no identifica un único instante, la
exportación la rechaza con la misma explicación de fecha no fiable. Una hora
con desplazamiento explícito sigue pudiendo exportarse.

Se fija `tzdata==2026.5` en los requisitos para que Windows tenga la base IANA
que `zoneinfo` necesita cuando el sistema no la proporciona.

Validación local: 70 pruebas enfocadas PASS: 12 de exportación, 22 del centro
de partido, 18 de assets canónicos y 18 variantes adaptables del Calendario.
Se comprobó conversión UTC, fecha sin hora, escape y plegado UTF-8, descarga
GET, host canónico configurado, estados de partido, rechazo explicado cuando
no hay fecha fiable, petición fría sin inicialización ni escrituras, esquema
antiguo, base ausente sin creación, rutas mal formadas sin efectos laterales
y ausencia del enlace para partidos archivados. py_compile, JSON y
git diff --check también pasan.

Una revisión del calendario real en Chromium a 320 px reprodujo el mecanismo:
una tarjeta lejana con `content-visibility:auto` devolvía `innerText` vacío;
tras entrar en la ventana y renderizar, mostraba ambos equipos. Se ajustó la
prueba para desplazar cada tarjeta al área visible y medir texto y geometría
después del render; en el caso sin JavaScript se usa la rueda del navegador y
una espera de pintura, sin relajar las aserciones ni cambiar CSS de producción.
El módulo completo pasó 18/18 variantes y la batería enfocada pasó 70/70.

La primera repetición amplia se detuvo al 47 % por un subproceso de diagnóstico
que devolvía texto con la codificación local de Windows, mientras el proceso
principal esperaba UTF-8. El caso exacto pasó al heredar UTF-8; no se modificó
la aplicación por esta incompatibilidad del entorno de prueba. La repetición
final, con UTF-8 heredado y Chromium local, recopiló 5.801 pruebas: 5.797
pasaron, 4 se omitieron y ninguna falló. Se excluyeron las seis suites
especiales ya separadas del conjunto principal: final replay, continuidad local
de cliente, HTTP de control de proyecto, HTTP de trabajos Sentinel, navegador
operativo Sentinel y tarjeta visual premium de Telegram. Este resultado no
declara ejecutadas esas suites excluidas.

La validación final también pasó py_compile para app.py y el motor, lectura del
catálogo JSON y git diff --check. El cambio permanece solo en el worktree: no
hay commit, push, CI, integración ni despliegue. Render sigue en V985 hasta que
el propietario publique la candidata.

Regresión suplementaria posterior: 18 pruebas locales de control de proyecto
y trabajos Sentinel pasaron. En una ejecución separada de tres suites que
requieren una sesión LOCAL SAFE preconfigurada, cuatro casos no lograron
completar sus expectativas de autenticación/preview; se excluyen de los conteos
de V986 y no se atribuyen al cambio de Calendario. No se alteró código de
producto por ese resultado. La suite Sentinel de navegador operativo se dejó
sin ejecutar porque su carpeta fija de capturas ya contenía artefactos previos.

Validación después de los ajustes DST y de dependencia: 71 pruebas PASS en
exportación (13), centro de partido (22), assets canónicos (18) y navegador
adaptable (18). `py_compile` y `git diff --check` también PASS. La batería
amplia de 5.797 PASS/4 SKIP se ejecutó antes del ajuste DST y no se presenta
como repetida después. La validación final utilizó un entorno virtual aislado,
`tzdata==2026.5` y Chromium local; Playwright se instaló solo en ese entorno de
pruebas, no en los requisitos del producto.
