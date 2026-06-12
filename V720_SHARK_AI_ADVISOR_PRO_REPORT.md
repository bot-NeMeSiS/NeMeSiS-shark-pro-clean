# V720 — SHARK AI Advisor PRO

## Objetivo
Convertir SHARK en un asesor deportivo más profesional, claro y útil: respuestas cortas, picks reales con cuota, explicación de riesgo, combis responsables y acciones visibles sin rutas internas tipo `/picks` como texto.

## Cambios principales

### SHARK AI Advisor PRO
- Versión actualizada a `V720_SHARK_AI_ADVISOR_PRO` en `app.py` y `VERSION.txt`.
- `shark_briefing()` ahora usa el motor de calidad de picks para distinguir picks premium de señales en estudio.
- SHARK prioriza picks premium reales: cuota real, selección clara, mercado claro, score de calidad y riesgo explicado.
- Añadida respuesta específica para:
  - mejor pick de hoy
  - qué no tocar / qué dejar en estudio
  - combi segura
  - combi media/larga hasta 15
  - value / oportunidades
  - directo
  - favoritos
  - resumen del día
- SHARK ya no responde con rutas internas como texto. Devuelve `actions` con botones útiles para frontend.
- Las combinadas largas avisan de riesgo alto y stake bajo obligatorio.
- Si faltan cuotas reales, SHARK no inventa: indica que no hay pick premium cerrado.

### Widget flotante SHARK
- Botones rápidos mejorados:
  - Pick de hoy
  - No tocar
  - Combi segura
  - Combi 15
  - Directo
  - Value
- El widget ahora muestra botones de acción reales devueltos por la API.

### Página `/shark`
- Hero actualizado a “SHARK AI Advisor PRO”.
- Texto más comercial y más claro.
- Picks explicados muestran precaución y etiqueta de calidad.
- Mensaje de transparencia actualizado: pocos picks buenos antes que mucho ruido.

## Archivos tocados
- `app.py`
- `VERSION.txt`
- `templates/base.html`
- `templates/shark.html`
- `static/app.css`
- `V720_SHARK_AI_ADVISOR_PRO_REPORT.md`

## Qué NO se tocó
- Render
- Cron Jobs
- `AUTOMATION_SECRET`
- `DB_PATH=/data/database.db`
- Telegram automático
- Telegram solo fútbol
- Calibración PRO Telegram
- Login/registro
- Membresías
- Combis hasta 15
- Escudos/identidad V718
- Calidad de picks V719

## Validación realizada
- `python3 -m py_compile app.py`: OK
- `python3 -m compileall -q app.py engines templates`: OK
- `python3 tools/smoke_check.py`: no completado en este entorno porque falta Flask instalado.
- Parseo Jinja simple: no aplicable sin registrar filtros Flask personalizados; el error detectado corresponde a filtros existentes de la app, no a los templates modificados.

## Cómo probar en Render
1. Desplegar el ZIP Render Ready.
2. Abrir `/api/runtime-version` y confirmar:
   `V720_SHARK_AI_ADVISOR_PRO`
3. Probar `/shark`.
4. Abrir el botón flotante SHARK en una cuenta cliente.
5. Probar:
   - Pick de hoy
   - No tocar
   - Combi segura
   - Combi 15
   - Directo
   - Value
6. Confirmar que SHARK responde sin inventar datos y con botones de acción.
7. Confirmar que Cron/Telegram siguen funcionando igual.

## Pendiente dependiente de producción real
- La calidad de respuestas depende de picks/cuotas reales disponibles en Render.
- Si no hay cuotas reales, SHARK debe responder que no hay pick premium cerrado.
- La validación completa con Flask debe ejecutarse en un entorno con `pip install -r requirements.txt`.
