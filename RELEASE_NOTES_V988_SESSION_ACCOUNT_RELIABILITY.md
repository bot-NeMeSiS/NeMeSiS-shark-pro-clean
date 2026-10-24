# V988 — Sesión del dispositivo y actividad verificable de la cuenta

Lote de fiabilidad de acceso y actividad local. La publicación se valida mediante
los controles del commit y las observaciones posteriores de Render.

Cliente y administración pueden elegir conservar la sesión en un dispositivo
de confianza. La cookie utiliza el vencimiento absoluto ya emitido y nunca lo
alarga al releer la cuenta. Se mantienen el plazo configurado, la comprobación
de usuario/rol/auth_version y la revocación de sesiones. La opción aparece
marcada para cliente y desmarcada para administración. El acceso móvil de admin
incluye cierre de sesión mediante la confirmación GET y el POST con CSRF.

Los cuatro alias de login comparten una reserva SQLite atómica del presupuesto
existente de ocho fallos por IP en quince minutos. Un almacén no disponible
rechaza antes de verificar la contraseña. La finalización intercambia la reserva
por una única auditoría; un éxito libera capacidad. No se mantiene una transacción
durante la comprobación de contraseña. Si la auditoría no cierra, no se emite la
nueva sesión. Las rutas inexistentes y métodos sin handler no consumen reservas.
La revisión detectó ese último caso, se reprodujo ocho PUT 405 seguidos de un
login válido bloqueado con 429, y se corrigió sin retirar CSRF ni aserciones.

Cuenta y Perfil muestran hasta siete acciones con total exacto. Actividad muestra
veinte y permite continuar mediante cursor, con el mismo filtro de usuario en
consulta, total y página. Los nombres y destinos se resuelven desde identidades
locales exactas; no se toman URLs o nombres del payload. Las fechas se ordenan
por instante UTC y se presentan con la zona de Madrid. Los estados vacío y error
se distinguen; una lectura fallida no se presenta como cero actividad. No se
añade seguimiento de navegación, proveedor, escritura o reparación de historial.

El checkbox mantiene tamaño nativo, etiqueta pulsable y foco visible. El aviso
flotante de instalación no tapa el formulario de login; la guía sigue accesible.

Validación enfocada antes del cambio de etiqueta de versión: 16 casos de admisión,
10 de cookie, 20 del motor de actividad, 11 de su componente y 17 HTTP de Cuenta.
Los handlers finales pasan 32 casos HTTP de login y 14 de seguridad. El contrato
de revocación pasó 17 casos en LOCAL SAFE y su caso Telegram separado pasó en
configuración normal con transporte simulado; auth shell pasó otros cinco.
Los conteos de suites repetidas se conservan por separado y no se suman.

Navegador local: ocho casos de cliente/admin, escritorio 1440 y móvil emulado 390,
con opción marcada/desmarcada, pasaron cierre y reapertura de perfil persistente
sin inyección de cookies, vencimiento/ID inmutables, teclado/foco, logout y CSRF.
Chromium Playwright 1248 ya instalado; sin mensajes ni servicios reales. Se
preservan intentos fallidos del harness, la captura del checkbox heredado gigante,
la superposición PWA y el resultado de redondeo subpíxel anterior. La tolerancia
geométrica final es 0,1 px con min-height calculado de al menos 44 px.

Los 143 casos enfocados del snapshot inicial también pasaron juntos con guardas
sin eventos. La revisión final conserva el valor implícito no persistente para
registro y acceso rápido LOCAL SAFE; los formularios de login pasan su elección
explícitamente. Se añaden regresiones HTTP de ambos callers. El gate final exige
la batería integral Linux, las suites LOCAL SAFE/Sentinel y la navegación del
commit exacto, además de verificar Render y ciclos naturales tras publicar. Las pruebas sintéticas no certifican sesiones de usuarios reales,
dispositivos Safari/iOS físicos, copias, recuperación, pagos o toda la plataforma.

La primera batería integral del HEAD7b conservó 5.646PASS y7FAIL: seis tests
heredados aún exigían el lector anterior y un séptimo agotó la navegación de
favoritos sin JavaScript. Se migran los contratos de Cuenta/Perfil/Actividad al
snapshot7/20 y al total exacto, conservando prohibiciones de dashboard y lector
legacy; se añaden total23/frente7visibles, vacío0 e indisponibleNone. El timeout
permanece documentado y recibe diagnóstico de formulario/petición sin retry,
cambio de activación ni aumento del plazo; su causa no está demostrada. La nueva
CI completa debe superar todos los pasos antes de cualquier publicación.
