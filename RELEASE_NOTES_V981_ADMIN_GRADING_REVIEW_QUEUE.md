# V981 — Cola de revisión de pronósticos para administración

El Centro de Mando ya puede mostrar los pronósticos que el evaluador mantiene pendientes, junto con el partido, competición, mercado, selección, estado y motivo guardado en la evaluación. La lista enseña hasta los 12 casos recientes y el total pendiente; no ejecuta liquidaciones ni añade botones de acción. El contexto pendiente sigue oculto en las respuestas de cliente.

La lectura enlaza los registros vigentes de evaluación con los picks y los partidos almacenados, y tolera instalaciones donde alguna columna opcional todavía no exista. El empty state distingue que no haya resultados decididos de que haya picks pendientes.

Validación local final: 189 pruebas de `test_pick_grading_truth_v941.py`, `test_get_business_readonly_v941.py` y `test_admin_readonly_render_context.py` pasan, junto con el gate de regresión V941 de 23 archivos (390 pruebas). También pasan `py_compile app.py` y `git diff --check`. La cobertura incluye una revisión pendiente real, privacidad cliente/admin, esquemas heredados, fechas Madrid con campos separados o fecha completa heredada y carga responsive del CSS solo en la ruta admin.

Revisión de seguridad local del diff: cero hallazgos reportables (ID `6168ad8d-82e0-49eb-ac97-5a6f38ded412`); el resultado avisa `rollout_unavailable` y cobertura agregada parcial, así que no se presenta como revisión de producción.

V981 se integró mediante PR #276 y se desplegó en Render el 23 de octubre de 2026. La verificación confirmó runtime READY y versión alineada; el primer tick del Cron coincidió con el reemplazo de la instancia web y falló en el control de disponibilidad antes de ejecutar sus lanes. Los tres ticks naturales siguientes terminaron sin error de proceso, aunque siguieron PARTIAL en conjunto.
