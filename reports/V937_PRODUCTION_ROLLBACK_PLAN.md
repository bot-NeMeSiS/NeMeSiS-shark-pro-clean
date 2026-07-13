# V937 Production Rollback Plan

Preparado: 2026-07-13 Madrid

## Identidad

- Main pre-V937: `6dafad26de43e5217f8b601d449802767c9c23f8`.
- Backup remoto: `origin/backup/pre-v937-production` confirmado en ese SHA.
- Main V937 final: `0cc17b323b5508fe9de7905f3a1307e71deffdc7`.
- Runtime actual: V937 alineada.

## Procedimiento

1. Confirmar de nuevo el SHA de `origin/backup/pre-v937-production`.
2. Crear una rama de rollback desde `main`; restaurar el arbol de aplicacion desde `6dafad2` mediante un commit normal.
3. No force-push. No borrar, copiar ni restaurar la DB.
4. Push del commit de rollback a `origin/main` y despliegue mediante el servicio Render existente.
5. Mantener persistent disk, mount path, `DB_PATH`, plan, variables y cron sin cambios.
6. Verificar runtime, home, login cliente/admin, manifest y service worker.
7. Comprobar una sesion cliente y una ruta admin con cuenta de prueba autorizada.

## Disparadores

Rollback ante bucle 5xx, fallo general de login, DB persistente ausente, secreto expuesto, cobro incorrecto, envio Telegram no controlado, pick incompleto publico o datos stale presentados como actuales.

El runtime V936 tenia un FileNotFoundError ya conocido. Volver a ese SHA es solo una medida de contencion; debe evaluarse frente al hotfix V937 antes de ejecutarlo.
