# V902B Next Deployment Actions

## Acción exacta para Damian
1. Abrir `release_output/V902B_DEPLOY_ROOT_CONTENTS`.
2. Copiar el contenido interno, no la carpeta padre.
3. Pegar ese contenido en la raíz del repo GitHub `bot-NeMeSiS/NeMeSiS-shark-pro-clean`, rama `main`.
4. Confirmar en GitHub raíz:
   - `VERSION.txt` = `V902B_DEPLOY_ALIGNMENT_AND_AUTOMATION_SECRET_ROTATION_GUARD_FINAL`.
   - `app.py` contiene `APP_VERSION = 'V902B_DEPLOY_ALIGNMENT_AND_AUTOMATION_SECRET_ROTATION_GUARD_FINAL'`.
5. En Render, abrir `bot-apuestas-crgf`.
6. Confirmar Root Directory vacío o apuntando a la raíz correcta.
7. Confirmar Start Command: `gunicorn app:app`.
8. Ejecutar `Manual Deploy -> Clear build cache & deploy`.
9. Consultar `/api/runtime-version`.
10. Confirmar que Render devuelve V902B.

## Si Render sigue en V897
Revisar:
- Render apunta a otro repo.
- Render apunta a otra rama.
- GitHub no recibió la raíz V902B.
- Se subió el ZIP como archivo.
- Se subió una carpeta anidada.
- Render desplegó un commit anterior.
- No se limpió caché de build.
