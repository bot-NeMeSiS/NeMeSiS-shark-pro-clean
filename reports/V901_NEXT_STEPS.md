# V901 Next Steps

## Antes de deploy

- Subir V901 a la raiz del repositorio correcto.
- Confirmar `VERSION.txt` y `APP_VERSION` en GitHub.
- Ejecutar deploy manual en Render con clear build cache.

## Despues del deploy

1. Abrir `/api/runtime-version` y confirmar V901.
2. Entrar en `/admin-login`.
3. Iniciar sesion admin con credenciales reales.
4. Abrir `/admin/continuous-sentinel`.
5. Pulsar `Client cycle`.
6. Confirmar que no navega a `/api/admin/...`.
7. Confirmar que el resultado aparece dentro de la pagina.
8. Revisar `/admin/sentinel-issues` si hay incidencia.

## Pendiente con credenciales reales

No se probo login admin real ni panel autenticado real de Render en esta ejecucion local.
