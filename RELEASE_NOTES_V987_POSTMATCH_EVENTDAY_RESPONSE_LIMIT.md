# V987 — Límite acotado para el catálogo diario de TheSportsDB

El Postmatch falló en producción con `eventsday.php`, `MALFORMED` y etapa
`TRANSPORT`. En V986, el lector emite esa firma si el cuerpo rebasa 512 KiB;
el tamaño real del cuerpo no quedó registrado, así que el diagnóstico apunta a
ese límite pero no lo demuestra por sí solo.

V987 eleva el máximo solo para `eventsday.php` a 2 MiB. Los demás endpoints
conservan 512 KiB. Al superar el máximo nuevo, el worker rechaza la respuesta y
registra la etapa cerrada `RESPONSE_SIZE_LIMIT`, sin guardar el cuerpo ni datos
del proveedor. No cambian llamadas, presupuesto ni reglas de selección de datos.

Una prueba adicional con catálogos densos reveló un segundo límite: el limpiador
compartido del archivo rechazaba la respuesta antes de que la caché operacional
decidiese omitirla por superar sus 128 KiB. V987 mide primero el JSON permitido y
omite esa caché cuando no cabe. La respuesta sigue disponible en memoria durante
el trabajo; el archivo conserva sus límites y las cachés pequeñas mantienen su
saneamiento, caducidad, retención y control de sesión de trabajo.

Validación local con Python 3.11.9: una respuesta sintética de 600 KiB y otra
de exactamente 2 MiB se aceptan; 2 MiB + 1 byte se rechaza de forma segura; el
límite de 512 KiB de otro endpoint se mantiene. Los catálogos densos de 700 y
1.500 eventos encuentran el partido correcto cerca del final con una llamada,
reutilizan memoria y no se guardan en la caché operacional. Un catálogo de
1.501 eventos sigue rechazándose. Se comprueban saneamiento y caducidad de la
caché pequeña, valores no finitos, errores SQL y trabajo con lease vencido.

El módulo final pasa 49/49 casos. Once módulos relacionados pasaron 394 casos
antes de los dos últimos casos del módulo, por lo que ambos conteos no se suman.
La regresión principal final terminó con 5.811 PASS, cero fallos/errores y cuatro
SKIP: un caso de symlink sin privilegio Windows y tres de Gunicorn que requieren
Linux. Las siete fuentes vigiladas no cambiaron y no hubo intentos de conexión
externa. Los 5.802 PASS anteriores corresponden al snapshot previo a la caché.
El primer intento final terminó con 4.724 PASS, una omisión y un fallo en la
prueba de procesos paralelos: el lanzador externo a la aplicación carecía del
guard de arranque de Windows y volvió a ejecutar pytest en un hijo, que chocó
con el temporal del padre. Ese intento no se considera aprobado. El mismo caso
pasa con el lanzador protegido, sin cambiar la aplicación ni el test. La batería
principal completa terminó correctamente con ese lanzador y un temporal independiente.

La batería principal excluye estas seis suites especiales, ejecutadas aparte:
`test_final_replay.py`, `test_local_client_continuity.py`,
`test_project_control_http.py`, `test_sentinel_jobs_http.py`,
`test_sentinel_operational_browser.py` y `test_telegram_visual_premium.py`.
Las seis terminaron con 104 PASS, cero fallos, errores u omisiones, con LOCAL
SAFE y bases aisladas. Cubren replay HTTP/navegador (10), continuidad (1),
control de proyecto (8), trabajos HTTP (10), navegador operativo (1) y Telegram
visual (74). Todas conservaron los controles de roles/CSRF y la frontera sin
intentos externos. No son mensajes reales ni certificación productiva.

La compilación de las cuatro fuentes de producto, la consistencia de versión
y `git diff --check` pasan sobre ese mismo código. Las omisiones de Windows
deben contrastarse en la CI Linux del candidato definitivo.

La validación usó datos sintéticos y un navegador local; no llamó proveedores ni
modificó producción. Tras completar la batería final, queda publicar el candidato
autorizado, comprobar la CI de su SHA, integrar y verificar el despliegue automático.
El comportamiento debe contrastarse en ticks naturales antes de afirmar que el
incidente quedó resuelto. La autorización humana de continuar y publicar por este
flujo está comprobada; ninguna prueba local sustituye esa verificación productiva.
