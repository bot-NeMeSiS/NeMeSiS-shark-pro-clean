# V876 Render Deploy Exact Steps

## Servicio

Abrir Render y entrar al servicio:

`bot-apuestas-crgf`

## Configuracion a confirmar

1. Repo conectado:
   `https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean`
   o el repo correcto equivalente.
2. Branch:
   `main`
3. Root Directory:
   vacio si `app.py` esta en raiz.
   Si se usa root directory, debe apuntar exactamente a la carpeta que contiene `app.py`.
4. Build Command:
   `pip install -r requirements.txt`
5. Start Command:
   `gunicorn app:app`

   O el comando completo:

   `gunicorn app:app --bind 0.0.0.0:$PORT`

   El `render.yaml` local usa:

   `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 3 --worker-class gthread --timeout 90`

## Deploy

1. Ejecutar:
   `Manual Deploy -> Clear build cache & deploy`
2. Esperar a que Render muestre:
   `Your service is live`
3. Abrir:
   `https://bot-apuestas-crgf.onrender.com/api/runtime-version`
4. Confirmar que devuelve:
   `V876_RENDER_VERSION_ALIGNMENT_AND_FINAL_VISUAL_DEPLOY_CHECK_FINAL`

## Si devuelve V855

El deploy no esta leyendo el contenido V876 en raiz o Render esta conectado a otro repo/rama/root.

