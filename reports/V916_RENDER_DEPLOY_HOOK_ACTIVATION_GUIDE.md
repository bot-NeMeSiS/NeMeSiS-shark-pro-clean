# V916 Render Deploy Hook Activation Guide

1. Entrar en Render.
2. Abrir el servicio `bot-apuestas-crgf`.
3. Crear o copiar el Deploy Hook.
4. Entrar en GitHub repo.
5. Ir a `Settings -> Secrets and variables -> Actions`.
6. Crear el secret `RENDER_DEPLOY_HOOK_URL`.
7. No pegar ese valor en chats, capturas ni reportes.
8. Ejecutar manualmente el workflow `render-deploy.yml`.
9. Confirmar `https://bot-apuestas-crgf.onrender.com/api/runtime-version`.
10. Si falla, revisar artifacts y reportes del workflow.

El hook real no se guarda en el repo.
