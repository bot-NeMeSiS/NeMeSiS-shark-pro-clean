# V930 Next Steps

1. Subir el contenido interno de `release_output/V930_DEPLOY_ROOT_CONTENTS` a la raíz de `main`; no subir la carpeta padre.
2. Confirmar en GitHub que `app.py`, `VERSION.txt`, `requirements.txt`, `templates/`, `static/`, `engines/` y `tools/` están en raíz.
3. Esperar el auto-deploy de Render o lanzar el workflow autorizado; no pegar hooks ni tokens en chats o reportes.
4. Consultar `/api/runtime-version` hasta ver V930, `version_files_match=true`, `deployment_alignment_status=aligned_local_files`, CSS busting y service worker V930.
5. Ejecutar Browser QA contra Render y revisar humanamente las 16 parejas de referencia.
6. Revisar en vídeo: home, app, calendario, live, picks, histórico, SHARK, Telegram, perfil, planes, dashboard admin, Telegram admin, pagos, automatización, Sentinel y navegación móvil.
7. Abrir un detalle de partido real disponible; en local quedó bloqueado correctamente por DB temporal vacía.

Siguiente acción runtime: `deploy_v930_then_run_render_browser_qa_and_human_visual_review`.
