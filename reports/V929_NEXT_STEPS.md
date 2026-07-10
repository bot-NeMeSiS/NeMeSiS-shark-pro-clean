# V929 Next Steps

1. Subir el contenido interno de `release_output/V929_DEPLOY_ROOT_CONTENTS` a la raiz de GitHub main.
2. Esperar el deploy de Render.
3. Confirmar que `/api/runtime-version` devuelve `V929_NAVIGATION_INTEGRITY_ROUTE_NOT_FOUND_FULL_APP_RECOVERY_FINAL` con `version_files_match=true` y `deployment_alignment_status=aligned_local_files`.
4. Abrir `/clientes` en ventana privada: debe llevar a login, no a 404.
5. Repetir login cliente y recorrer bottom nav; despues revisar `/admin/navigation-integrity` con sesion admin.
6. No declarar pixel-perfect por este QA de navegacion.
