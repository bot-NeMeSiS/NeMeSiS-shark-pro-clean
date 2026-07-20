# V938 Session Cookie Security QA

## Configuración aplicada

- `HttpOnly=true`.
- `SameSite=Lax` por defecto, con valores permitidos `Lax`, `Strict` o `None`.
- `Secure=true` por defecto cuando se detecta Render/producción; configurable de forma explícita.
- Vida permanente por defecto: 12 horas; límites aceptados: 1 a 168 horas.

## Evidencia

El check V938 ejecuta Flask en modo Render simulado y exige HttpOnly, Secure y SameSite válidos. En desarrollo HTTP local, Secure permanece falso por defecto para no inutilizar la sesión.

## Límite

La cabecera `Set-Cookie` real de Render permanece **BLOQUEADA POR ACCESO** hasta la certificación post-deploy.
