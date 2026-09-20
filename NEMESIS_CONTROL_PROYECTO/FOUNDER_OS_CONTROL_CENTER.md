# NeMeSiS Founder OS
Centro de control único para PC y móvil.

- Producción: `/admin/founder-os`
- Local Safe: perfil **Founder** desde `/local-safe`.
- Móvil: instalar la PWA **NeMeSiS Founder**.

Founder OS separa **configurado**, **operativo**, **facturación** y **pagado**. Nunca infiere un pago como realizado.

Web Push usa: `FOUNDER_PUSH_ENABLED`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`, `FOUNDER_PUSH_REPEAT_MINUTES`.
La clave privada nunca se renderiza.

Seguridad: sesión ADMIN + CSRF; LOCAL SAFE conserva bloqueos externos; no ejecuta cobros ni modifica membresías.
