# 06 — Reglas de trabajo

## Para ChatGPT / Codex

1. Partir siempre de la versión real actual, nunca de un ZIP histórico salvo rollback explícito.
2. Leer primero `project_control/` y después el detalle histórico necesario.
3. Preservar motores estables; cambiar solo la capa necesaria para resolver el objetivo.
4. No inventar datos deportivos, comerciales ni de producción.
5. No tocar secretos, usuarios, membresías, pagos reales o Telegram real sin instrucción explícita.
6. No hacer una mejora visual que rompa rutas, formularios, permisos, datos o responsive.
7. Toda nueva fuente de estado deportivo debe pasar por Sports Truth.
8. No multiplicar helpers paralelos que calculen lifecycle/confianza por separado.
9. Un deploy correcto no cierra una incidencia: hay que validar el comportamiento público posterior.
10. Diferenciar siempre: probado local, probado en Render, probado públicamente y no probado.

## Para releases

- `VERSION.txt` y `APP_VERSION` alineados cuando corresponda a una nueva versión funcional.
- ZIP limpio sin `.git`, `.venv`, caches, DB locales, logs, secretos, vídeos, capturas o ZIPs internos.
- QA mínimo: py_compile/compileall, Jinja, checks relevantes, smoke crítico, seguridad de cron/secret y ZIP audit.
- No declarar pixel-perfect sin capturas/browser QA real.
- No declarar Telegram/pagos/proveedor real funcionando si solo se probó con mocks/dry-run.

## Para incidencias de producción

1. Confirmar persistencia antes de alarmar: repetir comprobación y separar deploy/restart de outage.
2. Prioridad CRITICAL/HIGH solo si hay impacto público material.
3. Capturar evidencia: ruta, timestamp Madrid, versión/runtime, síntoma y alcance.
4. Corregir la causa más baja posible, no maquillar solo el texto visible.
5. Aplicar fail-closed cuando la alternativa sea publicar información deportiva falsa.
6. Validar todas las superficies que consumen el mismo dato.

## Para tareas programadas

- Antes de crear una tarea nueva, comprobar si una existente puede cubrir el objetivo ampliando su prompt.
- Evitar dos tareas que vigilen la misma señal.
- Los condition watches deben callar cuando no existe problema significativo.
- Los informes semanales deben convertir observaciones en decisiones concretas, no acumular listas.

## Convención de documentación

- `CHATGPT_CONTINUATION_REPORT.md`: historia larga.
- `reports/`: evidencia técnica/release/QA por versión.
- `project_control/`: estado vivo y decisiones de gestión.
- GitHub PR/issues: cambios o problemas concretos que requieren trazabilidad de código.
