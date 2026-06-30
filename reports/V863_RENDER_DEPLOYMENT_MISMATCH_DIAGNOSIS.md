# V863 Render Deployment Mismatch Diagnosis

## Diagnóstico

Render usa `/opt/render/project/src` y `app.py` en raíz. El runtime real confirma que no hay carpeta anidada activa en producción.

## Revisado localmente

- `VERSION.txt` local actualizado a V863.
- `APP_VERSION` local actualizado a V863.
- `app.py` local está en raíz.
- `VERSION.txt` local está en raíz.
- ZIP V862 previo existía como base limpia.
- V863 queda lista para generar ZIP limpio.

## Riesgo principal

Si se sube el ZIP como archivo dentro del repo en vez de descomprimir su contenido en raíz, Render seguirá usando código anterior. Esto debe evitarse en el despliegue.

## Start command esperado

`gunicorn app:app`
