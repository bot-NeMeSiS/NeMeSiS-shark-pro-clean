# NeMeSiS Founder OS
Centro de control único para PC y móvil.

- Producción: `/admin/founder-os`
- Local Safe: perfil **Founder** desde `/local-safe`.
- Móvil: instalar la PWA **NeMeSiS Founder**.

Founder OS separa **configurado**, **operativo**, **facturación** y **pagado**. Nunca infiere un pago como realizado.

Web Push usa: `FOUNDER_PUSH_ENABLED`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`, `FOUNDER_PUSH_REPEAT_MINUTES`.
La clave privada nunca se renderiza.

Seguridad: sesión ADMIN + CSRF; LOCAL SAFE conserva bloqueos externos; no ejecuta cobros ni modifica membresías.


## Sports Reality y frescura

Founder OS consume la evidencia de `data_freshness` ya persistida por el último tick de automatización.
No llama a APIs ni proveedores para pintar el panel.

Muestra de forma separada:
- estado canónico: `ESTABLISHED`, `PARTIAL` o `NOT_ESTABLISHED`;
- total evaluado, `fresh`, `observed`, `stale` y sin reloj canónico;
- instante y edad de la evidencia del tick;
- motivo seguro de la clasificación.

Founder Inbox abre una alerta `SPORTS_DATA` cuando la frescura es parcial o no está establecida y la resuelve automáticamente cuando vuelve a `ESTABLISHED`.
`ESTABLISHED` acredita que existe reloj canónico en la muestra; no se presenta como garantía de que todos los datos sean recientes.
