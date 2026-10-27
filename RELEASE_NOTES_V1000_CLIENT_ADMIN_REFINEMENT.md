# V1000 · Cliente, administración y referencias deportivas

## Cambios del candidato

- Ficha canónica: el escudo y el nombre forman una unidad por equipo, con marcador independiente. Diseño simétrico, nombres largos, RTL y fallback a 320/390/834/1440 px.
- Acceso cliente/Admin: formulario compacto, identidad aprobada visible en el espacio libre, campos y superficie sólidos. Contraste, colores forzados, reducción de transparencia, CSRF, sesión y destinos conservados. La transparencia queda localizada en decoración y espacios libres; conserva superficies de lectura firmes.
- Inicio: saludo secundario con el nombre real permitido; partidos como encabezado; cuenta/plan/preferencias en un acceso coherente. El CTA principal usa el calendario cuando no hay directo confirmado. Corrección del singular del resumen de otras competiciones.
- Admin: búsqueda por grupos y términos como «clientes» e «incidencias», también con GET sin JavaScript; los mismos 16 destinos agrupados para escritorio y Explorar móvil; frecuentes y búsqueda accesibles. La bandeja del fundador precede los indicadores; una lectura fallida o un importe no registrado no aparecen como un cero demostrado.
- Movimiento opcional: luz marina desactivada por defecto; pausa persistente y preferencias del dispositivo. El descubrimiento de SHARK tiene dos pulsos finitos y después permanece quieto. Interacción, modal, escritura y visibilidad detienen la decoración. Abrir/animar no inicia una pregunta. El almacenamiento bloqueado deja el movimiento y la telemetría opcional en silencio.
- Referencia de competición explícita y versionada para API-Football/140/`la-liga-spain` y `laliga`. Comprueba las PK y contradicciones existentes; fuentes primarias independientes, equivalencia local revisada. No es un puente publicado por los proveedores ni autoriza unir equipos/eventos.
- Instalador de accesos PC: Admin online, conservación del cliente PWA/perfil/app-id y carpeta existente, vista previa y respaldo antes de actualizar. Se prueba exclusivamente en Escritorios sintéticos; no reinstala una PWA ni modifica el Escritorio real durante la validación.

- SQLite readonly: codifica la ruta literal, incluidos `#` y `%`, para que no seleccionen otro archivo ni eliminen accidentalmente `mode=ro`. No activa ningún nuevo formato o fallback de copia.

## Verificación y límites

Se conservan los ensayos iniciales fallidos y sus correcciones. Las pruebas de navegador usan la aplicación real y SQLite propia bajo el supervisor LOCAL SAFE original; los módulos que lo requieren se ejecutan expresamente bajo ese supervisor en CI. La publicación requiere la CI del HEAD final, revisión, integración autorizada, Render web/Cron LIVE y runtime alineado; después se observan ciclos naturales.

V1000 no significa que haya terminado la aceptación integral de v1. La rotación automática de destacados, el núcleo de actualización de calendario/ficha, el rendimiento general y SHARK generativo siguen abiertos. La referencia de competición no resuelve por sí sola los duplicados: el caso observado aún carece de puente verificable de equipos y temporada Odds.

La copia automática real y su recuperación aislada siguen críticas y sin certificar. El adaptador comprimido se conserva fuera del producto: la prueba sintética de 1,1 GB agotó el límite total de 15 s durante integridad, sin publicar nada. No se activa por pasar pruebas pequeñas ni se aumentan plazos, recursos, disco o coste.

No cambios de secretos, proveedores, planes, cuotas, presupuestos, derechos, pagos, usuarios reales, servicios o almacenamiento. Se preservan datos, historial y cuarentena. Ningún job, backup, limpieza, recuperación, refresh de proveedor o Telegram real se invoca manualmente.

## Continuidad de uso · favoritos, obligaciones y navegación

- Favoritos: las tarjetas que representan la misma entidad comparten el bloqueo durante el guardado y el resultado confirmado. El destacado y las demás colecciones dejan de mostrar estrellas contradictorias. Una petición fallida conserva el estado anterior; el siguiente intento requiere otro clic. Las entidades distintas siguen siendo independientes y los controles previamente deshabilitados conservan esa condición.
- Obligaciones del fundador: los modos añadir y editar se distinguen, con cancelación explícita y enlaces GET que también funcionan sin JavaScript. Un rechazo de validación devuelve el formulario abierto con los campos conservados y el error visible, sin trasladar el borrador a la URL ni a la sesión. El cambio se confirma únicamente cuando el motor lo acepta; un registro inexistente no aparece como pagado. Estos controles mantienen el registro manual existente y no realizan pagos externos.
- Navegación desde Explorar: las sugerencias deportivas dejan de contraerse entre pulsar y soltar sobre un enlace. La búsqueda pendiente se cancela sin desplazar el destino durante el gesto; el cierre visual espera a su finalización. Se conserva la activación nativa del navegador y se protege una consulta nueva frente a cierres antiguos encolados.
- Aislamiento de navegador: los servidores temporales esperan al final de sus peticiones antes de restaurar el estado compartido de la aplicación. El acceso registra método, ruta, estado y destino de la respuesta real, sin credenciales ni contenido del formulario. Se conserva el supervisor LOCAL SAFE y sus límites. Esta mejora no demuestra la causa del 503 histórico ni lo reclasifica como corregido.
- Regresión: escenarios de tarjetas duplicadas, fallos de HTTP/JSON/red, creación tras cancelar edición, errores con datos conservados, permisos/CSRF, lectura sin escrituras, finalización de peticiones y activación de enlaces con sugerencias visibles. El recorrido real de obligaciones se incorpora al circuito LOCAL SAFE de CI, además de las matrices V1000 existentes.
