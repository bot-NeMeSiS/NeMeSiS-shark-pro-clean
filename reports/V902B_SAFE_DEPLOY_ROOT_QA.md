# V902B Safe Deploy Root QA

## Objetivo
Preparar una raíz de deploy limpia para evitar que GitHub/Render vuelvan a desplegar una versión vieja o una carpeta anidada.

## Raíz esperada
La raíz que debe verse en GitHub debe contener directamente:
- `app.py`
- `VERSION.txt`
- `APP_VERSION`
- `requirements.txt`
- `templates/`
- `static/`
- `engines/`
- `tools/`
- `reports/`
- `reference_images/`

## Prohibido
No subir:
- `.git/`
- `.venv/`
- bases de datos locales
- logs
- ZIPs internos
- `release_output/`
- carpetas anidadas del proyecto
- secretos reales

## Carpeta preparada
La carpeta final esperada tras generar ZIP es:
`release_output/V902B_DEPLOY_ROOT_CONTENTS`.
