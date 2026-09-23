# Telegram Premium - cierre local 2026-09-23

Estado: QA / LOCAL_ONLY. No certificado en Telegram ni en produccion.
Base: 706094630d337f9e329a8401fae217b316a9b49c.
Rama conservada: codex/repo-hygiene-20260923. Sin staging ni commit.
El diff previo de higiene se conserva y NO forma parte del parche Telegram.

## Implementacion

- engines/telegram_message_formatter.py: iconografia coherente, informacion ausente explicita, Madrid canonico, Sports Truth, HTML escapado y truncado con etiquetas balanceadas. Caption con aviso responsable; FREE/PRO/ELITE reutilizan el formato.
- engines/telegram_visual_card_engine.py: tarjetas PNG 960x1000; composiciones pick/combi/live/resultado/highlight; texto medido, nombres limitados visualmente sin modificar los datos del mensaje; escudos raster locales seguros o iniciales. Sin nuevas descargas externas.
- engines/telegram_delivery_engine.py: elimina stake/riesgo/value inferidos y umbral de cuota inventado; conserva filtrado y orden existentes. Combi diferencia cuotas individuales de cotizacion conjunta no disponible.
- engines/telegram_activity_engine.py: LIVE requiere Sports Truth, no basta minuto; final necesita resultado confirmado; rechaza cuotas no finitas y highlights bloqueados/sin enlace valido. No cambia cron ni horarios de actividad.
- app.py: conecta tarjetas tambien al flujo auto_pick existente; conserva flags actuales (LIVE visual desactivado por defecto); serializacion JSON integra de payload; respuesta Telegram necesita confirmacion verificable; timeout ambiguo queda uncertain, sin reintento automatico. Fallback solo tras fallo previo al envio o rechazo confirmado. Botones sin enlaces administrativos.
- templates/admin_telegram_pro_preview.html: panel existente con diez tipos, PNG descargable, caption, texto completo, estado visual, ultimos trabajos y resultados persistidos. Solo lectura; ya no usa partidos/cuotas de ejemplo inventados. No envia ni encola.
- tests/test_telegram_visual_premium.py: pruebas positivas/negativas, persistencia de cola, transporte interceptado y navegador sobre Flask real.

## Tipos

Pick individual, combinada, LIVE, resultado/pick cerrado, highlight, agenda diaria,
actualizacion de actividad, recordatorio, cierre del dia y bienvenida/sistema.
Los cinco primeros usan el renderer existente cuando su flag lo permite.
El resto conserva texto premium, sin crear motores ni nuevos trabajos programados.
Las membresias cambian presentacion; no se modifican precios, permisos ni planes reales.

## Evidencia de la revision

186 PASS, 0 FAIL, 0 ERROR, 0 SKIP. No es una suite global del repositorio.
Continuidad: otras 18 pruebas del lector de la cola PASS; se conserva su registro cerrado de fuentes.
Se actualiza tests/test_project_control_reader.py solo para TG-001: 24 IDs unicos y 9 trabajos en QA.
Incluye Telegram premium/fiabilidad/futbol, Madrid/DST/saludo y nuevas regresiones.
Flask y SQLite reales en almacenamiento desechable; transporte Telegram interceptado.
Boundary events: [] (ninguna conexion externa intentada por el proceso QA).
Navegador Chromium real: 1366x900, 390x900, 430x900; sin overflow horizontal ni errores JS.
Verificados: acceso admin, rechazo visitante/ELITE, GET sin nuevos trabajos,
caption expandible, descarga PNG, Command Center y retorno.
Se comprobo serializacion multipart/caption, fallo de renderer/Pillow, rechazo de foto,
fallback HTML a texto, no segundo envio tras timeout, dedupe y cola uncertain no reintentable.
AST de los Python modificados y parse Jinja: PASS. Diff-check: PASS.
Secret/Privacy Guard sobre lineas nuevas del diff: PASS; no certifica todo el historial.

Evidencia exacta (PNG, XML, huellas SHA-256, galeria y parche separado):
C:\Users\aloha\.codex\visualizations\2026\05\27\019e69a5-0d06-7af3-98c9-b9e23032ef02\telegram-premium-20260923

Fuente QA final: data/local_dev/candidate-8db65bc9ecf24b2e9dd833a2c8903a7b/result.xml.
qa-final.xml: 186 casos; scope-verification.json: hashes de los siete archivos de codigo/tests.
TELEGRAM_PREMIUM_LOCAL.patch excluye los cambios anteriores de higiene y la documentacion.
Las imagenes qa-*.png estan marcadas MUESTRA QA y usan un fixture ya existente:
NO son recomendaciones, cuotas ni eventos reales. Las capturas del panel usan DB temporal.

## Preview

http://127.0.0.1:54912/admin/telegram/pro-preview
Instancia local aislada, comprobada HTTP 200 con sesion admin LOCAL SAFE.
Sin workers, jobs productivos ni credenciales externas. No es Render.
El acceso de prueba se ha solicitado al panel del navegador de Codex; la herramienta
de apertura devolvio queued, no una certificacion de sesion del navegador del propietario.
La galeria HTML tambien se puede abrir sin servidor ni autenticacion.

## Limites y siguiente paso

- No se ha enviado nada a Telegram: falta envio de prueba expresamente autorizado y revision en cliente Telegram real.
- Escudos: PNG/JPEG/WebP locales. URLs remotas sin bytes locales y SVG usan iniciales. Falta validar assets reales cacheados; no se anade un descargador ni peticiones a proveedores en esta iteracion.
- Pillow ausente o error de render: mensaje de texto premium. Fallo de un escudo: la tarjeta conserva iniciales. Entrega incierta no significa fallida ni enviada.
- La vista previa de tipos sin payload almacenado muestra datos pendientes. No se ha certificado cobertura de datos reales, derechos de video ni delivery de cada plan/destino.
- No se garantiza ejecucion exactamente una vez frente a toda concurrencia distribuida; se ha probado el dedupe existente y se ha evitado el reenvio automatico por timeout ambiguo. No se rediseno la cola.
- Antes de integrar: revisar el parche separado, aportar escudos reales locales/cacheados y autorizar una prueba controlada de entrega. Publicacion e integracion requieren autorizacion posterior.
- No staging, commit, push, PR, merge, deploy, limpieza, cambios en main, proveedores, DB real, pagos o tareas programadas.

Ediciones congeladas al cerrar esta iteracion. No comenzar otro frente automaticamente.
Referencia de protocolo: https://core.telegram.org/bots/api#sendphoto (caption hasta 1024 caracteres tras interpretar entidades).
