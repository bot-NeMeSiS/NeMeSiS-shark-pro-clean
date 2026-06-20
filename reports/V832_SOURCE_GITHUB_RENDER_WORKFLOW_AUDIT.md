# V832 Source GitHub Render Workflow Audit

## Fuente real

Carpeta oficial usada: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`.

Versión detectada antes de V832: `V830_MOBILE_BOTTOM_NAV_PIXEL_QA_REFERENCE_FINAL`.

No se usó ningún ZIP viejo mezclado como base. El último ZIP limpio detectado en `release_output` era `NeMeSiS_SHARK_PRO_V830_MOBILE_BOTTOM_NAV_PIXEL_QA_REFERENCE_FINAL_RENDER_READY.zip`.

## Git / GitHub

Git no está disponible en PATH dentro de este entorno, por lo que no se ejecutó commit, push ni creación de rama con comandos Git.

La carpeta sí contiene `.git` y se pudo leer configuración local:

- Branch detectada: `main`.
- Remote origin: `https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean.git`.

La carpeta conserva `.gitignore` y excluye `.env`, bases de datos locales, `.venv`, cachés, logs, ZIPs y `release_output`.

Si se usa GitHub Desktop: revisar cambios, crear rama sugerida `v832-full-app-reference-workflow-final`, confirmar que no aparecen `.env`, `.db`, `.venv`, ZIPs internos ni capturas, hacer commit y push normal. No usar force push.

## Render

Existen archivos de despliegue `Procfile`, `render.yaml`, `requirements.txt` y `runtime.txt`. El ZIP limpio se genera desde `tools/build_clean_release.py` y se audita con `tools/audit_release_zip.py`.

## Flujo recomendado

1. Trabajar siempre en la carpeta oficial.
2. Validar `VERSION.txt`, `APP_VERSION` y `/api/runtime-version`.
3. Ejecutar compileall y smoke tests.
4. Generar ZIP limpio.
5. Auditar ZIP con `forbidden_count=0`.
6. Subir a GitHub solo el proyecto limpio, no releases locales ni datos.
7. Render redeploy desde GitHub o ZIP limpio según flujo elegido.
8. Verificar `/api/runtime-version`, `/api/automation/health-check` y `/api/automation/master-tick` con secret.

## Rollback

Usar el último ZIP limpio anterior de `release_output` o revertir el commit en GitHub. No restaurar desde ZIPs antiguos no auditados.
