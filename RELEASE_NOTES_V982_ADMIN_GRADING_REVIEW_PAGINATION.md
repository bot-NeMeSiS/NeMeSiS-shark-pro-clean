# V982 — Paginación de revisiones administrativas pendientes

La cola de revisión de pronósticos ahora permite recorrer todos los casos pendientes desde el Centro de Mando. La vista muestra el rango y el total, controles anterior/siguiente con estado accesible y una sola página de 12 filas por consulta. La página solicitada se valida y se limita al rango disponible.

La paginación usa GET y solo se activa en la ruta administrativa ya protegida. La API pública y las respuestas de cliente mantienen su comportamiento y no exponen las filas pendientes. Ninguna navegación modifica SQLite ni aplica resultados.

La hoja de estilo mantiene la cola en una columna en móvil y adapta los controles para pantallas estrechas. Validación incluida: paginación real con más de 12 filas, límites de página, rutas públicas/admin, ausencia de escrituras en GET y regresiones de evaluación.

Validación local: 190/190 pruebas de `test_get_business_readonly_v941.py`, `test_pick_grading_truth_v941.py` y `test_admin_readonly_render_context.py` pasaron; `py_compile app.py` y `git diff --check` también pasaron. La revisión de seguridad del diff no reportó hallazgos; no inspeccionó datos ni configuración de producción. El desempate determinista añadido durante la revisión se comprobó manualmente junto con la prueba de fechas empatadas.
